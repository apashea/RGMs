import numpy as np
from scipy import sparse


def spm_length(X):
    # vectorise numerical arrays
    if _isnumeric(X):
        n = _numel(X)

    # vectorise logical arrays
    elif _islogical(X):
        n = _numel(X)

    # vectorise structure into cell arrays
    elif _isstruct(X):
        n = 0
        f = _fieldnames(X)
        for i in range(len(f)):
            for item in _struct_items(X):
                n = n + spm_length(_getfield(item, f[i]))

    # vectorise cells into numerical arrays
    elif _iscell(X):
        n = 0
        for item in _cell_items(X):
            n = n + spm_length(item)

    else:
        n = 0

    return n


def _isnumeric(X):
    if sparse.issparse(X):
        return True
    if isinstance(X, (str, bytes, dict)):
        return False
    if isinstance(X, (list, tuple)):
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
    if sparse.issparse(X):
        return False
    if isinstance(X, np.ndarray):
        return X.dtype == object
    if isinstance(X, (list, tuple)):
        return not _isstruct(X)
    return False


def _numel(X):
    if sparse.issparse(X):
        return int(np.prod(X.shape))
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


def _getfield(X, field):
    if isinstance(X, dict):
        return X[field]
    return getattr(X, field)


def _cell_items(X):
    if isinstance(X, np.ndarray):
        return list(X.ravel(order="F"))
    return list(X)
