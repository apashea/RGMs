"""OPTIM1 — ``spm_information_distance`` (Tier B2: merge-shaped fast paths).

Tier **B2d** (2026-06-16): fuse per-part ``spm_dir_norm`` into merge-shaped concat
(``_merge_fast_cat_matrix_dirnorm``). **Does not remove** column normalization —
per-part ``dir_norm`` before horizontal concat is required for fidelity (differs from
normalizing the concatenated matrix). Slow path still calls ``spm_dir_norm``.

Tier **B2e** (2026-06-16): 2-D column ``dir_norm`` fast path in ``_dir_norm_dense_2d``
(avoid reshape/prod on merge-shaped blocks); indexed part loop in cat+dirnorm.

Tier **B2f** (2026-06-16): ``_dir_norm_dense_2d_into`` + preallocated group rows in
``_merge_fast_cat_matrix_dirnorm`` (drop per-part alloc + ``concatenate``).
"""

import numpy as np

from matlab_compat import as_matlab_array, full
from python_src.spm_cat import spm_cat
from python_src.spm_cov2corr import spm_cov2corr
from python_src.spm_dir_norm import spm_dir_norm


def spm_information_distance_optim(a):
    if _is_merge_fast_combined(a):
        ng = _size(a, 1)
        return _merge_fast_gram_corr_distance_dirnorm_cat(a, ng)
    a = spm_dir_norm(a)
    ng = _size(a, 1)
    c = spm_cat(a)
    c = spm_cov2corr(c.T @ c)
    d = 2 * np.sqrt(2) * ng * (1 - full(c))
    return d, c


def _merge_fast_gram_corr_distance_dirnorm_cat(a, ng):
    big = _merge_fast_cat_matrix_dirnorm(a)
    c = spm_cov2corr(big.T @ big)
    d = 2 * np.sqrt(2) * ng * (1 - full(c))
    return d, c


def _dir_norm_dense_2d(arr: np.ndarray) -> np.ndarray:
    """One dense block: column-normalize with ``spm_dir_norm`` semantics (no cell walk)."""
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim == 2:
        out = np.empty_like(arr)
        _dir_norm_dense_2d_into(out, arr)
        return out
    if arr.ndim == 0:
        arr = np.reshape(arr, (1, 1), order="F")
    siz = arr.shape
    flat = np.reshape(arr, (siz[0], int(np.prod(siz[1:]))), order="F")
    with np.errstate(divide="ignore", invalid="ignore"):
        a0 = np.sum(flat, axis=0, keepdims=True)
        mask = np.asarray(a0, dtype=bool).ravel(order="F")
        flat = np.divide(flat, a0)
        if siz[0] > 0:
            flat[:, ~mask] = 1.0 / siz[0]
    return np.reshape(flat, siz, order="F")


def _dir_norm_dense_2d_into(out: np.ndarray, arr: np.ndarray) -> None:
    """Write column-normalized ``arr`` into ``out`` (same 2-D shape)."""
    nrow, _ncol = arr.shape
    with np.errstate(divide="ignore", invalid="ignore"):
        col_sum = np.sum(arr, axis=0, keepdims=True)
        np.divide(arr, col_sum, out=out)
        if nrow > 0:
            zero_cols = (col_sum == 0).ravel()
            if zero_cols.any():
                out[:, zero_cols] = 1.0 / nrow


def _merge_fast_cat_matrix_dirnorm(a):
    """Per-part ``dir_norm`` then ``hstack`` / ``vstack`` — preallocated group rows."""
    rows = []
    for group in a:
        nrow = int(group[0].shape[0])
        ncol_total = sum(int(x.shape[1]) for x in group)
        big_row = np.empty((nrow, ncol_total), dtype=np.float64)
        c0 = 0
        for x in group:
            nc = int(x.shape[1])
            _dir_norm_dense_2d_into(big_row[:, c0 : c0 + nc], x)
            c0 += nc
        rows.append(big_row)
    return np.vstack(rows)


def _merge_fast_cat_matrix(a):
    """``spm_cat`` on ``[[ndarray, …], …]`` without cell/sparse partition overhead."""
    rows = []
    for group in a:
        parts = [np.asarray(x) for x in group]
        rows.append(np.concatenate(parts, axis=1))
    return np.vstack(rows)


def _is_merge_fast_combined(a):
    """``[[ndarray, ...], ...]`` layout from ``_spm_merge_fast`` ``combined``."""
    if not isinstance(a, (list, tuple)) or len(a) == 0:
        return False
    ncol = None
    for group in a:
        if not isinstance(group, (list, tuple)) or len(group) == 0:
            return False
        if ncol is None:
            ncol = len(group)
        elif len(group) != ncol:
            return False
        for arr in group:
            if not isinstance(arr, np.ndarray):
                return False
            if arr.dtype == object:
                return False
    return True


def _size(a, dim):
    if _iscell(a):
        siz = _cell_size(a)
    else:
        siz = np.shape(as_matlab_array(a))
    if dim <= len(siz):
        return siz[dim - 1]
    return 1


def _iscell(a):
    if isinstance(a, np.ndarray):
        return a.dtype == object
    return isinstance(a, (list, tuple))


def _cell_size(a):
    if isinstance(a, np.ndarray):
        if a.ndim == 0:
            return (1, 1)
        if a.ndim == 1:
            return (1, a.shape[0])
        return a.shape
    if len(a) > 0 and all(isinstance(row, (list, tuple)) for row in a):
        return (len(a), len(a[0]))
    return (1, len(a))
