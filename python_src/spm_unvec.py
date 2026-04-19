import numpy as np
from scipy import sparse

from matlab_compat import as_matlab_array, full
from python_src.spm_length import spm_length
from python_src.spm_vec import spm_vec


def spm_unvec(vX, *varargin):
    if len(varargin) == 1:
        X = varargin[0]
    else:
        X = list(varargin)

    # check vX is numeric
    if not (_isnumeric(vX) or _islogical(vX)):
        vX = spm_vec(vX)
    vX = _column(vX)

    X, _ = _unvec_one(vX, X)

    return X


def _unvec_one(vX, X):
    # reshape numerical arrays
    if _isnumeric(X) or _islogical(X):
        X = _template_array(X)
        n = X.size
        X = np.array(X, copy=True)
        X[...] = np.reshape(
            np.asarray(full(vX[:n])).ravel(order="F"),
            X.shape,
            order="F",
        )
        return X, vX[n:]

    # fill in structure arrays
    if _isstruct(X):
        X = _copy_struct(X)
        f = _fieldnames(X)
        for i in range(len(f)):
            c = [_getfield(item, f[i]) for item in _struct_items(X)]
            if _isnumeric(c):
                n = _numel(c)
            else:
                n = spm_length(c)
            c = spm_unvec(vX[:n], c)
            for item, value in zip(_struct_items(X), _cell_items(c)):
                _setfield(item, f[i], value)
            vX = vX[n:]
        return X, vX

    # fill in cell arrays
    if _iscell(X):
        X = _copy_cell(X)
        for i in range(_numel(X)):
            Xi = _cell_get(X, i)
            if _isnumeric(Xi):
                n = _numel(Xi)
            else:
                n = spm_length(Xi)
            Xi = spm_unvec(vX[:n], Xi)
            _cell_set(X, i, Xi)
            vX = vX[n:]
        return X, vX

    # else
    X = []
    return X, vX


def _isnumeric(X):
    if sparse.issparse(X):
        return True
    if isinstance(X, (str, bytes, dict, list, tuple)):
        return False
    X = np.asarray(X)
    return np.issubdtype(X.dtype, np.number) and not np.issubdtype(X.dtype, np.bool_)


def _islogical(X):
    if sparse.issparse(X):
        return np.issubdtype(X.dtype, np.bool_)
    if isinstance(X, (str, bytes, dict, list, tuple)):
        return False
    return np.issubdtype(np.asarray(X).dtype, np.bool_)


def _isstruct(X):
    if isinstance(X, dict):
        return True
    if isinstance(X, (list, tuple)) and len(X) > 0:
        return all(isinstance(x, dict) for x in X)
    return hasattr(X, "__dict__") and not isinstance(X, type)


def _iscell(X):
    if isinstance(X, np.ndarray):
        return X.dtype == object
    if isinstance(X, (list, tuple)):
        return not _isstruct(X)
    return False


def _template_array(X):
    X = as_matlab_array(full(X))
    if np.ndim(X) == 0:
        return np.reshape(X, (1, 1), order="F")
    return X


def _column(X):
    if sparse.issparse(X):
        X = X.toarray()
    return np.asarray(X).ravel(order="F").reshape((-1, 1))


def _numel(X):
    if sparse.issparse(X):
        return int(np.prod(X.shape))
    if _iscell(X):
        return len(_cell_items(X))
    return int(np.asarray(X).size)


def _fieldnames(X):
    item = _struct_items(X)[0]
    if isinstance(item, dict):
        return list(item.keys())
    return list(vars(item).keys())


def _struct_items(X):
    if isinstance(X, (list, tuple)):
        return list(X)
    return [X]


def _copy_struct(X):
    if isinstance(X, dict):
        return dict(X)
    if isinstance(X, list):
        return [dict(x) if isinstance(x, dict) else x for x in X]
    if isinstance(X, tuple):
        return [dict(x) if isinstance(x, dict) else x for x in X]
    return X


def _getfield(X, field):
    if isinstance(X, dict):
        return X[field]
    return getattr(X, field)


def _setfield(X, field, value):
    if isinstance(X, dict):
        X[field] = value
    else:
        setattr(X, field, value)


def _copy_cell(X):
    if isinstance(X, np.ndarray):
        return X.copy()
    if isinstance(X, tuple):
        return list(X)
    if len(X) > 0 and all(isinstance(row, list) for row in X):
        return [list(row) for row in X]
    return list(X)


def _cell_items(X):
    if isinstance(X, np.ndarray):
        return list(X.ravel(order="F"))
    if len(X) > 0 and all(isinstance(row, (list, tuple)) for row in X):
        return [X[i][j] for j in range(len(X[0])) for i in range(len(X))]
    return list(X)


def _cell_get(X, i):
    if isinstance(X, np.ndarray):
        return X.ravel(order="F")[i]
    if len(X) > 0 and all(isinstance(row, (list, tuple)) for row in X):
        n = len(X)
        row = i % n
        col = i // n
        return X[row][col]
    return X[i]


def _cell_set(X, i, value):
    if isinstance(X, np.ndarray):
        X.ravel(order="F")[i] = value
    elif len(X) > 0 and all(isinstance(row, list) for row in X):
        n = len(X)
        row = i % n
        col = i // n
        X[row][col] = value
    else:
        X[i] = value
