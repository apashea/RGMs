"""FSL backward Track A — integrated 1–12 (opt-in; long)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_RUN = Path(__file__).resolve().parent / "fsl_backward_run_entry1_12_integration.py"
_VALIDATE = Path(__file__).resolve().parent / "fsl_backward_validate_entry1_12_integration.py"

_ENABLED = str(os.getenv("RGMS_FSL_RUN_ENTRY1_12_INTEGRATION", "")).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


@pytest.mark.slow
@pytest.mark.skipif(
    not _ENABLED,
    reason="Set RGMS_FSL_RUN_ENTRY1_12_INTEGRATION=1 for Track A 1–12 integration (~60–90+ min)",
)
def test_fsl_backward_track_a_entry1_12_integration_subprocess():
    env = {**os.environ, "RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS": "1"}
    run = subprocess.run(
        [sys.executable, str(_RUN)],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry1_12_integration exited {run.returncode}\n"
            f"stderr:\n{run.stderr}"
        )
    val = subprocess.run(
        [sys.executable, str(_VALIDATE)],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if val.returncode != 0:
        raise AssertionError(
            f"fsl_backward_validate_entry1_12_integration exited {val.returncode}\n"
            f"stderr:\n{val.stderr}"
        )
