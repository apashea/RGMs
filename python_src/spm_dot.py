import numpy as np
from scipy import sparse

from matlab_compat import (
    as_matlab_array,
    full,
    matlab_ndims,
    matlab_scalar,
    matlab_size,
)


def spm_dot(X, x, i=None):
    # initialise dimensions
    if _iscell(x):
        x = _cell_list(x)

        # scalar product
        if len(x) == 1:
            if np.size(full(x[0])) == 1:
                X = as_matlab_array(X) * _scalar(x[0])
                return matlab_scalar(X)

        # omit leading dimensions
        DIM = np.arange(1, len(x) + 1) + max(matlab_ndims(X), len(x)) - len(x)

    else:

        # scalar product
        if np.size(x) == 1:
            X = as_matlab_array(X) * _scalar(x)
            return matlab_scalar(X)

        # find first matching dimension
        DIM = np.where(_size(X) == np.size(x))[0][0] + 1
        DIM = np.array([DIM])
        x = [x]

    # omit specified dimensions
    if i is not None:
        keep = np.ones(len(x), dtype=bool)
        keep[np.asarray(i, dtype=int).ravel(order="F") - 1] = False
        DIM = DIM[keep]
        x = [xd for j, xd in enumerate(x) if keep[j]]

    # inner product using tensorprod
    X = _double_full(X)
    for d in range(len(x)):
        x[d] = _double_full(x[d])
        X = _tensorprod(X, x[d].reshape(-1, order="F"), DIM[d], 1)
        DIM = DIM - 1

    return matlab_scalar(X)


def _iscell(x):
    if sparse.issparse(x):
        return False
    if isinstance(x, np.ndarray):
        return x.dtype == object
    if isinstance(x, (list, tuple)):
        return any(isinstance(xi, (list, tuple, np.ndarray)) for xi in x)
    return False


def _cell_list(x):
    if isinstance(x, np.ndarray):
        return list(x.ravel(order="F"))
    return list(x)


def _scalar(x):
    return np.asarray(full(x)).reshape(-1, order="F")[0]


def _double_full(x):
    return np.asarray(as_matlab_array(full(x)), dtype=float)


def _size(x):
    return np.array(matlab_size(x))


def _tensorprod(X, x, dim_X, dim_x):
    X = np.tensordot(X, x, axes=([int(dim_X) - 1], [int(dim_x) - 1]))
    X = np.asarray(X)
    if X.ndim == 0:
        X = X.reshape((1, 1))
    elif X.ndim == 1:
        X = X.reshape((X.shape[0], 1))
    return X
