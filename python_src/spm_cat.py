import numpy as np
from scipy import sparse


def spm_cat(x, d=None):
    # check x is not already a matrix
    if not _iscell(x):
        return _row_vector(x)

    x = _cell2d(x)

    # if concatenation over a specific dimension
    n, m = _cell_size(x)
    if d is not None:

        # concatenate over first dimension
        if d == 1:
            y = [None] * m
            for i in range(m):
                y[i] = spm_cat([[x[j][i]] for j in range(n)])

        # concatenate over second
        elif d == 2:

            y = [[None] for _ in range(n)]
            for i in range(n):
                y[i][0] = spm_cat([x[i]])

        # only viable for 2-D arrays
        else:
            raise ValueError("uknown option")
        x = y
        return x

    # find dimensions to fill in empty partitions
    I = np.zeros((n, m), dtype=int)
    J = np.zeros((n, m), dtype=int)
    for i in range(n):
        for j in range(m):
            if _iscell(x[i][j]):
                x[i][j] = spm_cat(x[i][j])
            u, v = _size(x[i][j])
            I[i, j] = u
            J[i, j] = v
    I = np.max(I, axis=1)
    J = np.max(J, axis=0)

    # sparse and empty partitions
    n, m = _cell_size(x)
    for i in range(n):
        for j in range(m):
            if _isempty(x[i][j]):
                x[i][j] = sparse.csr_matrix((I[i], J[j]))

    # concatenate
    y = [None] * n
    for i in range(n):
        y[i] = _cat(1, x[i])
    try:
        x = sparse.csr_matrix(_cat(0, y))
    except Exception:
        x = _cat(0, y)

    return x


def _iscell(x):
    if sparse.issparse(x):
        return False
    if isinstance(x, np.ndarray):
        return x.dtype == object
    if isinstance(x, (list, tuple)):
        return len(x) > 0
    return False


def _cell2d(x):
    if isinstance(x, np.ndarray):
        if x.ndim == 0:
            return [[x.item()]]
        if x.ndim == 1:
            return [list(x)]
        return [[x[i, j] for j in range(x.shape[1])] for i in range(x.shape[0])]
    if isinstance(x, tuple):
        x = list(x)
    if len(x) > 0 and all(isinstance(row, (list, tuple)) for row in x):
        return [list(row) for row in x]
    return [list(x)]


def _row_vector(x):
    if sparse.issparse(x):
        return x
    x = np.asarray(x)
    if x.ndim == 1:
        return x.reshape((1, x.shape[0]))
    return x


def _cell_size(x):
    if len(x) == 0:
        return 0, 0
    return len(x), len(x[0])


def _size(x):
    if sparse.issparse(x):
        return x.shape
    x = np.asarray(x)
    if x.ndim == 0:
        return 1, 1
    if x.ndim == 1:
        if x.size == 0:
            return 0, 0
        return 1, x.shape[0]
    return x.shape[0], x.shape[1]


def _isempty(x):
    if sparse.issparse(x):
        return x.shape[0] == 0 or x.shape[1] == 0
    return np.asarray(x).size == 0


def _asarray2d(x):
    if sparse.issparse(x):
        return x
    x = np.asarray(x)
    if x.ndim == 0:
        return x.reshape((1, 1))
    if x.ndim == 1:
        if x.size == 0:
            return x.reshape((0, 0))
        return x.reshape((1, x.shape[0]))
    return x


def _cat(dim, x):
    x = [_asarray2d(xi) for xi in x]
    if any(sparse.issparse(xi) for xi in x):
        if dim == 0:
            return sparse.vstack(x, format="csr")
        return sparse.hstack(x, format="csr")
    return np.concatenate(x, axis=dim)
