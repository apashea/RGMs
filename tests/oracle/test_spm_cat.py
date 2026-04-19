import matlab
import pytest
import numpy as np
from scipy import sparse

from python_src.spm_cat import spm_cat
from tests.helpers.compare import assert_matlab_match


_MATLAB_CELL = "{eye(2), []; [], [1 1; 1 1]}"


def test_spm_cat_matrix_passthrough_oracle(eng):
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    x_matlab = matlab.double(x.tolist())

    y_matlab = eng.spm_cat(x_matlab)
    y_python = spm_cat(x)

    assert not sparse.issparse(y_python)
    assert_matlab_match(y_matlab, y_python)


def test_spm_cat_cell_concatenation_oracle(eng):
    x_python = _python_cell()

    y_matlab_sparse = eng.eval(f"issparse(spm_cat({_MATLAB_CELL}))")
    y_matlab_full = eng.eval(f"full(spm_cat({_MATLAB_CELL}))")
    y_python = spm_cat(x_python)

    _assert_sparse_matrix_match(y_matlab_full, y_matlab_sparse, y_python)

    for d in (1, 2):
        eng.eval(f"y_spm_cat = spm_cat({_MATLAB_CELL}, {d});", nargout=0)
        y_matlab_size = _matlab_size(eng.eval("size(y_spm_cat)"))
        y_matlab_sparse = eng.eval("cellfun(@issparse, y_spm_cat)")
        y_matlab_full = eng.eval(
            "cellfun(@full, y_spm_cat, 'UniformOutput', false)"
        )
        y_python = spm_cat(_python_cell(), d)

        _assert_cell_match(y_matlab_size, y_matlab_sparse, y_matlab_full, y_python)


def test_spm_cat_nested_cell_oracle(eng):
    x_python = [
        [[np.eye(2)], np.empty((0, 0))],
        [np.empty((0, 0)), np.array([[1.0, 1.0], [1.0, 1.0]])],
    ]

    eng.eval("y_spm_cat = spm_cat({{eye(2)}, []; [], [1 1; 1 1]});", nargout=0)
    y_matlab_sparse = eng.eval("issparse(y_spm_cat)")
    y_matlab_full = eng.eval("full(y_spm_cat)")
    y_python = spm_cat(x_python)

    _assert_sparse_matrix_match(y_matlab_full, y_matlab_sparse, y_python)


def test_spm_cat_non_square_cell_oracle(eng):
    x_python = [[np.array([[1.0, 2.0]]), np.empty((0, 0)), np.array([[3.0, 4.0]])]]

    eng.eval("y_spm_cat = spm_cat({[1 2], [], [3 4]});", nargout=0)
    y_matlab_sparse = eng.eval("issparse(y_spm_cat)")
    y_matlab_full = eng.eval("full(y_spm_cat)")
    y_python = spm_cat(x_python)

    _assert_sparse_matrix_match(y_matlab_full, y_matlab_sparse, y_python)


def test_spm_cat_raw_1d_is_row_oracle(eng):
    x = np.array([1.0, 2.0, 3.0])

    y_matlab = eng.eval("spm_cat([1 2 3])")
    y_python = spm_cat(x)

    assert_matlab_match(y_matlab, y_python)


def test_spm_cat_scalar_zero_error_matches_matlab(eng):
    with pytest.raises(Exception):
        eng.eval("spm_cat({eye(2), []; 0, [1 1; 1 1]})")

    with pytest.raises(Exception):
        spm_cat([[np.eye(2), np.empty((0, 0))], [0.0, np.ones((2, 2))]])


def _python_cell():
    return [
        [np.eye(2), np.empty((0, 0))],
        [np.empty((0, 0)), np.array([[1.0, 1.0], [1.0, 1.0]])],
    ]


def _assert_sparse_matrix_match(y_matlab_full, y_matlab_sparse, y_python):
    assert sparse.issparse(y_python) == bool(y_matlab_sparse)
    if sparse.issparse(y_python):
        y_python = y_python.toarray()
    assert_matlab_match(y_matlab_full, y_python)


def _assert_cell_match(y_matlab_size, y_matlab_sparse, y_matlab_full, y_python):
    assert _python_cell_size(y_python) == y_matlab_size

    y_python_flat = _python_cell_flatten(y_python)
    y_python_sparse = np.array(
        [sparse.issparse(y) for y in y_python_flat], dtype=bool
    ).reshape(y_matlab_size)
    np.testing.assert_array_equal(
        np.asarray(y_matlab_sparse, dtype=bool),
        y_python_sparse,
    )

    for y_matlab, y_python_item in zip(y_matlab_full, y_python_flat):
        if sparse.issparse(y_python_item):
            y_python_item = y_python_item.toarray()
        assert_matlab_match(y_matlab, y_python_item)


def _matlab_size(x):
    return tuple(np.asarray(x, dtype=int).ravel())


def _python_cell_size(x):
    if len(x) > 0 and all(isinstance(row, list) for row in x):
        return len(x), len(x[0])
    return 1, len(x)


def _python_cell_flatten(x):
    if len(x) > 0 and all(isinstance(row, list) for row in x):
        return [item for row in x for item in row]
    return list(x)
