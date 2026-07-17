"""Oracle tests: spm_unique_optim vs fidelity and vs MATLAB."""

from pathlib import Path

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_unique_optim import spm_unique_optim
from python_src.toolbox.DEM.spm_unique import spm_unique
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)


def _case_o():
    return [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]


def test_spm_unique_optim_matches_fidelity():
    o = _case_o()
    i_f, j_f = spm_unique(o)
    i_o, j_o = spm_unique_optim(o)
    assert_matlab_match(i_f, i_o)
    assert_matlab_match(j_f, j_o)


def test_spm_unique_optim_likelihood_oracle(dem_eng):
    dem_eng.eval(
        "O_spm_unique = {[2 1; 1 3], [1 2; 4 1]};"
        "[i_spm_unique,j_spm_unique] = spm_unique(O_spm_unique);",
        nargout=0,
    )
    i_python, j_python = spm_unique_optim(_case_o())
    assert_matlab_match(dem_eng.eval("i_spm_unique"), i_python)
    assert_matlab_match(dem_eng.eval("j_spm_unique"), j_python)
