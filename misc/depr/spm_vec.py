import numpy as np
from scipy import sparse

from matlab_compat import as_matlab_array


def spm_vec(X, *varargin):
    if len(varargin) > 0:
        X = [X] + list(varargin)

    if _isnumeric(X) and not _islogical_array(X):
        if sparse.issparse(X):
            dense = np.asarray(X.toarray(), order="F", dtype=float)
            vX = dense.reshape((-1, 1), order="F")
            return vX
        X = as_matlab_array(np.asarray(X, dtype=float))
        vX = np.asarray(X, dtype=float).reshape((-1, 1), order="F")
        return vX

    if _islogical_array(X):
        if sparse.issparse(X):
            dense = np.asarray(X.toarray(), order="F", dtype=bool)
            return dense.reshape((-1, 1), order="F")
        X = as_matlab_array(np.asarray(X, dtype=bool))
        vX = np.asarray(X, dtype=bool).reshape((-1, 1), order="F")
        return vX

    if _isstruct(X):
        vX = np.empty((0, 1), dtype=float)
        f = _fieldnames(X)
        structs = _struct_as_list(X)
        for i in range(len(f)):
            vals = [s[f[i]] for s in structs]
            piece = spm_vec(vals)
            vX = np.vstack((vX, _as_float_column(piece)))
        return vX

    if _iscell(X):
        vX = np.empty((0, 1), dtype=float)
        arr = _cell_as_object_array(X)
        for flat in range(arr.size):
            sub = np.unravel_index(flat, arr.shape, order="F")
            piece = spm_vec(arr[sub])
            vX = np.vstack((vX, _as_float_column(piece)))
        return vX

    return np.empty((0, 1), dtype=float)


def _as_float_column(piece):
    if sparse.issparse(piece):
        piece = np.asarray(piece.toarray(), order="F", dtype=float)
    if piece.dtype == bool or np.issubdtype(piece.dtype, np.bool_):
        piece = np.asarray(piece, dtype=float)
    return np.asarray(piece, dtype=float).reshape((-1, 1), order="F")


def _fieldnames(X):
    if isinstance(X, dict):
        return list(X.keys())
    return list(X[0].keys())


def _struct_as_list(X):
    if isinstance(X, dict):
        return [X]
    return list(X)


def _isstruct(X):
    if isinstance(X, dict):
        return True
    if isinstance(X, list) and len(X) > 0 and all(isinstance(e, dict) for e in X):
        return True
    return False


def _islogical_array(X):
    if sparse.issparse(X):
        return X.dtype == bool or np.issubdtype(X.dtype, np.bool_)
    if isinstance(X, np.ndarray):
        return X.dtype == bool or np.issubdtype(X.dtype, np.bool_)
    return False


def _isnumeric(X):
    if sparse.issparse(X):
        return True
    if isinstance(X, (int, float, complex, np.number)):
        return True
    if isinstance(X, np.ndarray) and X.dtype != object:
        return True
    if isinstance(X, (list, tuple)):
        if len(X) == 0:
            return True
        if any(isinstance(x, (list, tuple, dict)) for x in X):
            return False
        if any(isinstance(x, np.ndarray) for x in X):
            return False
        return all(isinstance(x, (int, float, complex, np.number)) for x in X)
    return False


def _iscell(X):
    if sparse.issparse(X):
        return False
    if isinstance(X, np.ndarray) and X.dtype == object:
        return True
    if isinstance(X, (list, tuple)):
        return any(
            isinstance(xi, (list, tuple, np.ndarray, dict)) for xi in X
        )
    return False


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
