from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.spm_sum import spm_sum
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def spm_sum_eng(eng, tmp_path):
    _write_spm_check_version_stub(tmp_path)
    eng.addpath(str(tmp_path), "-begin", nargout=0)
    eng.clear("spm_sum", nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(tmp_path), nargout=0)
        eng.clear("spm_sum", nargout=0)


def test_spm_sum_matrix_default_oracle(spm_sum_eng):
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    X_matlab = matlab.double(X.tolist())

    S_matlab = spm_sum_eng.spm_sum(X_matlab)
    S_python = spm_sum(X)

    assert_matlab_match(S_matlab, S_python)


def test_spm_sum_explicit_dimension_oracle(spm_sum_eng):
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    X_matlab = matlab.double(X.tolist())

    S_matlab = spm_sum_eng.spm_sum(X_matlab, 2.0)
    S_python = spm_sum(X, 2)

    assert_matlab_match(S_matlab, S_python)


def test_spm_sum_vecdim_tensor_oracle(spm_sum_eng):
    X = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")

    spm_sum_eng.eval("X_spm_sum = reshape(1:24, [2 3 4]);", nargout=0)
    S_matlab = spm_sum_eng.eval("spm_sum(X_spm_sum, [1 3])")
    S_python = spm_sum(X, np.array([[1, 3]]))

    assert_matlab_match(S_matlab, S_python)


def test_spm_sum_scalar_oracle(spm_sum_eng):
    X = 5.0

    S_matlab = spm_sum_eng.spm_sum(X)
    S_python = spm_sum(X)

    assert_matlab_match(S_matlab, S_python)


def test_spm_sum_row_oracle(spm_sum_eng):
    X = np.array([[1.0, 2.0, 3.0]])
    X_matlab = matlab.double(X.tolist())

    S_matlab = spm_sum_eng.spm_sum(X_matlab)
    S_python = spm_sum(X)

    assert_matlab_match(S_matlab, S_python)


def test_spm_sum_column_oracle(spm_sum_eng):
    X = np.array([[1.0], [2.0], [3.0]])
    X_matlab = matlab.double(X.tolist())

    S_matlab = spm_sum_eng.spm_sum(X_matlab)
    S_python = spm_sum(X)

    assert_matlab_match(S_matlab, S_python)


def test_spm_sum_raw_1d_is_row_oracle(spm_sum_eng):
    X = np.array([1.0, 2.0, 3.0])

    S_matlab = spm_sum_eng.eval("spm_sum([1 2 3])")
    S_python = spm_sum(X)

    assert_matlab_match(S_matlab, S_python)


def _write_spm_check_version_stub(tmp_path):
    stub = Path(tmp_path) / "spm_check_version.m"
    stub.write_text(
        "function v = spm_check_version(varargin)\n"
        "if nargin == 0\n"
        "    v = 'matlab';\n"
        "else\n"
        "    v = 1;\n"
        "end\n",
        encoding="utf-8",
    )
