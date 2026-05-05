"""Oracle tests: spm_index.m vs python_src.toolbox.DEM.spm_index."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_index import spm_index
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    return eng


def test_spm_index_singleton_product_one_oracle(dem_eng):
    dem_eng.eval("ind_m = spm_index([1], 1);", nargout=0)
    ind_m = dem_eng.eval("ind_m")
    ind_p = spm_index([1], 1)
    assert_matlab_match(ind_m, ind_p)


def test_spm_index_two_dims_product_one_oracle(dem_eng):
    dem_eng.eval("ind_m = spm_index([1 1], 1);", nargout=0)
    ind_m = dem_eng.eval("ind_m")
    ind_p = spm_index([1, 1], 1)
    assert_matlab_match(ind_m, ind_p)


def test_spm_index_2d_oracle(dem_eng):
    dem_eng.eval("ind_m = spm_index([2 3], 4);", nargout=0)
    ind_m = dem_eng.eval("ind_m")
    ind_p = spm_index([2, 3], 4)
    assert_matlab_match(ind_m, ind_p)


def test_spm_index_3d_oracle(dem_eng):
    dem_eng.eval("ind_m = spm_index([2 3 4], 5);", nargout=0)
    ind_m = dem_eng.eval("ind_m")
    ind_p = spm_index([2, 3, 4], 5)
    assert_matlab_match(ind_m, ind_p)


def test_spm_index_4d_oracle(dem_eng):
    dem_eng.eval("ind_m = spm_index([2 3 4 5], 47);", nargout=0)
    ind_m = dem_eng.eval("ind_m")
    ind_p = spm_index([2, 3, 4, 5], 47)
    assert_matlab_match(ind_m, ind_p)


def test_spm_index_len1_errors_like_matlab():
    with pytest.raises(ValueError):
        spm_index([2], 1)
