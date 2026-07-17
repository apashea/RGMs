"""FSL backward Entry 4 — structure learning from MATLAB-fed ``PDP.O(:,1:1000)``.

Sign-off: isolated run (MATLAB hooks default on) + compare vs ``MDP_pre_entry5`` in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``. Do not waive **511 vs 485** on this lane.
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from python_src.toolbox.DEM.fsl_backward_entry4 import run_entry4_from_boundary

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_PRE4 = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"
_ISOLATED = _DEM / "fsl_backward_run_entry4_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry4_pkl_to_mat.py"


@pytest.fixture
def fsl_backward_pre4_boundary() -> dict:
    if not _PRE4.is_file():
        pytest.skip(
            f"missing {_PRE4} — run fsl_backward_materialize_mdp_pre_entry4_pkl.py "
            "(requires MDP_pre_entry5 patch on .mat)"
        )
    with _PRE4.open("rb") as f:
        return pickle.load(f)


@pytest.mark.slow
def test_fsl_backward_entry4_run_from_boundary_in_process(fsl_backward_pre4_boundary) -> None:
    """Library API with MATLAB structure learning (default FSL sign-off lane)."""
    import matlab.engine

    from python_src.toolbox.DEM.fsl_backward_entry4 import run_entry4_matlab_structure_learning

    dem_path = _REPO / "matlab_src" / "toolbox" / "DEM"
    mat_path = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    eng = matlab.engine.start_matlab()
    try:
        eng.addpath(str(_REPO), nargout=0)
        eng.addpath(str(_REPO / "matlab_src"), nargout=0)
        eng.addpath(str(dem_path), nargout=0)
        eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
        out = run_entry4_matlab_structure_learning(eng, authority_mat_path=mat_path)
    finally:
        eng.quit()
    assert isinstance(out["mdp"], list)
    assert out["Nm"] == len(out["mdp"])
    assert out["Nm"] >= 1


@pytest.mark.slow
def test_fsl_backward_entry4_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry4_isolated exited {iso.returncode}\n"
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
            f"fsl_backward_compare_entry4 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
