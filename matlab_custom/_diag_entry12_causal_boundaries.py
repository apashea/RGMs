"""
DEPRECATED — do not extend.

**Universal Entry 12 parity probe:** ``tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py``
(script **4**). See ``Atari_example.md`` § **Entry 12 — universal probe (core reading)**.

This file existed from **2026-05-18** as a fast duplicate of the causal gate before Validation 12
ran that gate first. It is now a thin alias only. New inspection blocks belong in
``entry12_matlab_capture.py`` and are printed from script **4** (tee:
``matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt``).

Equivalent command::

    python tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py \\
        --coerce-sparse-to-dense-for-compare --entry12-causal-only
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPARE = ROOT / "tests" / "oracle" / "toolbox" / "DEM" / "XXX_12_compare_pdp_pkl_to_mat.py"


def main() -> int:
    print(
        "[deprecated] _diag_entry12_causal_boundaries.py — use Validation 12 (script 4) instead.\n"
        f"  -> python {COMPARE.relative_to(ROOT)} "
        "--coerce-sparse-to-dense-for-compare --entry12-causal-only\n",
        file=sys.stderr,
    )
    cmd = [
        sys.executable,
        str(COMPARE),
        "--coerce-sparse-to-dense-for-compare",
        "--entry12-causal-only",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
