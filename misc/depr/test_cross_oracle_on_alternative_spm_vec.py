"""Oracle scenarios from tests/oracle/test_spm_vec.py run against misc.depr.spm_vec."""

import numpy as np

from misc.depr.spm_vec import spm_vec
from tests.helpers.compare import assert_matlab_match


def test_spm_vec_matrix_fortran_order_oracle(eng):
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

    v_matlab = eng.eval("spm_vec([1 2 3; 4 5 6])")
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_varargin_oracle(eng):
    v_matlab = eng.eval("spm_vec([1 2],[3;4])")
    v_python = spm_vec(
        np.array([[1.0, 2.0]]),
        np.array([[3.0], [4.0]]),
    )

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_cell_struct_array_oracle(eng):
    eng.eval(
        "X_spm_vec = {eye(2), "
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

    v_matlab = eng.eval("spm_vec(X_spm_vec)")
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_cell_matrix_column_major_oracle(eng):
    eng.eval(
        "X_spm_vec = {[1 2], 3; [4;5], [6 7]};",
        nargout=0,
    )
    X = [
        [np.array([[1.0, 2.0]]), 3.0],
        [np.array([[4.0], [5.0]]), np.array([[6.0, 7.0]])],
    ]

    v_matlab = eng.eval("spm_vec(X_spm_vec)")
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)
