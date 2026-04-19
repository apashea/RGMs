import matlab
import numpy as np
from scipy import sparse

from misc.depr.spm_vec import spm_vec
from tests.helpers.compare import assert_matlab_match


def test_spm_vec_doc_example_cell_oracle(eng):
    eng.eval("v_doc = spm_vec({eye(2), 3});", nargout=0)
    v_matlab = eng.eval("v_doc")
    X_python = [np.eye(2), 3.0]
    v_python = spm_vec(X_python)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_varargin_merge_oracle(eng):
    eng.eval("v_m = spm_vec(eye(2), 3);", nargout=0)
    v_matlab = eng.eval("v_m")
    v_python = spm_vec(np.eye(2), 3.0)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_matrix_column_major_oracle(eng):
    X = np.array([[1.0, 3.0], [2.0, 4.0]])
    X_matlab = matlab.double(X.tolist())

    v_matlab = eng.spm_vec(X_matlab)
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_raw_1d_row_oracle(eng):
    X = np.array([1.0, 2.0, 3.0])

    v_matlab = eng.eval("spm_vec([1 2 3])")
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_logical_oracle(eng):
    X = np.array([[True, False], [False, True]])
    X_matlab = matlab.logical(X.tolist())

    v_matlab = eng.spm_vec(X_matlab)
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_sparse_oracle(eng):
    eng.eval(
        "Xs = sparse([1 0; 0 2]); v_s = full(spm_vec(Xs));",
        nargout=0,
    )
    v_matlab = eng.eval("v_s")
    X_python = sparse.csr_matrix([[1.0, 0.0], [0.0, 2.0]])
    v_python = spm_vec(X_python)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_empty_numeric_oracle(eng):
    X = np.zeros((0, 3))
    X_matlab = matlab.double(X.tolist())

    v_matlab = eng.spm_vec(X_matlab)
    v_python = spm_vec(X)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_single_struct_oracle(eng):
    eng.eval(
        "S_one = struct('a', 1, 'b', [1 2]); v_st = spm_vec(S_one);",
        nargout=0,
    )
    v_matlab = eng.eval("v_st")
    S_python = {"a": 1.0, "b": np.array([[1.0, 2.0]])}
    v_python = spm_vec(S_python)

    assert_matlab_match(v_matlab, v_python)


def test_spm_vec_struct_array_oracle(eng):
    eng.eval(
        "S_arr(1).a = 1; S_arr(2).a = 2; v_sa = spm_vec(S_arr);",
        nargout=0,
    )
    v_matlab = eng.eval("v_sa")
    S_python = [{"a": 1.0}, {"a": 2.0}]
    v_python = spm_vec(S_python)

    assert_matlab_match(v_matlab, v_python)
