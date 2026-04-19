"""Oracle scenarios from tests/oracle/test_spm_dir_norm.py run against misc.depr.spm_dir_norm."""

import matlab
import numpy as np

from misc.depr.spm_dir_norm import spm_dir_norm
from tests.helpers.compare import assert_matlab_match


def test_spm_dir_norm_zero_column_oracle(eng):
    A = np.array([[1.0, 0.0, 2.0], [3.0, 0.0, 2.0]])
    A_matlab = matlab.double(A.tolist())

    A_matlab_norm = eng.spm_dir_norm(A_matlab)
    A_python_norm = spm_dir_norm(A)

    assert_matlab_match(A_matlab_norm, A_python_norm)


def test_spm_dir_norm_tensor_oracle(eng):
    eng.eval(
        "A_spm_dir_norm = reshape(1:12,[2 3 2]);"
        "A_spm_dir_norm(:,2,1) = 0;"
        "Y_spm_dir_norm = spm_dir_norm(A_spm_dir_norm);",
        nargout=0,
    )
    A = np.arange(1.0, 13.0).reshape((2, 3, 2), order="F")
    A[:, 1, 0] = 0

    A_matlab_norm = eng.eval("Y_spm_dir_norm")
    A_python_norm = spm_dir_norm(A)

    assert_matlab_match(A_matlab_norm, A_python_norm)


def test_spm_dir_norm_cell_oracle(eng):
    eng.eval(
        "Y_spm_dir_norm = spm_dir_norm({[1 0; 3 0], [2; 2]});",
        nargout=0,
    )
    A = [
        np.array([[1.0, 0.0], [3.0, 0.0]]),
        np.array([[2.0], [2.0]]),
    ]

    A_python_norm = spm_dir_norm(A)

    assert_matlab_match(eng.eval("Y_spm_dir_norm{1}"), A_python_norm[0])
    assert_matlab_match(eng.eval("Y_spm_dir_norm{2}"), A_python_norm[1])
