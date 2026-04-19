import matlab
import numpy as np

from misc.depr.spm_dir_norm import spm_dir_norm
from tests.helpers.compare import assert_matlab_match


def test_spm_dir_norm_matrix_oracle(eng):
    A = np.array([[1.0, 0.0, 3.0], [1.0, 0.0, 3.0], [2.0, 0.0, 4.0]])
    A_matlab = matlab.double(A.tolist())

    Y_matlab = eng.spm_dir_norm(A_matlab)
    Y_python = spm_dir_norm(A)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dir_norm_raw_1d_is_row_oracle(eng):
    A = np.array([1.0, 2.0, 3.0])

    Y_matlab = eng.eval("spm_dir_norm([1 2 3])")
    Y_python = spm_dir_norm(A)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dir_norm_column_vector_oracle(eng):
    A = np.array([[1.0], [2.0], [3.0]])
    A_matlab = matlab.double(A.tolist())

    Y_matlab = eng.spm_dir_norm(A_matlab)
    Y_python = spm_dir_norm(A)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dir_norm_cell_oracle(eng):
    eng.eval(
        "A_dn = {[1 2; 3 4], [0 0; 1 1]};",
        nargout=0,
    )
    A_python = [
        np.array([[1.0, 2.0], [3.0, 4.0]]),
        np.array([[0.0, 0.0], [1.0, 1.0]]),
    ]

    Y_matlab = eng.eval("spm_dir_norm(A_dn)")
    Y_python = spm_dir_norm(A_python)

    assert len(Y_python) == len(Y_matlab)
    for y_m, y_p in zip(Y_matlab, Y_python):
        assert_matlab_match(y_m, y_p)


def test_spm_dir_norm_cell_skips_function_handle_oracle(eng):
    eng.eval(
        "fh = @(x) x; "
        "A_dn2 = {fh, [1 2; 3 4]};",
        nargout=0,
    )
    A_python = [lambda x: x, np.array([[1.0, 2.0], [3.0, 4.0]])]

    Y_matlab = eng.eval("spm_dir_norm(A_dn2)")
    Y_python = spm_dir_norm(A_python)

    assert callable(Y_python[0])
    assert_matlab_match(Y_matlab[1], Y_python[1])
