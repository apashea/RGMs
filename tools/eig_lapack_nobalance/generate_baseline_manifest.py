#!/usr/bin/env python3
"""Regenerate Entry 4 Option B baseline SHA256 manifest (see eig.md §26)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SCOPE: dict[str, list[str]] = {
    "production_compute_frozen": [
        "python_src/toolbox/DEM/spm_rgm_group.py",
        "python_src/toolbox/DEM/spm_faster_structure_learning.py",
        "python_src/toolbox/DEM/spm_RDP_sort.py",
        "matlab_compat.py",
    ],
    "experiment_utils_may_change": [
        "python_src/utils/eig_nobalance.py",
        "python_src/utils/eig_layout_research.py",
        "python_src/utils/eig_principal_fixture.py",
        "python_src/utils/eig_lapack_nobalance/__init__.py",
        "python_src/utils/eig_lapack_nobalance/wrapper.py",
        "python_src/utils/eig_lapack_nobalance/README.md",
    ],
    "experiment_tools_may_change": [
        "eig.md",
        "tools/eig_lapack_nobalance/build_windows.ps1",
        "tools/eig_lapack_nobalance/src/rgms_eig_nobalance.f",
    ],
    "hooks_measurement_only": [
        "python_src/toolbox/DEM/fsl_backward_entry4.py",
        "python_src/toolbox/DEM/dem_atariiii_entry4.py",
        "tests/oracle/toolbox/DEM/fsl_backward_run_entry4_isolated.py",
    ],
    "t0_tests_instruments": [
        "tests/oracle/test_eig_nobalance.py",
        "tests/oracle/toolbox/DEM/entry4_eig_diagnosis.py",
        "tests/oracle/toolbox/DEM/entry4_eig_dump_paths.py",
        "tests/oracle/toolbox/DEM/entry4_eig_principal_fixture.py",
        "tests/oracle/toolbox/DEM/fsl_backward_instrument_entry4_eig_geevx_vendored_gate.py",
        "tests/oracle/toolbox/DEM/fsl_backward_instrument_entry4_eig_native_status.py",
    ],
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    commit = os.popen("git rev-parse HEAD").read().strip()
    branch = os.popen("git branch --show-current").read().strip()
    files: dict[str, dict] = {}
    missing: list[str] = []
    for group, paths in SCOPE.items():
        for rel in paths:
            p = REPO / rel
            if not p.is_file():
                missing.append(rel)
                continue
            files[rel] = {
                "sha256": _sha256(p),
                "bytes": p.stat().st_size,
                "group": group,
            }
    out = {
        "experiment_id": "entry4_eig_option_b_vendored_dgeevx",
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "git_branch": branch,
        "git_commit": commit,
        "policy": "production spm_rgm_group default eig=scipy frozen until B3 58/58",
        "files": files,
        "missing": missing,
    }
    dest = REPO / "notes" / "entry4_eig_option_b_baseline_manifest.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {dest} ({len(files)} files, {len(missing)} missing)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
