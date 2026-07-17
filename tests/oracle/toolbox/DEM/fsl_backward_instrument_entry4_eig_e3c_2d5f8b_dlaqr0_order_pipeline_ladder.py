#!/usr/bin/env python3
"""Entry 4 E3c-b-c-b2-c — ``2d5f8b83…`` ``DLAQR0_out`` order pipeline ladder (``eig.md`` §4.2 K88).

Post-**K87**. Rank-1 pair **48/13** (first default-path ``order`` mismatch): pipeline ladder +
per-sweep ``DLAQR0`` table via ``set_row_pair``; greedy-prefix replay oracles. No Fortran changes.
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
    dtrevc3_debug_get_qr0_sweep_table,
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

HASH = "2d5f8b838be81f21"
ROW_LO_0 = 48
ROW_HI_0 = 13
ORDER_ROWS = (48, 13, 44, 25, 23, 72, 21, 29)
GREEDY_PREFIX_MILESTONES = (1, 5, 10, 17, 33, 80)
KMAX_HOOK_ROWS = (44, 13)


def _leader(row_lo: int, row_hi: int, abs_lo: float, abs_hi: float) -> int | None:
    if abs_lo == 0.0 and abs_hi == 0.0:
        return None
    tol = 1e-15 * max(abs_lo, abs_hi, 1.0)
    if abs(abs_lo - abs_hi) <= tol:
        return row_lo
    if abs_lo > abs_hi:
        return row_lo
    return row_hi


def _stage(row_lo: int, row_hi: int, abs_lo: float, abs_hi: float) -> dict[str, Any]:
    return {
        "abs_lo": float(abs_lo),
        "abs_hi": float(abs_hi),
        "row_lo_0based": row_lo,
        "row_hi_0based": row_hi,
        "leader_0based": _leader(row_lo, row_hi, abs_lo, abs_hi),
        "diff_lo_minus_hi": float(abs_lo) - float(abs_hi),
    }


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def _greedy_snap_order(abs_py: np.ndarray, abs_ref: np.ndarray) -> list[int]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    return list(np.argsort(-d).astype(int))


def _first_leader_flip_ladder(
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


def _first_sweep_leader_flip(
    sweeps: list[dict[str, Any]], *, ref_leader: int, row_lo: int, row_hi: int
) -> dict[str, Any] | None:
    prev: int | None = None
    for sw in sweeps:
        leader = _leader(row_lo, row_hi, float(sw["abs_lo"]), float(sw["abs_hi"]))
        if leader is None:
            continue
        li = int(leader)
        if prev is None:
            prev = li
            continue
        if li != prev:
            return {
                "sweep": int(sw["sweep"]),
                "route_name": sw["route_name"],
                "it": int(sw["it"]),
                "from_leader_0based": prev,
                "to_leader_0based": li,
                "ref_leader_0based": ref_leader,
                "matches_ref": li == ref_leader,
            }
        prev = li
    return None


def _replay_oracles(
    abs_py: np.ndarray,
    abs_ref: np.ndarray,
    order_ref: np.ndarray,
    greedy_rows: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(name: str, vec: np.ndarray, **extra: Any) -> None:
        order_got = _sort_abs_descend_matlab_like(vec)
        rows.append(
            {
                "replay": name,
                "mismatch_count": _mismatch_count(order_ref, order_got),
                "rank1_got": int(order_got[1]),
                "rank1_ref": int(order_ref[1]),
                **extra,
            }
        )

    add("live_py", abs_py)
    a = abs_py.copy()
    a[ROW_LO_0] = abs_ref[ROW_LO_0]
    a[ROW_HI_0] = abs_ref[ROW_HI_0]
    add("snap_pair_48_13_to_ref", a)
    a = abs_py.copy()
    for i in ORDER_ROWS:
        a[i] = abs_ref[i]
    add("snap_order_rows_8", a, rows_snapped=[int(i) for i in ORDER_ROWS])
    for k in GREEDY_PREFIX_MILESTONES:
        if k > len(greedy_rows):
            continue
        a = abs_py.copy()
        for i in greedy_rows[:k]:
            a[i] = float(abs_ref[i])
        add(
            f"snap_greedy_prefix_{k}",
            a,
            rows_snapped=[int(i) for i in greedy_rows[:k]],
        )
    a = np.asarray(abs_ref, dtype=np.float64).copy()
    add("full_ref_absv_hybrid", a)
    return rows


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c 2d5f8b dlaqr0 order] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c 2d5f8b dlaqr0 order] missing oracle blocks", file=sys.stderr)
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
    ref_pair = _stage(
        ROW_LO_0, ROW_HI_0, float(abs_ref[ROW_LO_0]), float(abs_ref[ROW_HI_0])
    )
    ref_leader = int(ref_pair["leader_0based"])

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
    sweep_raw = dtrevc3_debug_get_qr0_sweep_table(max_n=48)

    w_pp, v_pp = apply_matlab_spectral_postprocess(w_v, v_v)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_py = dp["absv"]
    py_pair = _stage(
        ROW_LO_0, ROW_HI_0, float(abs_py[ROW_LO_0]), float(abs_py[ROW_HI_0])
    )

    pipeline = {
        "1_post_DGEHRD": _stage(
            ROW_LO_0,
            ROW_HI_0,
            dbg["post_dgehrd_hess_col_abs_13"],
            dbg["post_dgehrd_hess_col_abs_44"],
        ),
        "2_post_DORGHR": _stage(
            ROW_LO_0,
            ROW_HI_0,
            dbg["post_dorghr_q_col_abs_13"],
            dbg["post_dorghr_q_col_abs_44"],
        ),
        "2a_post_DLAQR0_in_VR_col": _stage(
            ROW_LO_0,
            ROW_HI_0,
            dbg["dlaqr0_in_vr_col_abs_13"],
            dbg["dlaqr0_in_vr_col_abs_44"],
        ),
        "2b_post_DLAQR0_out_schur_VR_col": _stage(
            ROW_LO_0,
            ROW_HI_0,
            dbg["dlaqr0_out_vr_col_abs_13"],
            dbg["dlaqr0_out_vr_col_abs_44"],
        ),
        "3_post_DHSEQR": _stage(
            ROW_LO_0,
            ROW_HI_0,
            dbg["post_dhseqr_schur_vr_col_abs_13"],
            dbg["post_dhseqr_schur_vr_col_abs_44"],
        ),
        "6_final_pp": py_pair,
    }

    sweep_rows: list[dict[str, Any]] = []
    first_nonzero_sweep: int | None = None
    for row in sweep_raw["rows"]:
        a_lo = float(row["abs_13"])
        a_hi = float(row["abs_44"])
        if first_nonzero_sweep is None and (a_lo > 0.0 or a_hi > 0.0):
            first_nonzero_sweep = int(row["sweep"])
        sweep_rows.append(
            {
                "sweep": int(row["sweep"]),
                "route": int(row["route"]),
                "route_name": row["route_name"],
                "it": int(row["it"]),
                "abs_lo": a_lo,
                "abs_hi": a_hi,
                "leader_0based": _leader(ROW_LO_0, ROW_HI_0, a_lo, a_hi),
                "diff_lo_minus_hi": a_lo - a_hi,
            }
        )

    sweep_flip = _first_sweep_leader_flip(
        sweep_rows, ref_leader=ref_leader, row_lo=ROW_LO_0, row_hi=ROW_HI_0
    )
    pipeline_flip = _first_leader_flip_ladder(pipeline, ref_leader=ref_leader)

    greedy_rows = _greedy_snap_order(abs_py, abs_ref)
    greedy_close = len(greedy_rows)
    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    for k, i in enumerate(greedy_rows):
        hyb[i] = float(abs_ref[i])
        if _mismatch_count(order_ref, _sort_abs_descend_matlab_like(hyb)) == 0:
            greedy_close = k + 1
            break

    row_table = [
        {
            "index": int(i),
            "abs_ref": float(abs_ref[i]),
            "abs_py": float(abs_py[i]),
            "delta_py_minus_ref": float(abs_py[i] - abs_ref[i]),
        }
        for i in ORDER_ROWS
    ]

    mm = _mismatch_count(order_ref, dp["order"])
    replays = _replay_oracles(abs_py, abs_ref, order_ref, greedy_rows)

    endpoint = sweep_rows[-1] if sweep_rows else None
    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.2 E3c-b-c-b2-c",
        "sub_hash": HASH,
        "backend": resolve_backend(),
        "row_pair_0based": [ROW_LO_0, ROW_HI_0],
        "kmax_hook_rows_0based": list(KMAX_HOOK_ROWS),
        "fortran_dbg_col": fortran_col,
        "j_ref_0based": j_ref,
        "order_mismatch_count": mm,
        "greedy_close_snap_count": int(greedy_close),
        "greedy_snap_order_head": [int(i) for i in greedy_rows[:12]],
        "first_mismatch_default": first_order_mismatch(
            order_ref, dp["order"], abs_ref, abs_py
        ),
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_got": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "ref_pair_at_jmax": ref_pair,
        "py_pair_at_jmax": py_pair,
        "pipeline_ladder_rank1_pair": pipeline,
        "first_leader_flip_pipeline": pipeline_flip,
        "dlaqr0_sweep_table": {
            "count": int(sweep_raw["count"]),
            "first_lo_gt_hi_sweep": int(sweep_raw["first_13gt44_sweep"]),
            "first_hi_gt_lo_sweep": int(sweep_raw["first_44gt13_sweep"]),
            "first_nonzero_sweep": first_nonzero_sweep,
            "first_leader_flip": sweep_flip,
            "endpoint_matches_dlaqr0_out": (
                endpoint is not None
                and abs(endpoint["abs_lo"] - pipeline["2b_post_DLAQR0_out_schur_VR_col"]["abs_lo"])
                < 1e-12
                and abs(endpoint["abs_hi"] - pipeline["2b_post_DLAQR0_out_schur_VR_col"]["abs_hi"])
                < 1e-12
            ),
            "rows_head": sweep_rows[:12],
            "rows_tail": sweep_rows[-3:] if len(sweep_rows) >= 3 else sweep_rows,
        },
        "order_row_table": row_table,
        "replay_oracles": replays,
        "oracle_kind": "wide_column_absv_drift_dlaqr0_out",
        "compute_patch_hint": (
            "K88: rank-1 pair 48/13 leader flips at DLAQR0_out; per-sweep table "
            "locates intra-DLAQR0 sweep; compare to kmax hook rows 44/13 (K66)."
        ),
    }

    out = (
        path.parent
        / "DEMAtariIII_fsl_backward_entry4_eig_e3c_2d5f8b_dlaqr0_order_pipeline_ladder.json"
    )
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    sf = sweep_flip or {}
    pf = pipeline_flip or {}
    ro = {r["replay"]: r for r in replays}
    print(
        f"[e3c 2d5f8b dlaqr0 order] mm={mm}/90 rank1={dp['order'][1]} vs {order_ref[1]} "
        f"pipe_flip={pf.get('site')} sweep_flip={sf.get('sweep')} "
        f"first_nz_sweep={first_nonzero_sweep} greedy_close={greedy_close} "
        f"pair_snap={ro['snap_pair_48_13_to_ref']['mismatch_count']}"
    )
    print(f"[e3c 2d5f8b dlaqr0 order] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
