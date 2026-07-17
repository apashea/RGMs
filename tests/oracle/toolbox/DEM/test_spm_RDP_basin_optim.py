"""Oracle tests: spm_RDP_basin_optim vs fidelity (v0 equivalence fork)."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_RDP_basin_optim import spm_RDP_basin_optim
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from tests.oracle.toolbox.DEM.test_spm_RDP_basin import _build_entry8_boundary
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _pull_mdp_from_matlab,
)


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


def test_spm_RDP_basin_optim_matches_fidelity(dem_eng):
    """Same inputs → identical ``mdp``, ``d``, ``o``, ``h`` (v0 fork)."""
    _build_entry8_boundary(dem_eng, training_t=10000, n_outer=2)
    mdp_in = copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8"))
    mdp_f, d_f, o_f, h_f, c_f = spm_RDP_basin(mdp_in, [2, 3], [32, -32])
    mdp_o, d_o, o_o, h_o, c_o = spm_RDP_basin_optim(
        copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8")), [2, 3], [32, -32]
    )
    _assert_mdp_full_equal(mdp_f, mdp_o, 1)
    assert np.array_equal(np.asarray(d_f, dtype=bool).ravel(order="F"), np.asarray(d_o, dtype=bool).ravel(order="F"))
    assert np.array_equal(np.asarray(o_f, dtype=bool).ravel(order="F"), np.asarray(o_o, dtype=bool).ravel(order="F"))
    assert np.array_equal(np.asarray(h_f, dtype=np.int64).ravel(order="F"), np.asarray(h_o, dtype=np.int64).ravel(order="F"))
    assert np.array_equal(np.asarray(c_f, dtype=np.int64).ravel(order="F"), np.asarray(c_o, dtype=np.int64).ravel(order="F"))


@pytest.mark.slow
def test_spm_RDP_basin_optim_matches_matlab(dem_eng):
    """Optim fork matches MATLAB ``spm_RDP_basin`` oracle."""
    _build_entry8_boundary(dem_eng)
    dem_eng.eval(
        "[MDPb,dm,om,hm] = spm_RDP_basin(rgms_mdp8,[2,3],[rgms_C,-rgms_C]);",
        nargout=0,
    )
    mdp_mat = _pull_mdp_from_matlab(dem_eng, "MDPb")
    d_mat = np.asarray(dem_eng.eval("dm"), dtype=bool).ravel(order="F")
    o_mat = np.asarray(dem_eng.eval("om"), dtype=bool).ravel(order="F")
    h_mat = np.asarray(dem_eng.eval("hm"), dtype=np.int64).ravel(order="F")

    mdp_py, d_py, o_py, h_py, _ = spm_RDP_basin_optim(
        copy.deepcopy(_pull_mdp_from_matlab(dem_eng, "rgms_mdp8")), [2, 3], [32, -32]
    )
    _assert_mdp_full_equal(mdp_py, mdp_mat, 1)
    assert np.array_equal(np.asarray(d_py, dtype=bool).ravel(order="F"), d_mat)
    assert np.array_equal(np.asarray(o_py, dtype=bool).ravel(order="F"), o_mat)
    assert np.array_equal(np.asarray(h_py, dtype=np.int64).ravel(order="F"), h_mat)
