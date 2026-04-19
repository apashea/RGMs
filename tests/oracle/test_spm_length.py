import matlab
import numpy as np

from python_src.spm_length import spm_length
from tests.helpers.compare import assert_matlab_match


def test_spm_length_numeric_matrix_oracle(eng):
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    X_matlab = matlab.double(X.tolist())

    n_matlab = eng.spm_length(X_matlab)
    n_python = spm_length(X)

    assert_matlab_match(n_matlab, n_python)


def test_spm_length_logical_matrix_oracle(eng):
    n_matlab = eng.eval("spm_length(logical([1 0; 0 1]))")
    n_python = spm_length(np.array([[True, False], [False, True]]))

    assert_matlab_match(n_matlab, n_python)


def test_spm_length_cell_struct_array_oracle(eng):
    eng.eval(
        "X_spm_length = {eye(2), "
        "struct('a',{[1;2],3},'b',{logical([1 0]),[4 5 6]})};",
        nargout=0,
    )
    X = [
        np.eye(2),
        [
            {"a": np.array([[1.0], [2.0]]), "b": np.array([[True, False]])},
            {"a": 3.0, "b": np.array([[4.0, 5.0, 6.0]])},
        ],
    ]

    n_matlab = eng.eval("spm_length(X_spm_length)")
    n_python = spm_length(X)

    assert_matlab_match(n_matlab, n_python)
