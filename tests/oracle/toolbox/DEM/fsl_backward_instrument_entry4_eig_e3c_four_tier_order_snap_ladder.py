#!/usr/bin/env python3
"""Entry 4 E3c-b-c-b1 — four remaining tier-reorder ``order`` snap ladders (``eig.md`` §4.1).

Post-**K79** (``4ab4`` closed). Per hash: greedy close count, threshold snaps,
plateau/tier replay, and ``wide_column_absv_drift`` classification. No Fortran.
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

from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available
from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

FOUR_TIER = [
    "2d5f8b838be81f21",
    "6abd2a358966b834",
    "7d978bc6b89bde7b",
    "7f1469f5003eebf1",
]
PLATEAU_RTOL = 1e-14
THRESHOLDS = (0.0, 1e-17, 1e-16, 1e-15, 1e-14)


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def _plateau_indices(absv: np.ndarray) -> list[int]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    m = float(np.max(a))
    tol = max(1e-300, PLATEAU_RTOL * max(m, 1.0))
    return np.flatnonzero(np.abs(a - m) <= tol).astype(int).tolist()


def _greedy_close(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> tuple[int, list[int]]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    order_idx = [int(i) for i in np.argsort(-d)]
    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    for k, i in enumerate(order_idx):
        hyb[i] = float(abs_ref[i])
        if _mismatch_count(order_ref, _sort_abs_descend_matlab_like(hyb)) == 0:
            return k + 1, order_idx[: k + 1]
    return len(order_idx), order_idx


def _threshold_snaps(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> list[dict[str, Any]]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    rows: list[dict[str, Any]] = []
    for thr in THRESHOLDS:
        hyb = np.asarray(abs_py, dtype=np.float64).copy()
        mask = d > thr if thr > 0 else d >= 0
        n = int(np.sum(mask))
        for i in np.flatnonzero(mask):
            hyb[int(i)] = float(abs_ref[int(i)])
        rows.append(
            {
                "threshold": float(thr),
                "n_rows_snapped": n,
                "mismatch_count": _mismatch_count(
                    order_ref, _sort_abs_descend_matlab_like(hyb)
                ),
            }
        )
    return rows


def _analyze_one(blk: dict[str, Any]) -> dict[str, Any]:
    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    w_py, v_py = eig_nobalance(sub)
    w_pp, v_pp = apply_matlab_spectral_postprocess(w_py, v_py)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_ref = dr["absv"]
    abs_py = dp["absv"]
    order_ref = dr["order"]
    d = np.abs(abs_py - abs_ref)
    plat_ref = _plateau_indices(abs_ref)
    hyb_plat = np.asarray(abs_py, dtype=np.float64).copy()
    for i in plat_ref:
        hyb_plat[i] = float(abs_ref[i])
    gc, snap_rows = _greedy_close(abs_py, abs_ref, order_ref)
    mm_def = _mismatch_count(order_ref, dp["order"])
    kind = "wide_column_absv_drift" if gc >= max(8, int(0.5 * sub.shape[0])) else "absv_graft_fixable"
    return {
        "sub_hash": str(blk.get("sub_hash", "")),
        "n": int(sub.shape[0]),
        "jmax": int(dr["jmax"]),
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_got": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "order_mismatch_count_default": mm_def,
        "order_ok_default": bool(mm_def == 0),
        "greedy_close_snap_count": gc,
        "greedy_snap_rows_head": snap_rows[:12],
        "plateau_ref_count": len(plat_ref),
        "plateau_snap_mismatch_count": _mismatch_count(
            order_ref, _sort_abs_descend_matlab_like(hyb_plat)
        ),
        "threshold_snaps": _threshold_snaps(abs_py, abs_ref, order_ref),
        "max_absv_diff": float(np.max(d)),
        "n_rows_gt_1e-15": int(np.sum(d > 1e-15)),
        "first_mismatch_default": first_order_mismatch(
            order_ref, dp["order"], abs_ref, abs_py
        ),
        "oracle_kind": kind,
        "compute_patch_hint": (
            "Head/plateau/tier snap alone insufficient; needs column-wide absv "
            "fidelity (greedy close count large). Not rank-1 demote class."
        ),
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c four tier] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c four tier] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blocks = [b for b in pickle.load(f)["blocks"] if str(b.get("sub_hash", "")) in FOUR_TIER]

    rows = [_analyze_one(blk) for blk in blocks]
    rows.sort(key=lambda r: r["sub_hash"])

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3c-b-c-b1",
        "backend": resolve_backend(),
        "summary": {
            "four_tier_count": len(rows),
            "order_ok_default": sum(1 for r in rows if r["order_ok_default"]),
            "greedy_min": min((r["greedy_close_snap_count"] for r in rows), default=0),
            "greedy_max": max((r["greedy_close_snap_count"] for r in rows), default=0),
            "wide_drift_count": sum(
                1 for r in rows if r["oracle_kind"] == "wide_column_absv_drift"
            ),
        },
        "rows": rows,
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3c_four_tier_order_snap_ladder.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    s = payload["summary"]
    print(
        f"[e3c four tier] order_ok={s['order_ok_default']}/{s['four_tier_count']} "
        f"greedy={s['greedy_min']}..{s['greedy_max']} wide={s['wide_drift_count']}"
    )
    for row in rows:
        print(
            f"  {row['sub_hash'][:8]} greedy={row['greedy_close_snap_count']} "
            f"plat_snap_mm={row['plateau_snap_mismatch_count']} "
            f"kind={row['oracle_kind']}"
        )
    print(f"[e3c four tier] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
