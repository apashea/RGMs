import matlab
import numpy as np

from python_src.spm_log import spm_log
from tests.helpers.compare import assert_matlab_match


def test_spm_log_numeric_oracle(eng):
    A = np.array([[0.5, 0.0], [1.0, 1e-20]])
    A_matlab = matlab.double(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_logical_oracle(eng):
    A = np.array([[True, False], [False, True]])
    A_matlab = matlab.logical(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_scalar_oracle(eng):
    A = 0.5

    A_matlab = eng.spm_log(A)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_all_zeros_oracle(eng):
    A = np.zeros((2, 3))
    A_matlab = matlab.double(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_column_oracle(eng):
    A = np.array([[0.5], [1.0], [2.0]])
    A_matlab = matlab.double(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_raw_1d_is_row_oracle(eng):
    A = np.array([0.5, 1.0, 2.0])

    A_matlab = eng.eval("spm_log([0.5 1 2])")
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)
