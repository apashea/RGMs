"""Oracle tests for spm_set_goals / spm_RDP_compress / spm_RDP_basin."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from python_src.toolbox.DEM.spm_RDP_compress import spm_RDP_compress
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _mat_full_numeric,
    _pull_mdp_from_matlab,
)


@pytest.fixture
def dem_eng(eng):
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


def _build_entry8_boundary(dem_eng, training_t: int = 10000, n_outer: int = 2) -> None:
    dem_eng.eval(
        "rng(0,'twister'); "
        "Nr = 12; Nc = 9; Sc = 9; Nd = 4; C = 32; "
        "[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0); "
        "S = ones(4,3); S(1,:) = [Nr,Nc,1]; "
        f"GDP.tau = 1; GDP.T = {int(training_t)}; "
        "PDP = spm_MDP_generate(GDP); "
        "MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc); "
        "Nm = numel(MDP); Ne = max(2^(Nm - 1),1); "
        "for n = 1:Nm, "
        "for g = 1:numel(MDP{n}.a), MDP{n}.a{g} = []; end; "
        "for f = 1:numel(MDP{n}.b), MDP{n}.b{f} = []; end; "
        "end; "
        "r = find(PDP.o(GDP.id.reward,:) > 1); "
        "c = find(PDP.o(GDP.id.contraint,:) > 1); "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + Ne):(r(i) + Ne); "
        "if numel(t), "
        "for s = 1:Ne, "
        "MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP); "
        "end; "
        "end; "
        "end; "
        "NT = 100; "
        f"for ii = 1:{int(n_outer)}, "
        "t = (0:(NT + Ne)) + rem(ii,100 - 1)*NT; "
        "for s = 1:Ne, "
        "MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP); "
        "end; "
        "end; "
        "rgms_mdp8 = MDP; rgms_C = C;",
        nargout=0,
    )


@pytest.mark.slow
def test_spm_set_goals_oracle(dem_eng):
    _build_entry8_boundary(dem_eng)
    dem_eng.eval("MDP = spm_set_goals(rgms_mdp8,[2,3],[rgms_C,-rgms_C]);", nargout=0)
    mdp_mat = _pull_mdp_from_matlab(dem_eng, "MDP")
    mdp_py = spm_set_goals(copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8")), [2, 3], [32, -32])
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)


@pytest.mark.slow
def test_spm_RDP_compress_first_oracle(dem_eng):
    _build_entry8_boundary(dem_eng)
    dem_eng.eval(
        "MDP = spm_set_goals(rgms_mdp8,[2,3],[rgms_C,-rgms_C]); "
        "h = MDP{end}.id.hid; c = MDP{end}.id.cid; "
        "B = sum(MDP{end}.b{1},3) > 0; B(c,:) = false; "
        "Nt = 32; Ns = size(B,1); P = false(Nt,Ns); P(1,h) = true; "
        "for t = 1:Nt, p = any(B(P(t,:),:),1)'; P(t+1,:) = p; if ~any(p), break, end, end; "
        "Nt = 1; C = false(Nt,Ns); C(1,h) = true; "
        "for t = 1:Nt, p = any(B(:,C(t,:)),2); C(t+1,:) = p; if ~any(p), break, end, end; "
        "R = true(1,Ns); R(c) = false; R = R & (any(P,1) | any(C,1)); j = R; "
        "Rfull = speye(Ns,Ns); Rj = full(Rfull(:,j)); "
        "MDPc = spm_RDP_compress(MDP,Rfull(:,j),'first');",
        nargout=0,
    )
    mdp_in = _pull_mdp_from_matlab(dem_eng, "MDP")
    rj = _mat_full_numeric(dem_eng, "Rj")
    mdp_mat = _pull_mdp_from_matlab(dem_eng, "MDPc")
    mdp_py = spm_RDP_compress(copy.deepcopy(mdp_in), rj, "first")
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)


@pytest.mark.slow
def test_spm_RDP_basin_oracle(dem_eng):
    _build_entry8_boundary(dem_eng)
    dem_eng.eval(
        "[MDPb,dm,om,hm] = spm_RDP_basin(rgms_mdp8,[2,3],[rgms_C,-rgms_C]);",
        nargout=0,
    )
    mdp_mat = _pull_mdp_from_matlab(dem_eng, "MDPb")
    d_mat = np.asarray(dem_eng.eval("dm"), dtype=bool).ravel(order="F")
    o_mat = np.asarray(dem_eng.eval("om"), dtype=bool).ravel(order="F")
    h_mat = np.asarray(dem_eng.eval("hm"), dtype=np.int64).ravel(order="F")

    mdp_py, d_py, o_py, h_py, _ = spm_RDP_basin(copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8")), [2, 3], [32, -32])
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)
    assert np.array_equal(np.asarray(d_py, dtype=bool).ravel(order="F"), d_mat)
    assert np.array_equal(np.asarray(o_py, dtype=bool).ravel(order="F"), o_mat)
    assert np.array_equal(np.asarray(h_py, dtype=np.int64).ravel(order="F"), h_mat)
