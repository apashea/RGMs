"""
Combinations of factor indices (MATLAB-compatible).

Translated from spm_combinations.m (Pass 1 faithful transliteration).
"""

from __future__ import annotations

import numpy as np


def _is_cell_nu(Nu) -> bool:
    """True when Nu should follow MATLAB iscell(Nu) branch."""
    if isinstance(Nu, np.ndarray) and Nu.dtype == object:
        return True
    if isinstance(Nu, (list, tuple)) and len(Nu) > 0:
        first = Nu[0]
        if isinstance(first, np.ndarray):
            return True
        if isinstance(first, (list, tuple)):
            return True
    return False


def _u_colon(u: np.ndarray) -> np.ndarray:
    """MATLAB u(:) — column vector in column-major order."""
    return np.reshape(u, (-1, 1), order="F")


def spm_combinations(Nu) -> np.ndarray:
    """
    FORMAT U = spm_combinations(Nu)

    Nu is either a 1-D numeric vector of domain sizes (domains are 1:Nu(f)),
    or a MATLAB-cell-like sequence of 1-D index arrays (list/tuple of arrays).
    """
    if _is_cell_nu(Nu):
        if isinstance(Nu, np.ndarray) and Nu.dtype == object:
            cells = [np.asarray(Nu.flat[i]).reshape(1, -1) for i in range(Nu.size)]
        else:
            cells = [
                np.asarray(x, dtype=np.float64).reshape(1, -1) for x in Nu
            ]
        n_f = len(cells)
        nu = np.array([c.size for c in cells], dtype=np.int64)
        n_rows = int(np.prod(nu))
        u_out = np.zeros((n_rows, n_f), dtype=np.float64)
        for f in range(n_f):
            k_list = []
            for j in range(n_f):
                if j == f:
                    k_list.append(np.asarray(cells[j], dtype=np.float64))
                else:
                    k_list.append(np.ones((1, int(nu[j])), dtype=np.float64))
            u_mat = np.array([[1.0]], dtype=np.float64)
            for i in range(n_f):
                u_mat = np.kron(k_list[i], u_mat)
            u_out[:, f] = _u_colon(u_mat).ravel()
        return u_out

    nu_vec = np.asarray(Nu, dtype=np.int64).ravel()
    n_f = nu_vec.size
    n_rows = int(np.prod(nu_vec))
    u_out = np.zeros((n_rows, n_f), dtype=np.float64)
    for f in range(n_f):
        k_list = []
        for j in range(n_f):
            if j == f:
                k_list.append(
                    np.arange(1, int(nu_vec[j]) + 1, dtype=np.float64).reshape(1, -1)
                )
            else:
                k_list.append(np.ones((1, int(nu_vec[j])), dtype=np.float64))
        u_mat = np.array([[1.0]], dtype=np.float64)
        for i in range(n_f):
            u_mat = np.kron(k_list[i], u_mat)
        u_out[:, f] = _u_colon(u_mat).ravel()
    return u_out
