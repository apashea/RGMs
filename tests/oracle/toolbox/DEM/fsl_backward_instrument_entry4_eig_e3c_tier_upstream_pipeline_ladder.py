#!/usr/bin/env python3
"""Entry 4 E3c-b-c-b2-b — tier-reorder upstream pipeline ladders (``eig.md`` §4.2 K87).

Post-**K85**/**K86**. ``2d5f8b``, ``6abd2a``, ``7d978`` first-mismatch row-pairs through
DGEEVX pipeline snaps; compares causal site to **K85** ``7f1469`` / **K82** ``866`` ``DHSEQR``
pattern. No Fortran changes.
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

CASES: dict[str, dict[str, Any]] = {
    "2d5f8b838be81f21": {
        "row_lo_0": 48,
        "row_hi_0": 13,
        "mismatch_rank": 1,
        "greedy_close_k80": 80,
        "order_rows": (48, 13, 44, 25, 23, 72, 21, 29),
    },
    "6abd2a358966b834": {
        "row_lo_0": 105,
        "row_hi_0": 1,
        "mismatch_rank": 58,
        "greedy_close_k80": 83,
        "order_rows": (105, 1, 48, 36, 60, 96, 24, 2),
    },
    "7d978bc6b89bde7b": {
        "row_lo_0": 23,
        "row_hi_0": 25,
        "mismatch_rank": 1,
        "greedy_close_k80": 64,
        "order_rows": (23, 25, 11, 29, 59, 21, 64, 45),
    },
}


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
    abs_py: np.ndarray,
    abs_ref: np.ndarray,
    order_ref: np.ndarray,
    *,
    row_lo: int,
    row_hi: int,
    order_rows: tuple[int, ...],
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
    a[row_lo] = abs_ref[row_lo]
    a[row_hi] = abs_ref[row_hi]
    add(f"snap_pair_{row_lo}_{row_hi}_to_ref", a)
    a = abs_py.copy()
    for i in order_rows:
        a[i] = abs_ref[i]
    add("snap_order_rows_to_ref", a)
    return rows


def _run_case(blk: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    row_lo = int(spec["row_lo_0"])
    row_hi = int(spec["row_hi_0"])
    order_rows = tuple(int(i) for i in spec["order_rows"])

    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    j_ref = int(dr["jmax"])
    abs_ref = dr["absv"]
    order_ref = dr["order"]
    ref_pair = _stage(row_lo, row_hi, float(abs_ref[row_lo]), float(abs_ref[row_hi]))

    w_probe, _ = eig_real_nobalance(sub)
    w_probe = np.asarray(w_probe, dtype=np.complex128).ravel(order="F")
    perm = np.argsort(np.abs(w_probe), kind="mergesort")
    raw_col = int(perm[j_ref])
    fortran_col = raw_col + 1

    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    dtrevc3_debug_set_row_pair(row_lo + 1, row_hi + 1)
    w_v, v_v = eig_real_nobalance(sub)
    dbg = dtrevc3_debug_get()

    w_pp, v_pp = apply_matlab_spectral_postprocess(w_v, v_v)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_py = dp["absv"]
    py_pair = _stage(row_lo, row_hi, float(abs_py[row_lo]), float(abs_py[row_hi]))

    ladder = {
        "1_post_DGEHRD": _stage(
            row_lo,
            row_hi,
            dbg["post_dgehrd_hess_col_abs_13"],
            dbg["post_dgehrd_hess_col_abs_44"],
        ),
        "2_post_DORGHR": _stage(
            row_lo,
            row_hi,
            dbg["post_dorghr_q_col_abs_13"],
            dbg["post_dorghr_q_col_abs_44"],
        ),
        "2a_post_DLAQR0_in_VR_col": _stage(
            row_lo,
            row_hi,
            dbg["dlaqr0_in_vr_col_abs_13"],
            dbg["dlaqr0_in_vr_col_abs_44"],
        ),
        "2b_post_DLAQR0_out_schur_VR_col": _stage(
            row_lo,
            row_hi,
            dbg["dlaqr0_out_vr_col_abs_13"],
            dbg["dlaqr0_out_vr_col_abs_44"],
        ),
        "3_post_DHSEQR": _stage(
            row_lo,
            row_hi,
            dbg["post_dhseqr_schur_vr_col_abs_13"],
            dbg["post_dhseqr_schur_vr_col_abs_44"],
        ),
        "4_DTREVC3_pre_IDAMAX": _stage(
            row_lo,
            row_hi,
            dbg["post_bt_pre_idamax_abs_13"],
            dbg["post_bt_pre_idamax_abs_44"],
        ),
        "5_DTREVC3_post_normalize": _stage(
            row_lo, row_hi, dbg["post_abs_13"], dbg["post_abs_44"]
        ),
        "6_final_pp": py_pair,
    }

    row_table = []
    for i in order_rows:
        row_table.append(
            {
                "index": int(i),
                "abs_ref": float(abs_ref[i]),
                "abs_py": float(abs_py[i]),
                "delta_py_minus_ref": float(abs_py[i] - abs_ref[i]),
            }
        )

    mm = _mismatch_count(order_ref, dp["order"])
    n = int(sub.shape[0])
    flip = _first_leader_flip(ladder, ref_leader=ref_pair["leader_0based"])
    div = _first_abs_divergence(
        ladder, ref_diff=float(ref_pair["diff_lo_minus_hi"])
    )
    replays = _replay_oracles(
        abs_py,
        abs_ref,
        order_ref,
        row_lo=row_lo,
        row_hi=row_hi,
        order_rows=order_rows,
    )

    return {
        "sub_hash": blk["sub_hash"],
        "n": n,
        "row_pair_0based": [row_lo, row_hi],
        "mismatch_rank": int(spec["mismatch_rank"]),
        "fortran_dbg_col": fortran_col,
        "raw_col_for_jref_0based": raw_col,
        "j_ref_0based": j_ref,
        "order_mismatch_count": mm,
        "greedy_close_snap_count_k80": int(spec["greedy_close_k80"]),
        "first_mismatch_default": first_order_mismatch(
            order_ref, dp["order"], abs_ref, abs_py
        ),
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_got": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "ref_pair_at_jmax": ref_pair,
        "py_pair_at_jmax": py_pair,
        "pipeline_ladder": ladder,
        "first_leader_flip_py": flip,
        "first_abs_divergence_from_ref_final": div,
        "order_row_table": row_table,
        "replay_oracles": replays,
        "oracle_kind": "wide_column_absv_drift",
        "dhseqr_causal_class": (
            flip is not None and flip.get("site") == "3_post_DHSEQR"
        ),
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c tier upstream] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c tier upstream] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blocks = {b["sub_hash"]: b for b in pickle.load(f)["blocks"]}

    rows: list[dict[str, Any]] = []
    for h, spec in CASES.items():
        if h not in blocks:
            print(f"[e3c tier upstream] missing block {h}", file=sys.stderr)
            return 2
        rows.append(_run_case(blocks[h], spec))

    dhseqr_count = sum(1 for r in rows if r["dhseqr_causal_class"])
    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.2 E3c-b-c-b2-b",
        "backend": resolve_backend(),
        "summary": {
            "case_count": len(rows),
            "dhseqr_flip_site_count": dhseqr_count,
            "compare_k85_7f1469": "3_post_DHSEQR",
            "compare_k82_866": "3_post_DHSEQR",
        },
        "rows": rows,
        "compute_patch_hint": (
            "K87 P2: compare tier-reorder upstream causal sites to 7f1469/866 DHSEQR; "
            "pair-only snap insufficient if replay worsens mm."
        ),
    }

    out = (
        path.parent
        / "DEMAtariIII_fsl_backward_entry4_eig_e3c_tier_upstream_pipeline_ladder.json"
    )
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for r in rows:
        flip = r.get("first_leader_flip_py") or {}
        div = r.get("first_abs_divergence_from_ref_final") or {}
        ro = r["replay_oracles"]
        ref_pair = r["ref_pair_at_jmax"]
        py_pair = r["py_pair_at_jmax"]
        print(
            f"[e3c tier upstream] {r['sub_hash'][:8]}… "
            f"mm={r['order_mismatch_count']}/{r['n']} "
            f"rank={r['mismatch_rank']} "
            f"ref_leader={ref_pair['leader_0based']} "
            f"py_leader={py_pair['leader_0based']} "
            f"flip={flip.get('site')} div={div.get('site')} "
            f"pair_snap={ro[1]['mismatch_count']} "
            f"dhseqr={r['dhseqr_causal_class']}"
        )
    print(
        f"[e3c tier upstream] dhseqr_site={dhseqr_count}/{len(rows)} "
        f"wrote {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
