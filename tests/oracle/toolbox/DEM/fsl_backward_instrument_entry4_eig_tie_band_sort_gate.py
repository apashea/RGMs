#!/usr/bin/env python3
"""Entry 4 B5.3 — T0 gate with optional ``RGMS_EIG_SPECTRAL_ABS_TIE_BAND_SORT`` (``eig.md`` §4.1)."""
from __future__ import annotations

import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES


def main() -> int:
    os.environ.pop("RGMS_EIG_NOBALANCE_PRINCIPAL_REFINE", None)
    os.environ["RGMS_EIG_SPECTRAL_ABS_TIE_BAND_SORT"] = "1"
    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[tie-band gate] missing oracle blocks", file=sys.stderr)
        return 2
    with path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    order_ok = 0
    fail_hashes: list[str] = []
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
        if np.array_equal(dr["order"], dp["order"]):
            order_ok += 1
        else:
            fail_hashes.append(str(blk.get("sub_hash", "")))
    n = len(blocks)
    known = set(KNOWN_FAIL_HASHES)
    seven_ok = len(known - set(fail_hashes))
    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "env": "RGMS_EIG_SPECTRAL_ABS_TIE_BAND_SORT=1",
        "order_ok": order_ok,
        "n_blocks": n,
        "seven_fail_order_ok": seven_ok,
        "fail_hashes": fail_hashes,
        "known_fail_matches": sorted(set(fail_hashes) & known),
    }
    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_tie_band_sort_gate.json"
    out.write_text(__import__("json").dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[tie-band gate] order={order_ok}/{n} seven_ok={seven_ok}/7")
    return 0 if order_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
