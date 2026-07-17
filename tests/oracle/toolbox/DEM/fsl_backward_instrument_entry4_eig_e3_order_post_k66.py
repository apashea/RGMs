#!/usr/bin/env python3
"""Entry 4 E3 — post-K66 ``order`` mismatch taxonomy on vendored path (``eig.md`` §4.1 E3).

After **K66** (`2d5f8b…` ``kmax`` fix), ``jmax`` is **58/58** but ``order`` remains **51/58**
on default sort. Reports per seven-fail hash:

- ``kmax`` / ``jmax`` vs MATLAB dump
- default vs ULP tie-band ``order`` (counterfactual)
- first-rank mismatch + failure kind
- ``2d5f8b…`` plateau tier head (max-tier vs sub-tier counts)
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
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

PLATEAU_RTOL = 1e-14
MODE_B_HASH = "2d5f8b838be81f21"
MODE_B_PLATEAU_HEAD = (13, 23, 25, 29, 42, 44, 48, 55, 57, 61, 63, 68, 70, 74)


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


def _plateau_tier_summary(absv: np.ndarray, *, rtol: float = PLATEAU_RTOL) -> dict[str, Any]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    if a.size == 0:
        return {"absv_max": 0.0, "n_at_max": 0, "n_sub_tier": 0, "head": []}
    m = float(np.max(a))
    tol = max(1e-300, rtol * max(m, 1.0))
    head = []
    for idx in MODE_B_PLATEAU_HEAD:
        if 0 <= idx < a.size:
            head.append(
                {
                    "index": int(idx),
                    "abs": float(a[idx]),
                    "delta_from_max": float(a[idx] - m),
                    "on_max_tier": bool(abs(a[idx] - m) <= tol),
                }
            )
    n_at_max = int(np.sum(np.abs(a - m) <= tol))
    sub_tol = max(1e-300, 2.0 * tol)
    n_sub = int(np.sum((a < m - tol) & (a >= m - sub_tol)))
    return {
        "absv_max": m,
        "tol": tol,
        "n_at_max": n_at_max,
        "n_sub_tier": n_sub,
        "head": head,
    }


def _classify_failure(
    *,
    kmax_match: bool,
    mismatch: dict[str, Any] | None,
    order_ok_default: bool,
    order_ok_tie_band: bool,
) -> str:
    if order_ok_default:
        return "order_ok"
    if order_ok_tie_band and not order_ok_default:
        return "tier_reorder_tie_band_fixable"
    if not kmax_match:
        return "kmax_mismatch"
    if mismatch is None:
        return "length_mismatch"
    ar = float(mismatch["absv_ref"])
    ag = float(mismatch["absv_got"])
    tol = max(1e-300, PLATEAU_RTOL * max(ar, ag, 1.0))
    if abs(ar - ag) <= tol:
        return "tie_plateau_reorder"
    return "absv_ulp_reorder"


def _score_block(blk: dict[str, Any], *, tie_band: bool) -> dict[str, Any]:
    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    with _tie_band_env(tie_band):
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
    kmax_ref = int(np.argmax(dr["absv"]))
    kmax_got = int(np.argmax(dp["absv"]))
    mismatch = first_order_mismatch(dr["order"], dp["order"], dr["absv"], dp["absv"])
    if mismatch is not None and mismatch.get("note") != "length_mismatch":
        ar = float(mismatch["absv_ref"])
        ag = float(mismatch["absv_got"])
        tol = max(1e-300, PLATEAU_RTOL * max(ar, ag, 1.0))
        mismatch = dict(mismatch)
        mismatch["absv_equal_at_ulp"] = bool(abs(ar - ag) <= tol)
    return {
        "sub_hash": str(blk.get("sub_hash", "")),
        "jmax_match": bool(dr["jmax"] == dp["jmax"]),
        "kmax_ref": kmax_ref,
        "kmax_got": kmax_got,
        "kmax_match": bool(kmax_ref == kmax_got),
        "order_ok": bool(np.array_equal(dr["order"], dp["order"])),
        "order_first_mismatch": mismatch,
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3 order post-K66] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3 order post-K66] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    seven_rows: list[dict[str, Any]] = []
    for blk in blocks:
        h = str(blk.get("sub_hash", ""))
        if h not in KNOWN_FAIL_HASHES:
            continue
        default = _score_block(blk, tie_band=False)
        tie = _score_block(blk, tie_band=True)
        row = {
            **default,
            "order_ok_tie_band": tie["order_ok"],
            "failure_kind": _classify_failure(
                kmax_match=default["kmax_match"],
                mismatch=default["order_first_mismatch"],
                order_ok_default=default["order_ok"],
                order_ok_tie_band=tie["order_ok"],
            ),
        }
        if h == MODE_B_HASH:
            sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
            w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
            v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
            with _tie_band_env(False):
                w_py, v_py = eig_nobalance(sub)
                dr = rgm_spectral_decisions(sub, w_ref, v_ref)
                dp = rgm_spectral_decisions(sub, w_py, v_py)
            row["plateau_tier_ref"] = _plateau_tier_summary(dr["absv"])
            row["plateau_tier_py"] = _plateau_tier_summary(dp["absv"])
        seven_rows.append(row)

    full_default = sum(
        1
        for blk in blocks
        if _score_block(blk, tie_band=False)["order_ok"]
    )
    full_tie = sum(1 for blk in blocks if _score_block(blk, tie_band=True)["order_ok"])

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3",
        "backend": resolve_backend(),
        "post_k66": True,
        "summary": {
            "full_order_default": full_default,
            "full_order_tie_band": full_tie,
            "n_blocks": len(blocks),
            "seven_fail_default": sum(1 for r in seven_rows if r["order_ok"]),
            "seven_fail_tie_band": sum(1 for r in seven_rows if r["order_ok_tie_band"]),
        },
        "seven_fail_rows": seven_rows,
    }
    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3_order_post_k66.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    s = payload["summary"]
    print(
        f"[e3 order post-K66] default order={s['full_order_default']}/{s['n_blocks']} "
        f"tie_band={s['full_order_tie_band']}/{s['n_blocks']} "
        f"seven={s['seven_fail_default']}/7 tie_band={s['seven_fail_tie_band']}/7"
    )
    for row in seven_rows:
        print(
            f"  {row['sub_hash'][:8]} kind={row['failure_kind']} "
            f"kmax={row['kmax_ref']}->{row['kmax_got']} "
            f"order={row['order_ok']} tb={row['order_ok_tie_band']}"
        )
    print(f"[e3 order post-K66] wrote={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
