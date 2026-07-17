"""Oracle tests: spm_set_goals_optim vs fidelity and vs MATLAB."""

from __future__ import annotations

import copy

import pytest

from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _pull_mdp_from_matlab,
)
from tests.oracle.toolbox.DEM.test_spm_RDP_basin import _build_entry8_boundary


@pytest.fixture
def dem_eng(eng):
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


def test_spm_set_goals_optim_matches_fidelity(dem_eng):
    _build_entry8_boundary(dem_eng, training_t=10000, n_outer=2)
    mdp_in = copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8"))
    mdp_f = spm_set_goals(copy.deepcopy(mdp_in), [2, 3], [32, -32])
    mdp_o = spm_set_goals_optim(copy.deepcopy(mdp_in), [2, 3], [32, -32])
    _assert_mdp_full_equal(mdp_f, mdp_o, 1)


@pytest.mark.slow
def test_spm_set_goals_optim_matches_matlab(dem_eng):
    _build_entry8_boundary(dem_eng)
    dem_eng.eval("MDP = spm_set_goals(rgms_mdp8,[2,3],[rgms_C,-rgms_C]);", nargout=0)
    mdp_mat = _pull_mdp_from_matlab(dem_eng, "MDP")
    mdp_py = spm_set_goals_optim(
        copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8")), [2, 3], [32, -32]
    )
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)
