#!/usr/bin/env python3
"""Entry 4 E3c-b-c-b2-a — ``7f1469f5…`` rank-1 upstream pipeline ladder (``eig.md`` §4.2 K84 P1).

First tier-reorder wide-drift hash (greedy **47** snaps, K80). Row-pair **30/37** (first
default-path ``order`` mismatch) through DGEEVX pipeline snaps; locates first upstream
stage where py leader diverges from ref.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_lapack_nobalance import (
    dtrevc3_debug_get,
    dtrevc3_debug_reset,
    dtrevc3_debug_set_col,
    dtrevc3_debug_set_row_pair,
    eig_real_nobalance,
    lapack_nobalance_available,
)
from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from python_src.utils.eig_nobalance import resolve_backend
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "7f1469f5003eebf1"
ROW_LO_0 = 30
ROW_HI_0 = 37
ORDER_ROWS = (30, 37, 18, 22, 40, 51, 43, 26)


def _leader(abs_lo: float, abs_hi: float) -> int | None:
    if abs_lo == 0.0 and abs_hi == 0.0:
        return None
    tol = 1e-15 * max(abs_lo, abs_hi, 1.0)
    if abs(abs_lo - abs_hi) <= tol:
        return ROW_LO_0
    if abs_lo > abs_hi:
        return ROW_LO_0
    return ROW_HI_0


def _stage(abs_lo: float, abs_hi: float) -> dict[str, Any]:
    return {
        "abs_lo": float(abs_lo),
        "abs_hi": float(abs_hi),
        "row_lo_0based": ROW_LO_0,
        "row_hi_0based": ROW_HI_0,
        "leader_0based": _leader(abs_lo, abs_hi),
        "diff_lo_minus_hi": float(abs_lo) - float(abs_hi),
    }


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def _first_leader_flip(
    ladder: dict[str, dict[str, Any]], *, ref_leader: int | None
) -> dict[str, Any] | None:
    if ref_leader is None:
        return None
    prev: int | None = None
    for name, st in ladder.items():
        leader = st["leader_0based"]
        if leader is None:
            continue
        li = int(leader)
        if prev is None:
            prev = li
            continue
        if li != prev:
            return {
                "site": name,
                "from_leader_0based": prev,
                "to_leader_0based": li,
                "ref_leader_0based": ref_leader,
                "matches_ref": li == ref_leader,
            }
        prev = li
    return None


def _first_abs_divergence(
    ladder: dict[str, dict[str, Any]], *, ref_diff: float, tol_scale: float = 1e-15
) -> dict[str, Any] | None:
    """First stage where pair diff_lo_minus_hi differs from ref final by > tol."""
    ref_tol = max(1e-300, abs(ref_diff) * tol_scale, 1e-15)
    for name, st in ladder.items():
        d = float(st["diff_lo_minus_hi"]) - float(ref_diff)
        if abs(d) > ref_tol:
            return {
                "site": name,
                "delta_diff_minus_ref_final": d,
                "stage": st,
            }
    return None


def _replay_oracles(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(name: str, vec: np.ndarray) -> None:
        order_got = _sort_abs_descend_matlab_like(vec)
        rows.append(
            {
                "replay": name,
                "mismatch_count": _mismatch_count(order_ref, order_got),
                "rank1_got": int(order_got[1]),
                "rank1_ref": int(order_ref[1]),
            }
        )

    add("live_py", abs_py)
    a = abs_py.copy()
    for i in (30, 37):
        a[i] = abs_ref[i]
    add("snap_pair_30_37_to_ref", a)
    a = abs_py.copy()
    for i in ORDER_ROWS:
        a[i] = abs_ref[i]
    add("snap_order_rows_to_ref", a)
    return rows


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c 7f1469 upstream] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c 7f1469 upstream] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blk = [b for b in pickle.load(f)["blocks"] if b["sub_hash"] == HASH][0]

    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    j_ref = int(dr["jmax"])
    abs_ref = dr["absv"]
    order_ref = dr["order"]
    ref_pair = _stage(float(abs_ref[ROW_LO_0]), float(abs_ref[ROW_HI_0]))

    w_probe, _ = eig_real_nobalance(sub)
    w_probe = np.asarray(w_probe, dtype=np.complex128).ravel(order="F")
    perm = np.argsort(np.abs(w_probe), kind="mergesort")
    raw_col = int(perm[j_ref])
    fortran_col = raw_col + 1

    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    dtrevc3_debug_set_row_pair(ROW_LO_0 + 1, ROW_HI_0 + 1)
    w_v, v_v = eig_real_nobalance(sub)
    dbg = dtrevc3_debug_get()

    w_pp, v_pp = apply_matlab_spectral_postprocess(w_v, v_v)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_py = dp["absv"]
    py_pair = _stage(float(abs_py[ROW_LO_0]), float(abs_py[ROW_HI_0]))

    ladder = {
        "1_post_DGEHRD": _stage(
            dbg["post_dgehrd_hess_col_abs_13"], dbg["post_dgehrd_hess_col_abs_44"]
        ),
        "2_post_DORGHR": _stage(
            dbg["post_dorghr_q_col_abs_13"], dbg["post_dorghr_q_col_abs_44"]
        ),
        "2a_post_DLAQR0_in_VR_col": _stage(
            dbg["dlaqr0_in_vr_col_abs_13"], dbg["dlaqr0_in_vr_col_abs_44"]
        ),
        "2b_post_DLAQR0_out_schur_VR_col": _stage(
            dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"]
        ),
        "3_post_DHSEQR": _stage(
            dbg["post_dhseqr_schur_vr_col_abs_13"],
            dbg["post_dhseqr_schur_vr_col_abs_44"],
        ),
        "4_DTREVC3_pre_IDAMAX": _stage(
            dbg["post_bt_pre_idamax_abs_13"], dbg["post_bt_pre_idamax_abs_44"]
        ),
        "5_DTREVC3_post_normalize": _stage(dbg["post_abs_13"], dbg["post_abs_44"]),
        "6_final_pp": py_pair,
    }

    row_table = []
    for i in ORDER_ROWS:
        row_table.append(
            {
                "index": i,
                "abs_ref": float(abs_ref[i]),
                "abs_py": float(abs_py[i]),
                "delta_py_minus_ref": float(abs_py[i] - abs_ref[i]),
            }
        )

    mm = _mismatch_count(order_ref, dp["order"])
    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.2 E3c-b-c-b2-a",
        "sub_hash": HASH,
        "backend": resolve_backend(),
        "row_pair_0based": [ROW_LO_0, ROW_HI_0],
        "fortran_dbg_col": fortran_col,
        "raw_col_for_jref_0based": raw_col,
        "j_ref_0based": j_ref,
        "order_mismatch_count": mm,
        "greedy_close_snap_count_k80": 47,
        "first_mismatch_default": first_order_mismatch(
            order_ref, dp["order"], abs_ref, abs_py
        ),
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_got": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "ref_pair_at_jmax": ref_pair,
        "py_pair_at_jmax": py_pair,
        "pipeline_ladder_rank1_pair": ladder,
        "first_leader_flip_py": _first_leader_flip(
            ladder, ref_leader=ref_pair["leader_0based"]
        ),
        "first_abs_divergence_from_ref_final": _first_abs_divergence(
            ladder, ref_diff=float(ref_pair["diff_lo_minus_hi"])
        ),
        "order_row_table": row_table,
        "replay_oracles": _replay_oracles(abs_py, abs_ref, order_ref),
        "oracle_kind": "wide_column_absv_drift",
        "compute_patch_hint": (
            "K84 P1: locate first upstream stage for rank-1 pair 30/37; "
            "compare to 866 DHSEQR pattern; multi-row fidelity likely."
        ),
    }

    out = (
        path.parent
        / "DEMAtariIII_fsl_backward_entry4_eig_e3c_7f1469_upstream_pipeline_ladder.json"
    )
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    flip = payload.get("first_leader_flip_py") or {}
    div = payload.get("first_abs_divergence_from_ref_final") or {}
    ro = payload["replay_oracles"]
    print(
        f"[e3c 7f1469 upstream] mm={mm}/72 pair ref_leader={ref_pair['leader_0based']} "
        f"py_leader={py_pair['leader_0based']} flip_site={flip.get('site')} "
        f"div_site={div.get('site')} replay_pair={ro[1]['mismatch_count']}"
    )
    print(f"[e3c 7f1469 upstream] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
