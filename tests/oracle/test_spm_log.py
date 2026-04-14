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
