from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_VB_prune import spm_MDP_VB_prune
from tests.helpers.compare import assert_matlab_match


def test_spm_MDP_VB_prune_default_mi_oracle(dem_eng):
    qA = np.array([[3.0, 1.0, 2.0], [1.0, 4.0, 2.0]])
    pA = np.array([[2.0, 2.0, 1.0], [1.0, 3.0, 2.0]])

    qA_matlab, pA_matlab = dem_eng.spm_MDP_VB_prune(
        matlab.double(qA.tolist()),
        matlab.double(pA.tolist()),
        nargout=2,
    )
    qA_python, pA_python = spm_MDP_VB_prune(qA, pA)

    assert_matlab_match(qA_matlab, qA_python)
    assert_matlab_match(pA_matlab, pA_python)


def test_spm_MDP_VB_prune_default_prior_oracle(dem_eng):
    qA = np.array([[3.0, 1.0, 2.0], [1.0, 4.0, 2.0]])

    qA_matlab, pA_matlab = dem_eng.spm_MDP_VB_prune(
        matlab.double(qA.tolist()),
        nargout=2,
    )
    qA_python, pA_python = spm_MDP_VB_prune(qA)

    assert_matlab_match(qA_matlab, qA_python)
    assert_matlab_match(pA_matlab, pA_python)


def test_spm_MDP_VB_prune_scalar_prior_oracle(dem_eng):
    qA = np.array([[3.0, 1.0, 2.0], [1.0, 4.0, 2.0]])

    qA_matlab, pA_matlab = dem_eng.spm_MDP_VB_prune(
        matlab.double(qA.tolist()),
        2.0,
        nargout=2,
    )
    qA_python, pA_python = spm_MDP_VB_prune(qA, 2.0)

    assert_matlab_match(qA_matlab, qA_python)
    assert_matlab_match(pA_matlab, pA_python)


def test_spm_MDP_VB_prune_simple_oracle(dem_eng):
    dem_eng.eval(
        "qA_spm_MDP_VB_prune = [3 1 2; 1 4 2];"
        "pA_spm_MDP_VB_prune = [2 2 1; 1 3 2];"
        "[qA_out_spm_MDP_VB_prune,pA_out_spm_MDP_VB_prune] = "
        "spm_MDP_VB_prune(qA_spm_MDP_VB_prune,pA_spm_MDP_VB_prune,0,0,[],'SIMPLE');",
        nargout=0,
    )
    qA = np.array([[3.0, 1.0, 2.0], [1.0, 4.0, 2.0]])
    pA = np.array([[2.0, 2.0, 1.0], [1.0, 3.0, 2.0]])

    qA_python, pA_python = spm_MDP_VB_prune(qA, pA, 0, 0, [], "SIMPLE")

    assert_matlab_match(dem_eng.eval("qA_out_spm_MDP_VB_prune"), qA_python)
    assert_matlab_match(dem_eng.eval("pA_out_spm_MDP_VB_prune"), pA_python)


def test_spm_MDP_VB_prune_contracted_factor_oracle(dem_eng):
    dem_eng.eval(
        "qA_spm_MDP_VB_prune = reshape(2:9,[2 2 2]);"
        "pA_spm_MDP_VB_prune = ones(2,2,2)*2;"
        "[qA_out_spm_MDP_VB_prune,pA_out_spm_MDP_VB_prune] = "
        "spm_MDP_VB_prune(qA_spm_MDP_VB_prune,pA_spm_MDP_VB_prune,1,1,[],'MI');",
        nargout=0,
    )
    qA = np.arange(2.0, 10.0).reshape((2, 2, 2), order="F")
    pA = np.ones((2, 2, 2)) * 2

    qA_python, pA_python = spm_MDP_VB_prune(qA, pA, 1, 1, [], "MI")

    assert_matlab_match(dem_eng.eval("qA_out_spm_MDP_VB_prune"), qA_python)
    assert_matlab_match(dem_eng.eval("pA_out_spm_MDP_VB_prune"), pA_python)


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)
