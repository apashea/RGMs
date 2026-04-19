from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from python_src.toolbox.DEM.spm_dir_reduce import spm_dir_reduce
from tests.helpers.compare import assert_matlab_match


def test_spm_dir_reduce_likelihood_oracle(dem_eng):
    dem_eng.eval(
        "a_spm_dir_reduce = {[2 1; 1 3], [1 2; 4 1]};"
        "R_spm_dir_reduce = spm_dir_reduce(a_spm_dir_reduce);",
        nargout=0,
    )
    a = [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]

    R_python = spm_dir_reduce(a)

    assert sparse.issparse(R_python) == bool(dem_eng.eval("issparse(R_spm_dir_reduce)"))
    assert_matlab_match(dem_eng.eval("full(R_spm_dir_reduce)"), R_python.toarray())


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)
