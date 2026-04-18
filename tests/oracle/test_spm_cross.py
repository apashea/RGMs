import matlab
import numpy as np
from scipy import sparse

from python_src.spm_cross import spm_cross
from tests.helpers.compare import assert_matlab_match


def test_spm_cross_numeric_outer_product_oracle(eng):
    X = np.array([[1.0, 2.0], [3.0, 4.0]])
    x = np.array([[5.0, 6.0, 7.0]])
    X_matlab = matlab.double(X.tolist())
    x_matlab = matlab.double(x.tolist())

    Y_matlab = eng.spm_cross(X_matlab, x_matlab)
    Y_python = spm_cross(X, x)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_cross_cell_input_oracle(eng):
    X_python = [
        np.array([[1.0, 2.0]]),
        np.array([[3.0], [4.0]]),
        5.0,
    ]

    Y_matlab = eng.eval("spm_cross({[1 2], [3; 4], 5})")
    Y_python = spm_cross(X_python)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_cross_sparse_input_oracle(eng):
    X_python = sparse.csr_matrix([[1.0, 0.0], [0.0, 2.0]])
    x_python = np.array([[3.0], [4.0]])

    eng.eval("Y_spm_cross = spm_cross(sparse([1 0; 0 2]), [3; 4]);", nargout=0)
    Y_matlab_sparse = eng.eval("issparse(Y_spm_cross)")
    Y_matlab = eng.eval("full(Y_spm_cross)")
    Y_python = spm_cross(X_python, x_python)

    assert sparse.issparse(Y_python) == bool(Y_matlab_sparse)
    assert_matlab_match(Y_matlab, Y_python)


def test_spm_cross_single_numeric_oracle(eng):
    X = np.array([[1.0, 2.0], [3.0, 4.0]])
    X_matlab = matlab.double(X.tolist())

    Y_matlab = eng.spm_cross(X_matlab)
    Y_python = spm_cross(X)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_cross_raw_1d_is_row_oracle(eng):
    X = np.array([1.0, 2.0, 3.0])

    Y_matlab = eng.eval("spm_cross([1 2 3])")
    Y_python = spm_cross(X)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_cross_varargin_oracle(eng):
    X = np.array([[1.0], [2.0]])
    x = np.array([[3.0], [4.0]])
    z = np.array([[5.0], [6.0]])

    Y_matlab = eng.eval("spm_cross([1;2],[3;4],[5;6])")
    Y_python = spm_cross(X, x, z)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_cross_row_and_column_vectors_oracle(eng):
    X = np.array([[1.0, 2.0]])
    x = np.array([[3.0], [4.0]])
    X_matlab = matlab.double(X.tolist())
    x_matlab = matlab.double(x.tolist())

    Y_matlab = eng.spm_cross(X_matlab, x_matlab)
    Y_python = spm_cross(X, x)

    assert_matlab_match(Y_matlab, Y_python)
