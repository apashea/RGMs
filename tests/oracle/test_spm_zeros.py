import matlab
import numpy as np

from python_src.spm_zeros import spm_zeros
from tests.helpers.compare import assert_matlab_match


def test_spm_zeros_numeric_row_oracle(eng):
    X = np.array([[1.0, -2.0, 3.0]])
    X_matlab = matlab.double(X.tolist())

    Y_matlab = eng.spm_zeros(X_matlab)
    Y_python = spm_zeros(X)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_zeros_cell_oracle(eng):
    eng.eval("X_spm_zeros = {[1 -2 3], [4; 5]};", nargout=0)
    X_python = [
        np.array([[1.0, -2.0, 3.0]]),
        np.array([[4.0], [5.0]]),
    ]

    eng.eval("Y_spm_zeros = spm_zeros(X_spm_zeros);", nargout=0)
    Y_matlab = eng.eval("Y_spm_zeros")
    Y_python = spm_zeros(X_python)

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_zeros_struct_oracle(eng):
    eng.eval(
        "X_spm_zeros = struct('a', [1 -2 3], 'b', [4; 5]);",
        nargout=0,
    )
    X_python = {
        "a": np.array([[1.0, -2.0, 3.0]]),
        "b": np.array([[4.0], [5.0]]),
    }

    eng.eval("Y_spm_zeros = spm_zeros(X_spm_zeros);", nargout=0)
    Y_python = spm_zeros(X_python)

    assert set(Y_python) == {"a", "b"}
    assert_matlab_match(eng.eval("Y_spm_zeros.a"), Y_python["a"])
    assert_matlab_match(eng.eval("Y_spm_zeros.b"), Y_python["b"])
