#!/usr/bin/env python3
"""Entry 4 E3c-b-a — seven-fail default-path ``order`` taxonomy (``eig.md`` §4.1).

Post-**K76** (``kmax`` **58/58**). Per seven-fail hash: mismatch counts, ``absv`` drift
stats, ref-``absv`` graft replay (does perfect ``absv`` parity close ``order``?),
and ``oracle_kind`` for **E3c-b** fork queue. No Fortran changes.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available
from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

PLATEAU_RTOL = 1e-14
ABSV_THRESHOLDS = (1e-15, 1e-14, 1e-13)


@contextmanager
def _tie_band_env(enabled: bool) -> Iterator[None]:
    key = "RGMS_EIG_SPECTRAL_ABS_TIE_BAND_SORT"
    prev = os.environ.get(key)
    if enabled:
        os.environ[key] = "1"
    else:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def _absv_diff_stats(abs_ref: np.ndarray, abs_py: np.ndarray) -> dict[str, Any]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    out: dict[str, Any] = {
        "max_abs_diff": float(np.max(d)) if d.size else 0.0,
        "mean_abs_diff": float(np.mean(d)) if d.size else 0.0,
    }
    for thr in ABSV_THRESHOLDS:
        out[f"n_rows_gt_{thr:g}"] = int(np.sum(d > thr))
    return out


def _graft_ref_absv_order_ok(dr: dict[str, Any]) -> bool:
    order_graft = _sort_abs_descend_matlab_like(dr["absv"])
    return bool(np.array_equal(order_graft, dr["order"]))


def _classify_oracle_kind(
    *,
    order_ok_default: bool,
    order_ok_tie_band: bool,
    graft_ref_absv_order_ok: bool,
    mismatch_count: int,
    n: int,
    first_mismatch: dict[str, Any] | None,
    kmax_match: bool,
) -> str:
    if order_ok_default:
        return "order_ok"
    if order_ok_tie_band and not order_ok_default:
        return "tier_reorder_tie_band_fixable"
    if not kmax_match:
        return "kmax_mismatch"
    if first_mismatch is not None and first_mismatch.get("absv_equal_at_ulp"):
        return "tie_plateau_reorder"
    if graft_ref_absv_order_ok:
        if mismatch_count >= max(8, int(0.75 * n)):
            return "full_column_absv_drift"
        return "absv_graft_fixable"
    return "absv_ulp_reorder"


def _decisions_for_block(
    blk: dict[str, Any], *, tie_band: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    with _tie_band_env(tie_band):
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
    return dr, dp


def _analyze_one(blk: dict[str, Any]) -> dict[str, Any]:
    n = int(np.asarray(blk["sub_mi"]).shape[0])
    dr, dp = _decisions_for_block(blk, tie_band=False)
    dr_tb, dp_tb = _decisions_for_block(blk, tie_band=True)

    mismatch_def = first_order_mismatch(dr["order"], dp["order"], dr["absv"], dp["absv"])
    if mismatch_def is not None and mismatch_def.get("note") != "length_mismatch":
        ar = float(mismatch_def["absv_ref"])
        ag = float(mismatch_def["absv_got"])
        tol = max(1e-300, PLATEAU_RTOL * max(ar, ag, 1.0))
        mismatch_def = dict(mismatch_def)
        mismatch_def["absv_equal_at_ulp"] = bool(abs(ar - ag) <= tol)

    mm_def = _mismatch_count(dr["order"], dp["order"])
    mm_tb = _mismatch_count(dr["order"], dp_tb["order"])
    graft_ok = _graft_ref_absv_order_ok(dr)
    order_ok_def = bool(np.array_equal(dr["order"], dp["order"]))
    order_ok_tb = bool(np.array_equal(dr_tb["order"], dp_tb["order"]))

    kmax_match = bool(np.argmax(dr["absv"]) == np.argmax(dp["absv"]))
    kind = _classify_oracle_kind(
        order_ok_default=order_ok_def,
        order_ok_tie_band=order_ok_tb,
        graft_ref_absv_order_ok=graft_ok,
        mismatch_count=mm_def,
        n=n,
        first_mismatch=mismatch_def,
        kmax_match=kmax_match,
    )

    return {
        "sub_hash": str(blk.get("sub_hash", "")),
        "n": n,
        "jmax_match": bool(dr["jmax"] == dp["jmax"]),
        "kmax_ref": int(np.argmax(dr["absv"])),
        "kmax_got": int(np.argmax(dp["absv"])),
        "kmax_match": kmax_match,
        "order_ok_default": order_ok_def,
        "order_ok_tie_band": order_ok_tb,
        "order_mismatch_count_default": mm_def,
        "order_mismatch_count_tie_band": mm_tb,
        "graft_ref_absv_order_ok": graft_ok,
        "oracle_kind": kind,
        "absv_diff": _absv_diff_stats(dr["absv"], dp["absv"]),
        "first_mismatch_default": mismatch_def,
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c seven order] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c seven order] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    rows = [_analyze_one(blk) for blk in blocks if str(blk.get("sub_hash", "")) in KNOWN_FAIL_HASHES]
    rows.sort(key=lambda r: r["sub_hash"])

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3c-b-a",
        "backend": resolve_backend(),
        "post_k76": True,
        "summary": {
            "seven_fail_count": len(rows),
            "order_ok_default": sum(1 for r in rows if r["order_ok_default"]),
            "order_ok_tie_band": sum(1 for r in rows if r["order_ok_tie_band"]),
            "graft_fixable_count": sum(
                1 for r in rows if r["oracle_kind"] == "absv_graft_fixable"
            ),
            "full_column_drift_count": sum(
                1 for r in rows if r["oracle_kind"] == "full_column_absv_drift"
            ),
            "tie_band_fixable_count": sum(
                1 for r in rows if r["oracle_kind"] == "tier_reorder_tie_band_fixable"
            ),
        },
        "rows": rows,
    }
    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3c_seven_order_taxonomy.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    s = payload["summary"]
    print(
        f"[e3c seven order] seven={s['seven_fail_count']} "
        f"order_default={s['order_ok_default']}/7 "
        f"tie_band={s['order_ok_tie_band']}/7 "
        f"graft_fixable={s['graft_fixable_count']} "
        f"full_drift={s['full_column_drift_count']} "
        f"tb_fixable={s['tie_band_fixable_count']}"
    )
    for row in rows:
        d = row["absv_diff"]
        print(
            f"  {row['sub_hash'][:8]} kind={row['oracle_kind']} "
            f"mm={row['order_mismatch_count_default']}/{row['n']} "
            f"graft={row['graft_ref_absv_order_ok']} "
            f"max_d={d['max_abs_diff']:.3e} n>1e-14={d['n_rows_gt_1e-14']}"
        )
    print(f"[e3c seven order] wrote={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
