import numpy as np

from matlab_compat import matlab_scalar


def spm_unique(O):
    # distance matrix (i.e., normalised vectors on a hypersphere)
    from python_src.toolbox.DEM.spm_information_distance import (
        spm_information_distance,
    )

    D, _ = spm_information_distance(O)

    # discretise and return indices of unique outcomes
    i, j = _unique_rows_stable(np.asarray(D) < 2)

    return matlab_scalar(i), matlab_scalar(j)


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
