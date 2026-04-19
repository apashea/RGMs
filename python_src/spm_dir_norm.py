import numpy as np

from matlab_compat import as_matlab_array


def spm_dir_norm(A):
    # deal with cells
    if _iscell(A):
        A = _copy_cell(A)
        for g in range(_numel(A)):
            if not callable(_cell_get(A, g)):
                _cell_set(A, g, spm_dir_norm(_cell_get(A, g)))
        return A

    # deal with Dirichlet tensors
    A = as_matlab_array(A)
    if A.ndim == 0:
        A = np.reshape(A, (1, 1), order="F")
    siz = np.shape(A)
    A = np.reshape(A, (siz[0], int(np.prod(siz[1:]))), order="F")
    A0 = np.sum(A, axis=0, keepdims=True)
    i = np.asarray(A0, dtype=bool).ravel(order="F")
    A = np.divide(A, A0)
    A[:, ~i] = 1 / siz[0]
    A = np.reshape(A, siz, order="F")

    return A


def _iscell(A):
    if isinstance(A, np.ndarray):
        return A.dtype == object
    return isinstance(A, (list, tuple))


def _copy_cell(A):
    if isinstance(A, np.ndarray):
        return A.copy()
    if isinstance(A, tuple):
        return list(A)
    return list(A)


def _numel(A):
    if isinstance(A, np.ndarray):
        return A.size
    return len(A)


def _cell_get(A, i):
    if isinstance(A, np.ndarray):
        return A.ravel(order="F")[i]
    return A[i]


def _cell_set(A, i, value):
    if isinstance(A, np.ndarray):
        A.ravel(order="F")[i] = value
    else:
        A[i] = value
