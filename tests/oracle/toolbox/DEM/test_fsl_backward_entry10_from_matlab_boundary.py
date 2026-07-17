"""FSL backward Entry 10 — MATLAB-fed boundary (``MDP_pre_entry10`` → post-10 ``MDP``).

**Split validation:** isolated runner defaults to MATLAB ``eig(B,'nobalance')`` injection; compare
checks ``validation.eig_source=matlab_engine`` and full ``MDP`` parity vs ``MDP_pre_entry11``.
Native eig alone is diagnostic only (**484** vs **485** at full scale). See
``Atari_example.md`` § **Entry 10 — eigen limitation (project-critical)**.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_ISOLATED = _DEM / "fsl_backward_run_entry10_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry10_pkl_to_mat.py"


@pytest.mark.slow
def test_fsl_backward_entry10_matlab_boundary_compare():
    env = {**os.environ, "RGMS_FSL_RDP_SORT_MATLAB_EIG": "1"}
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry10_isolated exited {iso.returncode}\n"
            f"stdout:\n{iso.stdout}\nstderr:\n{iso.stderr}"
        )
    proc = subprocess.run(
        [sys.executable, str(_COMPARE)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"fsl_backward_compare_entry10 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
