import numpy as np
from scipy import sparse


def spm_dir_reduce(a):
    # distance matrix (i.e., normalised vectors on a hypersphere)
    from python_src.toolbox.DEM.spm_information_distance import (
        spm_information_distance,
    )

    D, _ = spm_information_distance(a)

    # discretise and return indices of unique outcomes
    i, j = _unique_rows_stable(np.asarray(D) < np.sqrt(2))

    # restriction matrix for reduction of likelihood
    Ns = np.size(i)
    jj = np.asarray(j).reshape(-1, order="F") - 1
    R = sparse.csr_matrix(
        (np.ones(np.size(jj)), (np.arange(np.size(jj)), jj)),
        shape=(np.size(jj), Ns),
    )

    return R


def _unique_rows_stable(x):
    x = np.asarray(x)
    if x.ndim == 1:
        x = np.reshape(x, (-1, 1), order="F")

    rows = {}
    i = []
    j = []
    for row in range(x.shape[0]):
        key = tuple(x[row, :].tolist())
        if key not in rows:
            rows[key] = len(i) + 1
            i.append(row + 1)
        j.append(rows[key])

    return np.asarray(i).reshape((-1, 1)), np.asarray(j).reshape((-1, 1))
