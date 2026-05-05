"""
Multiple subscripts from linear index (MATLAB-compatible).

Translated from spm_index.m (Pass 1 faithful transliteration).
"""

from __future__ import annotations

import numpy as np


def spm_index(siz, ndx):
    """
    FORMAT ind = spm_index(siz, ndx)

    ``siz`` — MATLAB-like size vector (row or flat array).
    ``ndx`` — linear index (1-based, matching MATLAB).
    """
    siz = np.asarray(siz, dtype=float).reshape(-1)
    ndx_work = float(ndx)
    k = np.cumprod(siz)

    if np.prod(siz) == 1:
        if siz.size == 1:
            return np.array(float(siz[0]))
        return np.reshape(siz, (1, -1))

    ln = int(siz.size)
    ind_hi: list[float] = []
    if ln > 2:
        ind_hi = [0.0] * (ln - 2)
        for i in range(ln, 2, -1):
            vi = np.remainder(ndx_work - 1, k[i - 2]) + 1
            vj = (ndx_work - vi) / k[i - 2] + 1
            ind_hi[i - 3] = float(vj)
            ndx_work = float(vi)

    if ln >= 2:
        vi = np.remainder(ndx_work - 1, siz[0]) + 1
        v2 = (ndx_work - vi) / siz[0] + 1
        v1 = float(vi)
    else:
        v1 = float(ndx_work)
        raise ValueError("spm_index: internal variable v2 undefined (len(siz)==1, prod(siz)~=1)")

    out_list = [v1, float(v2)] + ind_hi
    return np.asarray(out_list, dtype=float).reshape(1, -1)

