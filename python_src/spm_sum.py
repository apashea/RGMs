import numpy as np

from matlab_compat import as_matlab_array, matlab_scalar, trim_trailing_singletons


def spm_sum(*varargin):
    # Compatibility layer for SUM for MATLAB < R2018b
    X = as_matlab_array(varargin[0])

    if len(varargin) == 1:
        dim = _first_non_singleton_dim(X)
        S = _sum_dim(X, dim)
    else:
        vecdim = varargin[1]
        if isinstance(vecdim, str) and vecdim.lower() == "all":
            S = np.sum(X)
        elif _is_numeric_vecdim(vecdim):
            S = X
            for dim in np.asarray(vecdim, dtype=int).ravel(order="F"):
                S = _sum_dim(S, int(dim))
        else:
            S = _sum_dim(X, int(vecdim))

    return _matlab_scalar(S)


def _first_non_singleton_dim(X):
    if X.ndim == 0:
        return None
    for dim, size in enumerate(X.shape, start=1):
        if size != 1:
            return dim
    return 1


def _sum_dim(X, dim):
    if dim is None:
        return np.sum(X)
    axis = int(dim) - 1
    if axis >= np.ndim(X):
        return X
    return np.sum(X, axis=axis, keepdims=True)


def _is_numeric_vecdim(x):
    if isinstance(x, str):
        return False
    x = np.asarray(x)
    return x.size > 1 and np.issubdtype(x.dtype, np.number)


def _matlab_scalar(S):
    return matlab_scalar(trim_trailing_singletons(S))
