import matlab
import numpy as np
from scipy import sparse

from python_src.spm_dot import spm_dot
from tests.helpers.compare import assert_matlab_match


def test_spm_dot_scalar_oracle(eng):
    X = np.array([[1.0, -2.0], [3.5, 4.0]])
    x = -2.0
    X_matlab = matlab.double(X.tolist())

    Y_matlab = eng.spm_dot(X_matlab, x)
    Y_python = spm_dot(X, x)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_vector_matching_second_dimension_oracle(eng):
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    x = np.array([0.5, -1.0, 2.0])

    eng.eval("X_spm_dot = sparse([1 2 3; 4 5 6]);", nargout=0)
    eng.eval("x_spm_dot = [0.5; -1; 2];", nargout=0)
    Y_matlab_sparse = eng.eval("issparse(spm_dot(X_spm_dot, x_spm_dot))")
    Y_matlab = eng.eval("spm_dot(X_spm_dot, x_spm_dot)")
    Y_python = spm_dot(sparse.csr_matrix(X), x)

    assert not bool(Y_matlab_sparse)
    assert not sparse.issparse(Y_python)
    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_cell_trailing_dimensions_oracle(eng):
    X = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")
    x = [
        np.array([1.0, -1.0, 0.5]),
        np.array([2.0, 0.0, -1.0, 1.0]),
    ]

    eng.eval("X_spm_dot = reshape(1:24, [2 3 4]);", nargout=0)
    eng.eval("x_spm_dot = {[1; -1; 0.5], [2; 0; -1; 1]};", nargout=0)
    Y_matlab = eng.eval("spm_dot(X_spm_dot, x_spm_dot)")
    Y_python = spm_dot(X, x)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_cell_omit_dimension_oracle(eng):
    X = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")
    x = [
        np.array([1.0, -1.0, 0.5]),
        np.array([2.0, 0.0, -1.0, 1.0]),
    ]

    eng.eval("X_spm_dot = reshape(1:24, [2 3 4]);", nargout=0)
    eng.eval("x_spm_dot = {[1; -1; 0.5], [2; 0; -1; 1]};", nargout=0)
    Y_matlab = eng.eval("spm_dot(X_spm_dot, x_spm_dot, 2)")
    Y_python = spm_dot(X, x, 2)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_cell_scalar_oracle(eng):
    X = np.array([[1.0, -2.0], [3.5, 4.0]])
    x = [np.array([[2.0]])]
    X_matlab = matlab.double(X.tolist())

    Y_matlab = eng.eval("spm_dot([1 -2; 3.5 4], {2})")
    Y_python = spm_dot(X, x)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_vector_matching_first_dimension_oracle(eng):
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    x = np.array([10.0, 20.0])
    X_matlab = matlab.double(X.tolist())

    Y_matlab = eng.eval("spm_dot([1 2 3; 4 5 6], [10; 20])")
    Y_python = spm_dot(X, x)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_cell_omit_first_dimension_oracle(eng):
    X = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")
    x = [
        np.array([1.0, -1.0, 0.5]),
        np.array([2.0, 0.0, -1.0, 1.0]),
    ]

    eng.eval("X_spm_dot = reshape(1:24, [2 3 4]);", nargout=0)
    eng.eval("x_spm_dot = {[1; -1; 0.5], [2; 0; -1; 1]};", nargout=0)
    Y_matlab = eng.eval("spm_dot(X_spm_dot, x_spm_dot, 1)")
    Y_python = spm_dot(X, x, 1)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_cell_omit_multiple_dimensions_oracle(eng):
    X = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")
    x = [
        np.array([1.0, -1.0]),
        np.array([0.5, -1.0, 2.0]),
        np.array([2.0, 0.0, -1.0, 1.0]),
    ]

    eng.eval("X_spm_dot = reshape(1:24, [2 3 4]);", nargout=0)
    eng.eval(
        "x_spm_dot = {[1; -1], [0.5; -1; 2], [2; 0; -1; 1]};",
        nargout=0,
    )
    Y_matlab = eng.eval("spm_dot(X_spm_dot, x_spm_dot, [1 3])")
    Y_python = spm_dot(X, x, [1, 3])

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_dot_raw_1d_X_is_row_oracle(eng):
    X = np.array([1.0, 2.0, 3.0])
    x = np.array([0.5, -1.0, 2.0])

    Y_matlab = eng.eval("spm_dot([1 2 3], [0.5 -1 2])")
    Y_python = spm_dot(X, x)

    assert_matlab_match(Y_matlab, Y_python)
