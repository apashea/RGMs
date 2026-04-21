"""
Kronecker tensor product with sparse outputs (MATLAB-compatible).

Translated from spm_kron.m (Pass 1 faithful transliteration).
"""

from __future__ import annotations

import numpy as np
from scipy import sparse


def _as_sparse(A):
    """MATLAB sparse(A) for numeric / logical dense or sparse arrays."""
    if sparse.issparse(A):
        return sparse.csr_matrix(A, dtype=np.float64)
    arr = np.asarray(A)
    if arr.dtype == bool or arr.dtype == np.bool_:
        return sparse.csr_matrix(arr.astype(np.float64))
    return sparse.csr_matrix(arr.astype(np.float64))


def _is_cell_vector(A) -> bool:
    """MATLAB iscell(A) — use list/tuple as 1-D cell vector."""
    return isinstance(A, (list, tuple))


def spm_kron(A, B=None) -> sparse.csr_matrix:
    """
    FORMAT K = spm_kron(A,B)
            K = spm_kron(A)   when A is a cell (list/tuple of matrices)

    Second argument B is ignored when A is cell-like (MATLAB behavior).
    """
    if _is_cell_vector(A):
        K = sparse.csr_matrix([[1.0]], dtype=np.float64)
        for i in range(len(A)):
            K = sparse.kron(_as_sparse(A[i]), K)
        return K.tocsr()

    if B is None:
        raise TypeError("spm_kron: two matrix arguments required when A is not a cell array")

    K = sparse.kron(_as_sparse(A), _as_sparse(B))
    return K.tocsr()
