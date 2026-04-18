import matlab
import numpy as np

from python_src.spm_softmax import spm_softmax
from tests.helpers.compare import assert_matlab_match


def test_spm_softmax_matrix_oracle(eng):
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    x_matlab = matlab.double(x.tolist())

    y_matlab = eng.spm_softmax(x_matlab)
    y_python = spm_softmax(x)

    assert_matlab_match(y_matlab, y_python)


def test_spm_softmax_k_oracle(eng):
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    k = 0.5
    x_matlab = matlab.double(x.tolist())

    y_matlab = eng.spm_softmax(x_matlab, k)
    y_python = spm_softmax(x, k)

    assert_matlab_match(y_matlab, y_python)


def test_spm_softmax_row_oracle(eng):
    x = np.array([[1.0, 2.0, 3.0]])
    x_matlab = matlab.double(x.tolist())

    y_matlab = eng.spm_softmax(x_matlab)
    y_python = spm_softmax(x)

    assert_matlab_match(y_matlab, y_python)


def test_spm_softmax_scalar_oracle(eng):
    x = 5.0

    y_matlab = eng.spm_softmax(x)
    y_python = spm_softmax(x)

    assert_matlab_match(y_matlab, y_python)


def test_spm_softmax_raw_1d_is_row_oracle(eng):
    x = np.array([1.0, 2.0, 3.0])

    y_matlab = eng.eval("spm_softmax([1 2 3])")
    y_python = spm_softmax(x)

    assert_matlab_match(y_matlab, y_python)


def test_spm_softmax_column_oracle(eng):
    x = np.array([[1.0], [2.0], [3.0]])
    x_matlab = matlab.double(x.tolist())

    y_matlab = eng.spm_softmax(x_matlab)
    y_python = spm_softmax(x)

    assert_matlab_match(y_matlab, y_python)


def test_spm_softmax_negative_large_oracle(eng):
    x = np.array([[-1000.0], [-999.0], [-998.0]])
    x_matlab = matlab.double(x.tolist())

    y_matlab = eng.spm_softmax(x_matlab)
    y_python = spm_softmax(x)

    assert_matlab_match(y_matlab, y_python)
