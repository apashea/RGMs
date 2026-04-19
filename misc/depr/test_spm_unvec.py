import copy

import numpy as np
from scipy import sparse

from misc.depr.spm_unvec import spm_unvec
from misc.depr.spm_vec import spm_vec
from tests.helpers.compare import assert_matlab_match


def _assert_nested_match(matlab_result, python_result):
    if isinstance(matlab_result, (list, tuple)) and isinstance(
        python_result, (list, tuple)
    ):
        assert len(matlab_result) == len(python_result)
        for a, b in zip(matlab_result, python_result):
            _assert_nested_match(a, b)
        return
    if isinstance(matlab_result, dict) and isinstance(python_result, dict):
        assert set(matlab_result) == set(python_result)
        for key in matlab_result:
            _assert_nested_match(matlab_result[key], python_result[key])
        return
    assert_matlab_match(matlab_result, python_result)


def test_spm_unvec_matrix_standalone_oracle(eng):
    X = np.array([[1.0, 3.0], [2.0, 4.0]])
    eng.eval("X_u = [1 3; 2 4]; v_u = spm_vec(X_u);", nargout=0)
    v_matlab = eng.eval("v_u")
    v_python = spm_vec(X)

    Y_matlab = eng.eval("spm_unvec(v_u, X_u)")
    Y_python = spm_unvec(v_python, copy.deepcopy(X))

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_unvec_raw_row_template_standalone_oracle(eng):
    X = np.array([1.0, 2.0, 3.0])
    eng.eval("X_u = [1 2 3]; v_u = spm_vec(X_u);", nargout=0)
    v_matlab = eng.eval("v_u")
    v_python = spm_vec(X)

    Y_matlab = eng.eval("spm_unvec(v_u, X_u)")
    Y_python = spm_unvec(v_python, copy.deepcopy(X))

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_unvec_logical_standalone_oracle(eng):
    X = np.array([[True, False], [False, True]])
    eng.eval("X_u = logical([1 0; 0 1]); v_u = spm_vec(X_u);", nargout=0)
    v_matlab = eng.eval("v_u")
    v_python = spm_vec(X)

    Y_matlab = eng.eval("spm_unvec(v_u, X_u)")
    Y_python = spm_unvec(v_python, copy.deepcopy(X))

    assert_matlab_match(Y_matlab, Y_python)


def test_spm_unvec_sparse_template_standalone_oracle(eng):
    eng.eval(
        "X_u = sparse([1 0; 0 2]); v_u = spm_vec(X_u); Y_u = spm_unvec(v_u, X_u);",
        nargout=0,
    )
    Y_matlab = eng.eval("full(Y_u)")
    X_python = sparse.csr_matrix([[1.0, 0.0], [0.0, 2.0]])
    v_python = spm_vec(X_python)
    Y_python = spm_unvec(v_python, copy.deepcopy(X_python))

    assert_matlab_match(Y_matlab, Y_python.toarray())


def test_spm_unvec_roundtrip_matrix_oracle(eng):
    eng.eval("X_rt = [1 3; 2 4];", nargout=0)
    Y_matlab = eng.eval("spm_unvec(spm_vec(X_rt), X_rt)")
    X = np.array([[1.0, 3.0], [2.0, 4.0]])
    Y_python = spm_unvec(spm_vec(X), copy.deepcopy(X))
    assert_matlab_match(Y_matlab, Y_python)


def test_spm_unvec_roundtrip_row_oracle(eng):
    X = np.array([1.0, 2.0, 3.0])
    eng.eval("X_rt = [1 2 3];", nargout=0)
    Y_matlab = eng.eval("spm_unvec(spm_vec(X_rt), X_rt)")
    Y_python = spm_unvec(spm_vec(X), copy.deepcopy(X))
    assert_matlab_match(Y_matlab, Y_python)


def test_spm_unvec_roundtrip_cell_doc_oracle(eng):
    eng.eval("X_rt = {eye(2), 3};", nargout=0)
    Y_matlab = eng.eval("spm_unvec(spm_vec(X_rt), X_rt)")
    X_python = [np.eye(2), 3.0]
    Y_python = spm_unvec(spm_vec(X_python), copy.deepcopy(X_python))
    _assert_nested_match(Y_matlab, Y_python)


def test_spm_unvec_roundtrip_single_struct_oracle(eng):
    eng.eval(
        "X_rt = struct('a', 1, 'b', [1 2]);",
        nargout=0,
    )
    Y_matlab = eng.eval("spm_unvec(spm_vec(X_rt), X_rt)")
    X_python = {"a": 1.0, "b": np.array([[1.0, 2.0]])}
    Y_python = spm_unvec(spm_vec(X_python), copy.deepcopy(X_python))
    _assert_nested_match(Y_matlab, Y_python)


def test_spm_unvec_roundtrip_struct_array_oracle(eng):
    eng.eval(
        "clear X_rt; X_rt(1).a = 1; X_rt(2).a = 2; "
        "Y_rt = spm_unvec(spm_vec(X_rt), X_rt);",
        nargout=0,
    )
    y1_matlab = eng.eval("Y_rt(1).a")
    y2_matlab = eng.eval("Y_rt(2).a")
    X_python = [{"a": 1.0}, {"a": 2.0}]
    Y_python = spm_unvec(spm_vec(X_python), copy.deepcopy(X_python))
    assert_matlab_match(y1_matlab, Y_python[0]["a"])
    assert_matlab_match(y2_matlab, Y_python[1]["a"])


def test_spm_unvec_roundtrip_sparse_oracle(eng):
    eng.eval("X_rt = sparse([1 0; 0 2]);", nargout=0)
    Y_matlab = eng.eval("full(spm_unvec(spm_vec(X_rt), X_rt))")
    X_python = sparse.csr_matrix([[1.0, 0.0], [0.0, 2.0]])
    Y_python = spm_unvec(spm_vec(X_python), copy.deepcopy(X_python))
    assert_matlab_match(Y_matlab, Y_python.toarray())
