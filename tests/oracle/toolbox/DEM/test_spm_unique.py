from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_unique import spm_unique
from tests.helpers.compare import assert_matlab_match


def test_spm_unique_likelihood_oracle(dem_eng):
    dem_eng.eval(
        "O_spm_unique = {[2 1; 1 3], [1 2; 4 1]};"
        "[i_spm_unique,j_spm_unique] = spm_unique(O_spm_unique);",
        nargout=0,
    )
    O = [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]

    i_python, j_python = spm_unique(O)

    assert_matlab_match(dem_eng.eval("i_spm_unique"), i_python)
    assert_matlab_match(dem_eng.eval("j_spm_unique"), j_python)


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)
