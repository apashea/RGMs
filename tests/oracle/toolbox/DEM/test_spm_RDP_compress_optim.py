"""Oracle tests: spm_RDP_compress_optim vs fidelity and vs MATLAB."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_RDP_compress_optim import (
    spm_RDP_compress_columns_first,
    spm_RDP_compress_optim,
)
from python_src.toolbox.DEM.spm_RDP_compress import spm_RDP_compress
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _mat_full_numeric,
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


def test_spm_RDP_compress_optim_matches_fidelity(dem_eng):
    _build_entry8_boundary(dem_eng, training_t=10000, n_outer=2)
    dem_eng.eval(
        "MDP = spm_set_goals(rgms_mdp8,[2,3],[rgms_C,-rgms_C]); "
        "h = MDP{end}.id.hid; c = MDP{end}.id.cid; "
        "B = sum(MDP{end}.b{1},3) > 0; B(c,:) = false; "
        "Nt = 32; Ns = size(B,1); P = false(Nt,Ns); P(1,h) = true; "
        "for t = 1:Nt, p = any(B(P(t,:),:),1)'; P(t+1,:) = p; if ~any(p), break, end, end; "
        "Nt = 1; C = false(Nt,Ns); C(1,h) = true; "
        "for t = 1:Nt, p = any(B(:,C(t,:)),2); C(t+1,:) = p; if ~any(p), break, end, end; "
        "R = true(1,Ns); R(c) = false; R = R & (any(P,1) | any(C,1)); j = R; "
        "Rfull = speye(Ns,Ns); Rj = full(Rfull(:,j));",
        nargout=0,
    )
    mdp_in = _pull_mdp_from_matlab(dem_eng, "MDP")
    rj = _mat_full_numeric(dem_eng, "Rj")
    mdp_f = spm_RDP_compress(copy.deepcopy(mdp_in), rj, "first")
    mdp_o = spm_RDP_compress_optim(copy.deepcopy(mdp_in), rj, "first")
    _assert_mdp_full_equal(mdp_f, mdp_o, 1)


def test_spm_RDP_compress_columns_first_matches_fidelity_first(dem_eng):
    """Tier Cc: direct ``j`` indices ≡ fidelity ``speye(:,j)`` top compress."""
    import copy

    from scipy import sparse

    _build_entry8_boundary(dem_eng, training_t=10000, n_outer=2)
    dem_eng.eval(
        "MDP = spm_set_goals(rgms_mdp8,[2,3],[rgms_C,-rgms_C]); "
        "h = MDP{end}.id.hid; c = MDP{end}.id.cid; "
        "B = sum(MDP{end}.b{1},3) > 0; B(c,:) = false; "
        "Nt = 32; Ns = size(B,1); P = false(Nt,Ns); P(1,h) = true; "
        "for t = 1:Nt, p = any(B(P(t,:),:),1)'; P(t+1,:) = p; if ~any(p), break, end, end; "
        "Nt = 1; C = false(Nt,Ns); C(1,h) = true; "
        "for t = 1:Nt, p = any(B(:,C(t,:)),2); C(t+1,:) = p; if ~any(p), break, end, end; "
        "R = true(1,Ns); R(c) = false; R = R & (any(P,1) | any(C,1)); j = find(R); "
        "Rfull = speye(Ns,Ns);",
        nargout=0,
    )
    mdp_in = _pull_mdp_from_matlab(dem_eng, "MDP")
    j_py = np.asarray(dem_eng.eval("j"), dtype=np.int64).ravel(order="F") - 1
    ns = int(dem_eng.eval("Ns"))
    r_sub = sparse.eye(ns, ns, dtype=np.float64, format="csr")[:, j_py]
    mdp_f = spm_RDP_compress(copy.deepcopy(mdp_in), r_sub, "first")
    mdp_o = spm_RDP_compress_columns_first(copy.deepcopy(mdp_in), j_py)
    _assert_mdp_full_equal(mdp_f, mdp_o, 1)


@pytest.mark.slow
def test_spm_RDP_compress_optim_matches_matlab(dem_eng):
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
    mdp_py = spm_RDP_compress_optim(copy.deepcopy(mdp_in), rj, "first")
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)
