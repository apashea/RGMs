"""MATLAB oracle: DEMO2 post–NR ``RDP`` assembly (calls 3 and 4) vs ``python_src_demo2``."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
from python_src_demo2.toolbox.DEM.dem_atariiii_post12 import (
    assemble_rdp_call3_post_nr_loop,
    assemble_rdp_call4_post_nr_loop,
)
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    _matlab_build_entry10_training_end_boundary,
)
from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _pull_mdp_from_matlab,
)
from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal
from python_src_demo2.toolbox.DEM.spm_RDP_sort import spm_RDP_sort


def _matlab_nested_rdp_to_py(eng, var_expr: str, tmp_path: Path) -> dict[str, Any]:
    """Load nested ``RDP`` from live MATLAB workspace via v7 ``save`` (complete field set)."""
    from scipy.io import loadmat

    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    mat_file = tmp_path / "demo2_asm_rdp.mat"
    mat_posix = str(mat_file).replace("\\", "/")
    eng.eval(f"RDP = {var_expr}; save('{mat_posix}','RDP');", nargout=0)
    raw = loadmat(str(mat_file))
    return mat_nested_to_py(raw["RDP"])


def _pull_post_nr_mdp_from_matlab(eng, expr: str, tmp_path: Path) -> list[dict[str, Any]]:
    """Pull post–NR ``MDP`` including generative-process attach on level 1."""
    mdp_py = _pull_mdp_from_matlab(eng, expr)
    mat_file = tmp_path / "demo2_mdp1.mat"
    mat_posix = str(mat_file).replace("\\", "/")
    eng.eval(f"MDP1 = {expr}{{1}}; save('{mat_posix}','MDP1');", nargout=0)
    from scipy.io import loadmat

    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    m1 = mat_nested_to_py(loadmat(str(mat_file))["MDP1"])
    for key in ("GA", "GB", "GU", "GD", "ID", "chi"):
        if key in m1:
            mdp_py[0][key] = copy.deepcopy(m1[key])
    return mdp_py


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


def _matlab_build_post_nr_mdp_one_game(dem_eng, training_t: int, n_outer: int) -> None:
    """Preamble + one active-inference game → ``rgms_mdp_post_nr`` (pre call 3/4 assembly)."""
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
        "rgms_mdp_post_nr = MDP;",
        nargout=0,
    )


def _matlab_assemble_call3(dem_eng) -> None:
    dem_eng.eval(
        "RDP = spm_RDP_sort(rgms_mdp_post_nr); "
        "RDP = spm_set_goals(RDP,[2,3],[C,-C]); "
        "RDP = spm_set_costs(RDP,[2,3],[C,-C]); "
        "RDP = spm_mdp2rdp(RDP,0,1/256); "
        "RDP.T = 128; "
        "rgms_rdp_call3_mat = RDP;",
        nargout=0,
    )


def _matlab_assemble_call4(dem_eng) -> None:
    dem_eng.eval(
        "RDP = spm_RDP_sort(rgms_mdp_post_nr); "
        "RDP = spm_RDP_MI(RDP); "
        "RDP = spm_set_goals(RDP,[2,3],[C,-C]); "
        "RDP = spm_set_costs(RDP,[2,3],[C,-C]); "
        "RDP = spm_mdp2rdp(RDP,0,1/256); "
        "RDP.T = 128; "
        "rgms_rdp_call4_mat = RDP;",
        nargout=0,
    )


def _vb_prep_pair(py_rdp: dict, mat_rdp: dict) -> tuple[dict, dict]:
    py_vb = entry12_rdp_for_vb_from_mat_nested(copy.deepcopy(py_rdp))
    mat_vb = entry12_rdp_for_vb_from_mat_nested(copy.deepcopy(mat_rdp))
    return py_vb, mat_vb


@pytest.mark.slow
def test_demo2_post_nr_sort_input_matches_matlab(dem_eng, tmp_path) -> None:
    """Post–NR ``rgms_mdp_post_nr`` pull matches MATLAB before call 3/4 assembly."""
    training_t = 1000
    n_outer = 2
    _matlab_build_post_nr_mdp_one_game(dem_eng, training_t, n_outer)
    dem_eng.eval("rgms_mdp_sorted = spm_RDP_sort(rgms_mdp_post_nr);", nargout=0)
    mdp_py = _pull_post_nr_mdp_from_matlab(dem_eng, "rgms_mdp_post_nr", tmp_path)
    matlab_eig = _make_matlab_spm_RDP_sort_eig(dem_eng)
    mdp_sort_py, _j = spm_RDP_sort(copy.deepcopy(mdp_py), eig=matlab_eig)
    mdp_sort_mat = _pull_mdp_from_matlab(dem_eng, "rgms_mdp_sorted")
    _assert_mdp_full_equal(mdp_sort_py, mdp_sort_mat, 1)


@pytest.mark.slow
def test_demo2_assemble_rdp_call3_matches_matlab_post_nr(dem_eng, tmp_path) -> None:
    """``assemble_rdp_call3_post_nr_loop`` matches MATLAB ``entry12_dem_call3`` ledger."""
    training_t = 1000
    n_outer = 2
    ns = 256.0
    _matlab_build_post_nr_mdp_one_game(dem_eng, training_t, n_outer)
    _matlab_assemble_call3(dem_eng)

    c_val = float(dem_eng.eval("C", nargout=1))
    mdp_py = _pull_post_nr_mdp_from_matlab(dem_eng, "rgms_mdp_post_nr", tmp_path)
    matlab_eig = _make_matlab_spm_RDP_sort_eig(dem_eng)
    rdp_py = assemble_rdp_call3_post_nr_loop(mdp_py, c_val, ns, eig=matlab_eig)
    rdp_mat = _matlab_nested_rdp_to_py(dem_eng, "rgms_rdp_call3_mat", tmp_path)

    py_vb, mat_vb = _vb_prep_pair(rdp_py, rdp_mat)
    _assert_nested_rdp_equal(py_vb, mat_vb, "DEMO2 call3 VB-input RDP")


@pytest.mark.slow
def test_demo2_assemble_rdp_call4_matches_matlab_post_nr(dem_eng, tmp_path) -> None:
    """``assemble_rdp_call4_post_nr_loop`` matches MATLAB ``entry12_dem_call4`` ledger."""
    training_t = 1000
    n_outer = 2
    ns = 256.0
    _matlab_build_post_nr_mdp_one_game(dem_eng, training_t, n_outer)
    _matlab_assemble_call4(dem_eng)

    c_val = float(dem_eng.eval("C", nargout=1))
    mdp_py = _pull_post_nr_mdp_from_matlab(dem_eng, "rgms_mdp_post_nr", tmp_path)
    matlab_eig = _make_matlab_spm_RDP_sort_eig(dem_eng)
    rdp_py = assemble_rdp_call4_post_nr_loop(mdp_py, c_val, ns, eig=matlab_eig)
    rdp_mat = _matlab_nested_rdp_to_py(dem_eng, "rgms_rdp_call4_mat", tmp_path)

    py_vb, mat_vb = _vb_prep_pair(rdp_py, rdp_mat)
    _assert_nested_rdp_equal(py_vb, mat_vb, "DEMO2 call4 VB-input RDP")
