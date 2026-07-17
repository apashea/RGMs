"""FSL backward — Entry 11 ``RDP`` must pass Entry 12 VB + Validation 12 (frozen MATLAB authority).

Requires canonical Entry 12 fixtures (``rgms_canonical``): script **1b** mats, ``vb_rand_buf``,
``DEMAtariIII_XXX_12_rdp.mat``. Does **not** modify Entry 12 sources or overwrite script **3** PKLs.

See ``fsl_backward_validate_entry11_through_entry12.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_SCRIPT = Path(__file__).resolve().parent / "fsl_backward_validate_entry11_through_entry12.py"


@pytest.mark.slow
def test_fsl_backward_entry11_rdp_passes_entry12_vb_and_validation12():
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"fsl_backward_validate_entry11_through_entry12 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
