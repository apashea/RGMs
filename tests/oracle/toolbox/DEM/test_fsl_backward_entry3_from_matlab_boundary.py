"""FSL backward Entry 3 — ``spm_MDP_generate`` on ``rng(2)`` ledger.

Sign-off: isolated run (MATLAB generate default) + compare vs ``PDP_o`` / ``PDP_O`` in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_ISOLATED = _DEM / "fsl_backward_run_entry3_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry3_pkl_to_mat.py"
_MAT = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


@pytest.mark.slow
def test_fsl_backward_entry3_driver_replay_in_process() -> None:
    """Native driver ledger + ``dem_atari_rand_buf`` replay through Entry 3."""
    from tests.oracle.toolbox.DEM.fsl_backward_preflight_rand_k_entry3 import main as preflight_main

    from python_src.toolbox.DEM.fsl_backward_entry3 import run_entry3_driver_ledger_replay

    if not _MAT.is_file():
        pytest.skip(f"missing {_MAT}")

    if preflight_main() != 0:
        pytest.fail("fsl_backward_preflight_rand_k_entry3 failed")

    out = run_entry3_driver_ledger_replay()
    assert out.get("validation_lane") == "driver_ledger_replay"
    assert int(out["pdp"]["T"]) == 10000
    assert int(out["draws_used"]) == int(out["k_3"])


@pytest.mark.slow
def test_fsl_backward_entry3_run_from_boundary_in_process() -> None:
    """Library API with MATLAB generate (default FSL sign-off lane)."""
    import matlab.engine

    from python_src.toolbox.DEM.fsl_backward_entry3 import run_entry3_matlab_generate

    if not _MAT.is_file():
        pytest.skip(f"missing {_MAT}")

    dem_path = _REPO / "matlab_src" / "toolbox" / "DEM"
    eng = matlab.engine.start_matlab()
    try:
        eng.addpath(str(_REPO), nargout=0)
        eng.addpath(str(_REPO / "matlab_src"), nargout=0)
        eng.addpath(str(dem_path), nargout=0)
        eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
        out = run_entry3_matlab_generate(eng, authority_mat_path=_MAT)
    finally:
        eng.quit()
    assert "pdp" in out
    assert int(out["pdp"]["T"]) == 10000


@pytest.mark.slow
def test_fsl_backward_entry3_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry3_isolated exited {iso.returncode}\n"
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
            f"fsl_backward_compare_entry3 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
