"""
Sparse leading diagonal matrix (MATLAB-compatible).

Translated from spm_speye.m (Pass 1 faithful transliteration).
"""

from __future__ import annotations

import numpy as np
from scipy import sparse


def _spdiags_ones_k(m: int, n: int, k: int) -> sparse.csr_matrix:
    """MATLAB: spdiags(ones(m,1), k, m, n)."""
    m = int(m)
    n = int(n)
    k = int(k)
    i0 = max(0, -k)
    i1 = min(m - 1, n - 1 - k)
    if i1 < i0:
        return sparse.csr_matrix((m, n), dtype=np.float64)
    ii = np.arange(i0, i1 + 1, dtype=np.int32)
    jj = ii + k
    data = np.ones(ii.size, dtype=np.float64)
    return sparse.csr_matrix((data, (ii, jj)), shape=(m, n))


def spm_speye(m, *args) -> sparse.csr_matrix:
    """
    FORMAT D = spm_speye(m,n,k,c,o)

    Positional tail mirrors MATLAB nargin (after m).
    """
    if len(args) >= 1:
        n = args[0]
    else:
        n = m
    if len(args) >= 2:
        k = args[1]
    else:
        k = 0
    if len(args) >= 3:
        c = args[2]
    else:
        c = 0
    if len(args) >= 4:
        o = args[3]
    else:
        o = 1

    m = int(m)
    n = int(n)
    k = int(k)
    c = int(c)
    o = int(o)

    D = _spdiags_ones_k(m, n, k)

    if c == 1:
        if k < 0:
            D = D + spm_speye(m, n, min(n, m) + k)
        elif k > 0:
            D = D + spm_speye(m, n, k - min(n, m))
    elif c == 2:
        # MATLAB: i = find(~any(D));  any(D) is column-wise for 2-D matrices
        col_nnz = np.diff(D.tocsc().indptr)
        i = np.where(col_nnz == 0)[0] + 1  # 1-based column indices (MATLAB find)
        if i.size > 0:
            rows = (i - 1).astype(np.int32)
            cols = (i - 1).astype(np.int32)
            data = np.ones(i.size, dtype=np.float64)
            S = sparse.coo_matrix((data, (rows, cols)), shape=(n, m)).tocsr()
            D = D + S

    if m == n:
        D = D**o

    return D.tocsr()
