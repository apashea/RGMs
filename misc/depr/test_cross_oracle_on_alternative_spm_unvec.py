"""Oracle scenarios from tests/oracle/test_spm_unvec.py run against misc.depr.spm_unvec (+ misc.depr.spm_vec)."""

import numpy as np

from misc.depr.spm_unvec import spm_unvec
from tests.helpers.compare import assert_matlab_match


def test_spm_unvec_column_vector_oracle(eng):
    v = np.arange(1.0, 4.0).reshape((-1, 1))

    X_matlab = eng.eval("spm_unvec((1:3)', zeros(3,1))")
    X_python = spm_unvec(v, np.zeros((3, 1)))

    assert_matlab_match(X_matlab, X_python)


def test_spm_unvec_matrix_fortran_order_oracle(eng):
    v = np.arange(1.0, 7.0).reshape((-1, 1))

    X_matlab = eng.eval("spm_unvec((1:6)', zeros(2,3))")
    X_python = spm_unvec(v, np.zeros((2, 3)))

    assert_matlab_match(X_matlab, X_python)


def test_spm_unvec_cell_struct_template_oracle(eng):
    eng.eval(
        "Y_spm_unvec = spm_unvec((1:9)', "
        "{zeros(2,2), struct('a',zeros(2,1),'b',zeros(1,3))});",
        nargout=0,
    )
    template = [
        np.zeros((2, 2)),
        {"a": np.zeros((2, 1)), "b": np.zeros((1, 3))},
    ]

    Y_python = spm_unvec(np.arange(1.0, 10.0).reshape((-1, 1)), template)

    assert_matlab_match(eng.eval("Y_spm_unvec{1}"), Y_python[0])
    assert_matlab_match(eng.eval("Y_spm_unvec{2}.a"), Y_python[1]["a"])
    assert_matlab_match(eng.eval("Y_spm_unvec{2}.b"), Y_python[1]["b"])


def test_spm_unvec_cell_matrix_column_major_oracle(eng):
    eng.eval(
        "Y_spm_unvec = spm_unvec((1:6)', "
        "{zeros(1,1), zeros(1,2); zeros(2,1), zeros(1,1)});",
        nargout=0,
    )
    template = [
        [np.zeros((1, 1)), np.zeros((1, 2))],
        [np.zeros((2, 1)), np.zeros((1, 1))],
    ]

    Y_python = spm_unvec(np.arange(1.0, 7.0).reshape((-1, 1)), template)

    _assert_cell_item_match(eng, "Y_spm_unvec{1,1}", Y_python[0][0])
    _assert_cell_item_match(eng, "Y_spm_unvec{2,1}", Y_python[1][0])
    _assert_cell_item_match(eng, "Y_spm_unvec{1,2}", Y_python[0][1])
    _assert_cell_item_match(eng, "Y_spm_unvec{2,2}", Y_python[1][1])


def _assert_cell_item_match(eng, matlab_expr, python_item):
    matlab_size = tuple(np.asarray(eng.eval(f"size({matlab_expr})"), dtype=int).ravel())
    assert np.asarray(python_item).shape == matlab_size
    if matlab_size == (1, 1):
        python_item = np.asarray(python_item).reshape(-1, order="F")[0]
    assert_matlab_match(eng.eval(matlab_expr), python_item)
