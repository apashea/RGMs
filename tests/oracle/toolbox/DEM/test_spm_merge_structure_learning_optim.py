"""Oracle tests: spm_merge_structure_learning_optim vs fidelity (low-risk OPTIM1)."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_merge_structure_learning_optim import (
    spm_merge_structure_learning_optim,
)
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from tests.oracle.toolbox.DEM.test_spm_merge_structure_learning import (
    _matlab_case_eval,
    _python_case_inputs,
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


def _assert_merge_mdp_equal(ref: list, out: list) -> None:
    p_a = np.asarray(ref[0]["a"][0][0], dtype=np.float64)
    p_b = np.asarray(ref[0]["b"][0][0], dtype=np.float64)
    o_a = np.asarray(out[0]["a"][0][0], dtype=np.float64)
    o_b = np.asarray(out[0]["b"][0][0], dtype=np.float64)
    if p_b.ndim == 2:
        p_b = p_b[:, :, None]
    if o_b.ndim == 2:
        o_b = o_b[:, :, None]
    np.testing.assert_allclose(o_a, p_a, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(o_b, p_b, rtol=0.0, atol=1e-12)


@pytest.mark.parametrize("n_calls", [1, 2, 3])
def test_spm_merge_structure_learning_optim_matches_fidelity(n_calls: int):
    """Same ``O`` / ``MDP`` → identical ``a`` / ``b`` (v0 low-risk equivalence)."""
    o, mdp = _python_case_inputs()
    mdp_f = copy.deepcopy(mdp)
    mdp_o = copy.deepcopy(mdp)
    for _ in range(n_calls):
        mdp_f = spm_merge_structure_learning(o, mdp_f)
        mdp_o = spm_merge_structure_learning_optim(o, mdp_o)
    _assert_merge_mdp_equal(mdp_f, mdp_o)


def test_spm_merge_structure_learning_optim_as_o_cells_fast_path():
    """List-of-lists ``O`` is reused without copy; outputs still match fidelity."""
    o, mdp = _python_case_inputs()
    o_cells = [[np.asarray(x, dtype=np.float64) for x in row] for row in o]
    mdp_f = spm_merge_structure_learning(o_cells, copy.deepcopy(mdp))
    mdp_o = spm_merge_structure_learning_optim(o_cells, copy.deepcopy(mdp))
    _assert_merge_mdp_equal(mdp_f, mdp_o)


@pytest.mark.slow
@pytest.mark.parametrize("n_calls", [1, 2])
def test_spm_merge_structure_learning_optim_matches_matlab(dem_eng, n_calls: int):
    """Optim path matches MATLAB oracle (same case as fidelity test)."""
    o, mdp = _python_case_inputs()
    m_a, m_b = _matlab_case_eval(dem_eng, n_calls=n_calls)
    mdp_py = mdp
    for _ in range(n_calls):
        mdp_py = spm_merge_structure_learning_optim(o, mdp_py)
    p_a = np.asarray(mdp_py[0]["a"][0][0], dtype=np.float64)
    p_b = np.asarray(mdp_py[0]["b"][0][0], dtype=np.float64)
    if p_b.ndim == 2:
        p_b = p_b[:, :, None]
    np.testing.assert_allclose(p_a, m_a, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(p_b, m_b, rtol=0.0, atol=1e-12)
