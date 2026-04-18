import numpy as np
from scipy import sparse

from matlab_compat import (
    as_matlab_array,
    full,
    matlab_ndims,
    matlab_size,
    trim_trailing_singletons,
)


def spm_cross(X, x=None, *varargin):
    # handle single inputs
    if x is None:
        if _iscell(X):
            return spm_cross(*_cell_contents(X))
        else:
            Y = as_matlab_array(X)
        return Y

    # handle cell arrays
    if _iscell(X):
        X = spm_cross(*_cell_contents(X))
    if _iscell(x):
        x = spm_cross(*_cell_contents(x))

    # outer product of first pair of arguments (using bsxfun)
    A = np.reshape(full(X), matlab_size(X) + (1,) * matlab_ndims(x), order="F")
    B = np.reshape(full(x), (1,) * matlab_ndims(X) + matlab_size(x), order="F")
    Y = A * B
    siz = np.asarray(matlab_size(Y))
    siz = siz[siz > 1]
    if siz.size:
        Y = np.reshape(Y, tuple(siz.tolist()) + (1,), order="F")
    Y = trim_trailing_singletons(Y)

    # and handle remaining arguments
    for i in range(len(varargin)):
        Y = spm_cross(Y, varargin[i])

    return Y


def _iscell(x):
    if sparse.issparse(x):
        return False
    if isinstance(x, np.ndarray):
        return x.dtype == object
    if isinstance(x, (list, tuple)):
        return len(x) > 0
    return False


def _cell_contents(x):
    if isinstance(x, np.ndarray):
        if x.ndim == 0:
            return [x.item()]
        return list(x.ravel(order="F"))
    if isinstance(x, tuple):
        x = list(x)
    if len(x) > 0 and all(isinstance(row, (list, tuple)) for row in x):
        n = len(x)
        m = len(x[0])
        return [x[i][j] for j in range(m) for i in range(n)]
    return list(x)
