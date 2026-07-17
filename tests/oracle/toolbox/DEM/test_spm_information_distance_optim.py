"""Oracle tests: spm_information_distance_optim vs fidelity and vs MATLAB."""

from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from matlab_compat import full
from python_src.optimized.toolbox.DEM.spm_information_distance_optim import (
    _dir_norm_dense_2d,
    _dir_norm_dense_2d_into,
    _is_merge_fast_combined,
    _merge_fast_cat_matrix,
    _merge_fast_cat_matrix_dirnorm,
    spm_information_distance_optim,
)
from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_information_distance import spm_information_distance
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)


def _case_a():
    return [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]


def test_spm_information_distance_optim_matches_fidelity():
    a = _case_a()
    d_f, c_f = spm_information_distance(a)
    d_o, c_o = spm_information_distance_optim(a)
    np.testing.assert_allclose(np.asarray(d_f), np.asarray(d_o), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(full(c_f), full(c_o), rtol=0.0, atol=1e-12)


def test_spm_information_distance_optim_cell_likelihood_oracle(dem_eng):
    dem_eng.eval(
        "a_spm_information_distance = {[2 1; 1 3], [1 2; 4 1]};"
        "[D_spm_information_distance,C_spm_information_distance] = "
        "spm_information_distance(a_spm_information_distance);",
        nargout=0,
    )
    d_python, c_python = spm_information_distance_optim(_case_a())
    assert_matlab_match(dem_eng.eval("D_spm_information_distance"), d_python)
    assert_matlab_match(
        dem_eng.eval("full(C_spm_information_distance)"),
        full(c_python),
    )


def test_merge_fast_dir_norm_dense_matches_spm_dir_norm():
    """Tier B2d/B2e guard: fused per-part normalize ≡ ``spm_dir_norm`` on dense blocks."""
    rng = np.random.default_rng(42)
    for _ in range(8):
        arr = rng.random((5, 7)) + 0.05
        ref = spm_dir_norm(arr)
        out = _dir_norm_dense_2d(arr)
        np.testing.assert_allclose(out, np.asarray(ref, dtype=np.float64), rtol=0.0, atol=1e-15)
    for _ in range(4):
        arr = rng.random((9, 1)) + 0.05
        ref = spm_dir_norm(arr)
        out = _dir_norm_dense_2d(arr)
        np.testing.assert_allclose(out, np.asarray(ref, dtype=np.float64), rtol=0.0, atol=1e-15)
    arr = np.array([[0.0, 2.0], [0.0, 1.0]], dtype=np.float64)
    ref = spm_dir_norm(arr)
    out = np.empty_like(arr)
    _dir_norm_dense_2d_into(out, arr)
    np.testing.assert_allclose(out, np.asarray(ref, dtype=np.float64), rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(_dir_norm_dense_2d(arr), np.asarray(ref, dtype=np.float64), rtol=0.0, atol=1e-15)


def test_merge_fast_fused_cat_dirnorm_matches_two_pass():
    """Fused cat+dirnorm ≡ dir_norm each part then ``_merge_fast_cat_matrix``."""
    rng = np.random.default_rng(7)
    a = [[rng.random((4, 5)) + 0.1 for _ in range(3)] for _ in range(2)]
    assert _is_merge_fast_combined(a)
    fused = _merge_fast_cat_matrix_dirnorm(a)
    parts_norm = [[spm_dir_norm(x) for x in group] for group in a]
    two_pass = _merge_fast_cat_matrix(parts_norm)
    np.testing.assert_allclose(fused, two_pass, rtol=0.0, atol=1e-15)


def test_spm_information_distance_optim_c_sparse_status_oracle(dem_eng):
    dem_eng.eval(
        "a_spm_information_distance = {[2 1; 1 3], [1 2; 4 1]};"
        "[~,C_spm_information_distance] = "
        "spm_information_distance(a_spm_information_distance);",
        nargout=0,
    )
    _, c_python = spm_information_distance_optim(_case_a())
    assert sparse.issparse(c_python) == bool(
        dem_eng.eval("issparse(C_spm_information_distance)")
    )
