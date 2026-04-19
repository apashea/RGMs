import numpy as np
from scipy import sparse

from matlab_compat import as_matlab_array
from misc.depr.spm_vec import spm_vec


def spm_unvec(vX, *varargin):
    if len(varargin) == 1:
        X = varargin[0]
    else:
        X = list(varargin)

    if not (_is_numeric_like(vX) or _is_logical_vector(vX)):
        vX = spm_vec(vX)

    vX = np.asarray(vX)
    if vX.ndim == 1:
        vX = vX.reshape((-1, 1), order="F")
    elif vX.ndim == 0:
        vX = vX.reshape((1, 1), order="F")

    if _is_leaf_numeric_or_logical(X):
        X = _leaf_template_orientation(X)
        if not _ismatrix(X):
            out = np.array(X, copy=True)
            flat = out.reshape((-1, 1), order="F")
            vfull = np.asarray(vX)
            if sparse.issparse(vfull):
                vfull = vfull.toarray()
            src = np.asarray(vfull, dtype=out.dtype).reshape((-1,), order="F")[: flat.shape[0]]
            flat[:, 0] = src
            return out
        if sparse.issparse(X):
            dense = np.asarray(vX, dtype=float).reshape(X.shape, order="F")
            return sparse.csr_matrix(dense)
        out = np.array(X, copy=True, order="F")
        flat = out.reshape((-1, 1), order="F")
        vcol = np.asarray(vX)
        if sparse.issparse(vcol):
            vcol = vcol.toarray()
        if out.dtype == bool or np.issubdtype(out.dtype, np.bool_):
            flat[:, 0] = np.asarray(vcol, dtype=out.dtype).reshape((-1,), order="F")[: flat.shape[0]]
        else:
            flat[:, 0] = np.asarray(vcol, dtype=float).reshape((-1,), order="F")[: flat.shape[0]]
        return out

    if _isstruct(X):
        f = _fieldnames(X)
        structs = _struct_as_list(X)
        offset = 0
        for i in range(len(f)):
            fname = f[i]
            c = [s[fname] for s in structs]
            c_cell = _row_cell_from_list(c)
            n = int(_spm_length(c_cell))
            filled = spm_unvec(vX[offset : offset + n, :], c_cell)
            if isinstance(filled, list):
                for k in range(len(structs)):
                    structs[k][fname] = filled[k]
            else:
                structs[0][fname] = filled
            offset = offset + int(n)
        if isinstance(X, dict):
            return structs[0]
        return structs

    if _iscell(X):
        arr = _cell_as_object_array(X)
        out = np.empty_like(arr, dtype=object)
        offset = 0
        for flat in range(arr.size):
            sub = np.unravel_index(flat, arr.shape, order="F")
            item = arr[sub]
            if _isnumeric_leaf(item):
                n = int(np.size(item))
            else:
                n = int(_spm_length(item))
            out[sub] = spm_unvec(vX[offset : offset + n, :], item)
            offset = offset + n
        return out.tolist()

    return []


def _leaf_template_orientation(X):
    if isinstance(X, np.ndarray) and X.ndim == 1:
        if X.dtype == bool or np.issubdtype(X.dtype, np.bool_):
            return as_matlab_array(np.asarray(X, dtype=bool))
        return as_matlab_array(np.asarray(X, dtype=float))
    return X


def _row_cell_from_list(vals):
    out = np.empty((len(vals),), dtype=object)
    for i, v in enumerate(vals):
        out[i] = v
    return out


def _spm_length(X):
    if _isnumeric_leaf(X):
        return int(np.size(X))
    if _islogical_leaf(X):
        return int(np.size(X))
    if _isstruct(X):
        n = 0
        f = _fieldnames(X)
        structs = _struct_as_list(X)
        for i in range(len(f)):
            fname = f[i]
            for j in range(len(structs)):
                n = n + _spm_length(structs[j][fname])
        return int(n)
    if _iscell(X):
        if isinstance(X, np.ndarray) and X.dtype == object:
            arr = X
        else:
            arr = _cell_as_object_array(X)
        n = 0
        for flat in range(arr.size):
            sub = np.unravel_index(flat, arr.shape, order="F")
            n = n + _spm_length(arr[sub])
        return int(n)
    return 0


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


def _ismatrix(X):
    if sparse.issparse(X):
        return True
    if isinstance(X, np.ndarray):
        return X.ndim <= 2
    if isinstance(X, (int, float, complex, np.number, bool, np.bool_)):
        return True
    return True


def _is_leaf_numeric_or_logical(X):
    return _isnumeric_leaf(X) or _islogical_leaf(X)


def _isnumeric_leaf(X):
    if sparse.issparse(X):
        return True
    if isinstance(X, (int, float, complex, np.number)):
        return True
    if isinstance(X, np.ndarray) and X.dtype != object:
        return not (X.dtype == bool or np.issubdtype(X.dtype, np.bool_))
    return False


def _islogical_leaf(X):
    if sparse.issparse(X):
        return X.dtype == bool or np.issubdtype(X.dtype, np.bool_)
    if isinstance(X, np.ndarray):
        return X.dtype == bool or np.issubdtype(X.dtype, np.bool_)
    return False


def _is_numeric_like(vX):
    if sparse.issparse(vX):
        return True
    if isinstance(vX, (int, float, complex, np.number)):
        return True
    if isinstance(vX, np.ndarray) and vX.dtype != object:
        return not (vX.dtype == bool or np.issubdtype(vX.dtype, np.bool_))
    return False


def _is_logical_vector(vX):
    if sparse.issparse(vX):
        return vX.dtype == bool or np.issubdtype(vX.dtype, np.bool_)
    if isinstance(vX, np.ndarray):
        return vX.dtype == bool or np.issubdtype(vX.dtype, np.bool_)
    return False
