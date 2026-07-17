#!/usr/bin/env python3
"""Entry 4 E3c-b-c — five tier-reorder hashes greedy ``absv`` snap ladder (``eig.md`` §4.1).

Post-**K78**; documents minimum snap counts for default-path ``order`` closure per hash.
No Fortran changes.
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
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

TIER_REORDER = [
    "2d5f8b838be81f21",
    "4ab4f22de6228a3a",
    "6abd2a358966b834",
    "7d978bc6b89bde7b",
    "7f1469f5003eebf1",
]


def _greedy_close(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> tuple[int, list[int]]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    order_idx = [int(i) for i in np.argsort(-d)]
    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    for k, i in enumerate(order_idx):
        hyb[i] = float(abs_ref[i])
        mm = int(np.sum(_sort_abs_descend_matlab_like(hyb) != order_ref))
        if mm == 0:
            return k + 1, order_idx[: k + 1]
    return len(order_idx), order_idx


def _analyze_one(blk: dict[str, Any]) -> dict[str, Any]:
    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    w_py, v_py = eig_nobalance(sub)
    w_pp, v_pp = apply_matlab_spectral_postprocess(w_py, v_py)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    n = int(sub.shape[0])
    order_ok = bool(np.array_equal(dr["order"], dp["order"]))
    mm = int(np.sum(dr["order"] != dp["order"]))
    gc, snap_rows = _greedy_close(dp["absv"], dr["absv"], dr["order"])
    d = np.abs(dp["absv"] - dr["absv"])
    return {
        "sub_hash": str(blk.get("sub_hash", "")),
        "n": n,
        "order_ok_default": order_ok,
        "order_mismatch_count": mm,
        "greedy_close_snap_count": gc,
        "greedy_snap_rows_head": snap_rows[:12],
        "max_absv_diff": float(np.max(d)),
        "n_rows_gt_1e-15": int(np.sum(d > 1e-15)),
        "first_mismatch": first_order_mismatch(
            dr["order"], dp["order"], dr["absv"], dp["absv"]
        ),
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c tier snap] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c tier snap] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blocks = [b for b in pickle.load(f)["blocks"] if str(b.get("sub_hash", "")) in TIER_REORDER]

    rows = [_analyze_one(blk) for blk in blocks]
    rows.sort(key=lambda r: r["sub_hash"])

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3c-b-c",
        "backend": resolve_backend(),
        "summary": {
            "tier_reorder_count": len(rows),
            "order_ok_default": sum(1 for r in rows if r["order_ok_default"]),
            "greedy_snap_max": max((r["greedy_close_snap_count"] for r in rows), default=0),
            "greedy_snap_min": min((r["greedy_close_snap_count"] for r in rows), default=0),
        },
        "rows": rows,
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3c_tier_reorder_snap_ladder.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    s = payload["summary"]
    print(
        f"[e3c tier snap] order_ok={s['order_ok_default']}/{s['tier_reorder_count']} "
        f"greedy_min={s['greedy_snap_min']} greedy_max={s['greedy_snap_max']}"
    )
    for row in rows:
        print(
            f"  {row['sub_hash'][:8]} ok={row['order_ok_default']} "
            f"mm={row['order_mismatch_count']}/{row['n']} greedy={row['greedy_close_snap_count']}"
        )
    print(f"[e3c tier snap] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
