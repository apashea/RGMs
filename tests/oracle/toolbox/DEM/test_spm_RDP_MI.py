"""Per-file oracle: ``spm_RDP_MI`` MATLAB vs Python (OPTIM1FULL / call 4 dependency)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from python_src.toolbox.DEM.spm_RDP_MI import spm_RDP_MI
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _pull_mdp_from_matlab,
)
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    _matlab_build_entry10_training_end_boundary,
)


@pytest.fixture
def dem_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath(str(repo / "matlab_custom" / "entry12"), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


def _matlab_build_post_nr_mdp_for_mi(dem_eng, training_t: int, n_outer: int) -> None:
    """Preamble through Entry 9, one active-inference game, then MI oracle vars."""
    _matlab_build_entry10_training_end_boundary(dem_eng, training_t, n_outer)
    dem_eng.eval(
        "MDP = rgms_mdp9; "
        "MDP{1}.GA = GDP.A; MDP{1}.GB = GDP.B; MDP{1}.GU = GDP.U; "
        "MDP{1}.GD = GDP.D; MDP{1}.ID = GDP.id; MDP{1}.chi = 512; "
        "NT = 256; NS = 256; "
        "RDP = spm_set_goals(MDP,[2,3],[C,-C]); "
        "RDP = spm_set_costs(RDP,[2,3],[C,-C]); "
        "RDP = spm_mdp2rdp(RDP,0,1/NS); "
        "RDP.T = fix(NT/Ne); "
        "OPTIONS = struct('B',0,'C',0,'D',0,'N',0,'O',1,'P',0,'Y',1); "
        "PDP = spm_MDP_VB_XXX(RDP, OPTIONS, false, false); "
        "O = PDP.Q.O{1}; "
        "t = 0:(NT - Ne); "
        "for s = 1:Ne, "
        "MDP = spm_merge_structure_learning(O(:,t + s),MDP); "
        "end; "
        "[MDP,~,~,~] = spm_RDP_basin(MDP,[2,3],[C,-C]); "
        "rgms_mdp_mi_in = spm_RDP_sort(MDP); "
        "rgms_mdp_mi_out = spm_RDP_MI(rgms_mdp_mi_in);",
        nargout=0,
    )


@pytest.mark.slow
def test_spm_RDP_MI_matches_matlab_post_nr_mdp(dem_eng):
    """``spm_RDP_MI`` on post–NR-loop sorted ``MDP`` matches MATLAB (one game)."""
    training_t = 1000
    n_outer = 2
    _matlab_build_post_nr_mdp_for_mi(dem_eng, training_t, n_outer)
    mdp_mat = _pull_mdp_from_matlab(dem_eng, "rgms_mdp_mi_out")
    mdp_in_py = _pull_mdp_from_matlab(dem_eng, "rgms_mdp_mi_in")
    mdp_py = spm_RDP_MI(copy.deepcopy(mdp_in_py))
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)
