"""OPTIM1 — ``spm_unique`` (Tier B2v0 fork + B2c ``_unique_rows_stable``)."""

import numpy as np

from matlab_compat import matlab_scalar
from python_src.optimized.toolbox.DEM.spm_information_distance_optim import (
    spm_information_distance_optim,
)


def spm_unique_optim(O):
    d, _ = spm_information_distance_optim(O)
    i, j = _unique_rows_stable(np.asarray(d) < 2)
    return matlab_scalar(i), matlab_scalar(j)


def _unique_rows_stable(x):
    x = np.asarray(x)
    if x.ndim == 1:
        x = np.reshape(x, (-1, 1), order="F")
    x = np.ascontiguousarray(x)

    rows = {}
    i = []
    j = np.empty(x.shape[0], dtype=np.int64)
    for row in range(x.shape[0]):
        key = x[row].tobytes()
        if key not in rows:
            rows[key] = len(i) + 1
            i.append(row + 1)
        j[row] = rows[key]

    return np.asarray(i, dtype=np.int64).reshape((-1, 1)), j.reshape((-1, 1))
