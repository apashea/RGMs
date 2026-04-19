from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from matlab_compat import full
from python_src.toolbox.DEM.spm_information_distance import spm_information_distance
from tests.helpers.compare import assert_matlab_match


def test_spm_information_distance_cell_likelihood_oracle(dem_eng):
    dem_eng.eval(
        "a_spm_information_distance = {[2 1; 1 3], [1 2; 4 1]};"
        "[D_spm_information_distance,C_spm_information_distance] = "
        "spm_information_distance(a_spm_information_distance);",
        nargout=0,
    )
    a = [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]

    D_python, C_python = spm_information_distance(a)

    assert_matlab_match(dem_eng.eval("D_spm_information_distance"), D_python)
    assert_matlab_match(
        dem_eng.eval("full(C_spm_information_distance)"),
        full(C_python),
    )


def test_spm_information_distance_c_sparse_status_oracle(dem_eng):
    dem_eng.eval(
        "a_spm_information_distance = {[2 1; 1 3], [1 2; 4 1]};"
        "[~,C_spm_information_distance] = "
        "spm_information_distance(a_spm_information_distance);",
        nargout=0,
    )
    a = [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]

    _, C_python = spm_information_distance(a)

    assert sparse.issparse(C_python) == bool(
        dem_eng.eval("issparse(C_spm_information_distance)")
    )


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)
