import numpy as np
from scipy import sparse


def spm_vec(X, *varargin):
    # initialise X and vX
    if len(varargin) > 0:
        X = [X] + list(varargin)

    # vectorise numerical arrays
    if _isnumeric(X):
        vX = _column(X)

    # vectorise logical arrays
    elif _islogical(X):
        vX = _column(X)

    # vectorise structure into cell arrays
    elif _isstruct(X):
        vX = np.zeros((0, 1))
        f = _fieldnames(X)
        X = _struct_items(X)
        for i in range(len(f)):
            vX = np.concatenate(
                (vX, spm_vec([_getfield(item, f[i]) for item in X])),
                axis=0,
            )

    # vectorise cells into numerical arrays
    elif _iscell(X):
        vX = np.zeros((0, 1))
        for item in _cell_items(X):
            vX = np.concatenate((vX, spm_vec(item)), axis=0)

    else:
        vX = np.zeros((0, 1))

    return vX


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


def _column(X):
    if sparse.issparse(X):
        X = X.toarray()
    return np.asarray(X).ravel(order="F").reshape((-1, 1))


def _fieldnames(X):
    item = _struct_items(X)[0]
    if isinstance(item, dict):
        return list(item.keys())
    return list(vars(item).keys())


def _struct_items(X):
    if isinstance(X, (list, tuple)):
        return list(X)
    return [X]


def _getfield(X, field):
    if isinstance(X, dict):
        return X[field]
    return getattr(X, field)


def _cell_items(X):
    if isinstance(X, np.ndarray):
        return list(X.ravel(order="F"))
    if len(X) > 0 and all(isinstance(row, (list, tuple)) for row in X):
        return [X[i][j] for j in range(len(X[0])) for i in range(len(X))]
    return list(X)
