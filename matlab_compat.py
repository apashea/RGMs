import numpy as np
from scipy import sparse


def as_matlab_array(x):
    x = full(x)
    x = np.asarray(x)
    if x.ndim == 1:
        x = x.reshape((1, x.shape[0]))
    return x


def full(x):
    if sparse.issparse(x):
        return x.toarray()
    return x


def matlab_scalar(x):
    if sparse.issparse(x):
        if x.shape == (1, 1):
            return x.toarray().reshape(-1, order="F")[0]
        return x
    x = np.asarray(x)
    if x.ndim == 0 or x.shape == (1, 1):
        return x.reshape(-1, order="F")[0]
    return x


def trim_trailing_singletons(x):
    siz = _trim_size(np.shape(x))
    if siz != np.shape(x):
        x = np.reshape(x, siz, order="F")
    return x


def matlab_size(x):
    if sparse.issparse(x):
        siz = x.shape
    else:
        x = np.asarray(x)
        if x.ndim == 0:
            siz = (1, 1)
        elif x.ndim == 1:
            if x.size == 0:
                siz = (0, 0)
            else:
                siz = (1, x.shape[0])
        else:
            siz = x.shape
    return _trim_size(siz)


def matlab_ndims(x):
    return len(matlab_size(x))


def _trim_size(siz):
    siz = tuple(siz)
    while len(siz) > 2 and siz[-1] == 1:
        siz = siz[:-1]
    if len(siz) == 0:
        return (1, 1)
    if len(siz) == 1:
        return siz + (1,)
    return siz
