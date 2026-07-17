#!/usr/bin/env python3
"""Entry 4 — consolidated native ``eig_nobalance`` parity status (``eig.md`` §24)."""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_dump_report_txt,
    entry4_eig_oracle_blocks_pkl,
)
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[entry4 native status] missing oracle blocks pkl", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    order_ok = 0
    jmax_ok = 0
    fail_hashes: list[str] = []
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
        if dr["jmax"] == dp["jmax"]:
            jmax_ok += 1
        if np.array_equal(dr["order"], dp["order"]):
            order_ok += 1
        else:
            fail_hashes.append(str(blk.get("sub_hash", "")))

    utc = datetime.now(timezone.utc).isoformat()
    payload = {
        "utc": utc,
        "backend": resolve_backend(),
        "t0_oracle_blocks": {
            "n_blocks": len(blocks),
            "order_match": order_ok,
            "jmax_match": jmax_ok,
            "order_fail_hashes": fail_hashes,
            "known_fail_set": sorted(KNOWN_FAIL_HASHES),
            "known_fail_matches": sorted(set(fail_hashes) & KNOWN_FAIL_HASHES),
        },
        "native_lane": {
            "env_enable_fsl": "RGMS_FSL_RGM_NATIVE_EIG_NOBALANCE=1",
            "runner": "fsl_backward_run_entry4_isolated.py",
            "t0_order": f"{order_ok}/{len(blocks)}",
            "diagnostic_only_until_58_58": order_ok < len(blocks),
            "engine_probe": "solver_gap_matlab_eig_required (eig.md §28)",
        },
        "validation_ceiling": {
            "env_enable": "RGMS_EIG_NOBALANCE_PRINCIPAL_FIXTURE=1",
            "expected_order_match": 58,
            "test": "test_eig_nobalance_58_58_with_principal_fixture",
        },
        "blockers": [
            "solver_vendor: SciPy/OpenBLAS and vendored reference dgeevx both 51/58 order",
            "principal_column_absv_ulps on seven high-tie symmetric blocks",
            "post_process_closed: live MATLAB eig + same policy is 58/58 (§28)",
        ],
        "toolchain_next": [
            "MKL or MATLAB-linked LAPACK with geevx balanc=N (see notes/entry4_eig_toolchain_research.md)",
            "Do not add utils sort/heuristic/hash patches",
        ],
    }

    out_path = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_native_status.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    lines = [
        f"=== Entry 4 eig native status {utc} ===",
        f"order={order_ok}/{len(blocks)} jmax={jmax_ok}/{len(blocks)} backend={payload['backend']}",
        f"wrote={out_path}",
    ]
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for ln in lines:
        print(f"[entry4 native status] {ln}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
