import types

import numpy as np
from scipy import sparse

from matlab_compat import as_matlab_array


def spm_dir_norm(A):
    if _iscell(A):
        arr = _cell_as_object_array(A)
        out = np.empty_like(arr, dtype=object)
        for flat in range(arr.size):
            sub = np.unravel_index(flat, arr.shape, order="F")
            item = arr[sub]
            if _isa_function_handle(item):
                out[sub] = item
            else:
                out[sub] = spm_dir_norm(item)
        return out.tolist()

    A = as_matlab_array(A)
    A = np.asarray(A, dtype=float)
    if A.size == 0:
        return A
    n = A.shape[0]
    A0 = np.sum(A, axis=0, keepdims=True)
    i = A0 != 0
    with np.errstate(invalid="ignore", divide="ignore"):
        A = np.divide(A, A0)
    cols = np.where(~i.reshape(-1))[0]
    if cols.size and n > 0:
        A[:, cols] = 1.0 / n
    return A


def _isa_function_handle(x):
    return isinstance(x, (types.FunctionType, types.MethodType))


def _cell_as_object_array(A):
    if isinstance(A, np.ndarray) and A.dtype == object:
        return A
    if isinstance(A, (list, tuple)):
        if len(A) == 0:
            return np.empty((0,), dtype=object)
        if all(isinstance(x, np.ndarray) for x in A):
            out = np.empty(len(A), dtype=object)
            for i, x in enumerate(A):
                out[i] = x
            return out
        if all(isinstance(x, (list, tuple)) for x in A):
            nrows = len(A)
            ncols = len(A[0])
            out = np.empty((nrows, ncols), dtype=object)
            for i in range(nrows):
                for j in range(ncols):
                    out[i, j] = A[i][j]
            return out
    return np.asarray(A, dtype=object)


def _iscell(x):
    if sparse.issparse(x):
        return False
    if isinstance(x, np.ndarray):
        return x.dtype == object
    if isinstance(x, (list, tuple)):
        return any(isinstance(xi, (list, tuple, np.ndarray)) for xi in x)
    return False
