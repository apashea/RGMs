"""
Expected information gain (mutual information) for Dirichlet parameters.

Translated from spm_dir_MI.m (Pass 1). Local entropy helper mirrors
subfunction `spm_H`, using SciPy `psi` (digamma) like MATLAB `psi`.

**Cell + `h` branch:** staged MATLAB line 25 calls `spm_dir_MI(a{g},c{g},h)` with
the full multimodal `h`, which mis-dimensions `sum(A,1)*H` when `numel(h)>1`.
Python passes the per-modality slice `h[g]` (aligned with `a{g}` / `c{g}`); oracle
for multimodal + `h` compares against the MATLAB **sum of per-modality** calls.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Union

import numpy as np
from scipy.special import psi

from matlab_compat import as_matlab_array
from python_src.spm_cat import spm_cat
from python_src.spm_log import spm_log


ArrayLike = Union[np.ndarray, List[Any], tuple]

_MISSING = object()


def _iscell_arg(x: Any) -> bool:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return True
    if isinstance(x, (list, tuple)) and len(x) > 0:
        # MATLAB `iscell(a)`; avoid treating a plain numeric list like `[1, 2]`
        # as a cell of modalities (those are `double` in MATLAB).
        if all(isinstance(item, np.ndarray) for item in x):
            return True
        if isinstance(x[0], (list, tuple)):
            return True
    return False


def _numel_cell(x: Sequence[Any]) -> int:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return int(x.size)
    return len(x)


def _cell_get(x: Sequence[Any], index: int) -> Any:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return x.reshape(-1, order="F")[index]
    return x[index]


def _marginals_sum_matlab_like(a_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``sum(a,2)`` and ``sum(a,1)`` with sequential float accumulation (MATLAB ``sum``).

    NumPy ``np.sum(..., axis=...)`` can use pairwise reduction; SPM marginals feed
    ``spm_H`` and drive MI cancellation at ~ULP scale on large grids.
    """
    a_arr = np.asarray(a_arr, dtype=np.float64)
    nr, nc = int(a_arr.shape[0]), int(a_arr.shape[1])
    col_sums = np.zeros((nr, 1), dtype=np.float64)
    row_sums = np.zeros((1, nc), dtype=np.float64)
    for i in range(nr):
        s = 0.0
        for j in range(nc):
            s += float(a_arr[i, j])
        col_sums[i, 0] = s
    for j in range(nc):
        s = 0.0
        for i in range(nr):
            s += float(a_arr[i, j])
        row_sums[0, j] = s
    return col_sums, row_sums


def _sum_all_matlab_like(a_arr: np.ndarray) -> float:
    """``sum(a,'all')`` in linear index order ``a(:)`` (column-major)."""
    av = np.asarray(a_arr, dtype=np.float64).reshape(-1, order="F")
    s = 0.0
    for x in av:
        s += float(x)
    return float(s)


def _sum_axis1_matlab_like(a_arr: np.ndarray) -> np.ndarray:
    """``sum(A,2)`` for compatibility with outcome-cost term (column vector)."""
    a_arr = np.asarray(a_arr, dtype=np.float64)
    nr, nc = int(a_arr.shape[0]), int(a_arr.shape[1])
    out = np.zeros((nr, 1), dtype=np.float64)
    for i in range(nr):
        s = 0.0
        for j in range(nc):
            s += float(a_arr[i, j])
        out[i, 0] = s
    return out


def _sum_axis0_matlab_like(a_arr: np.ndarray) -> np.ndarray:
    """``sum(A,1)`` as row vector for state-cost term."""
    a_arr = np.asarray(a_arr, dtype=np.float64)
    nr, nc = int(a_arr.shape[0]), int(a_arr.shape[1])
    out = np.zeros((1, nc), dtype=np.float64)
    for j in range(nc):
        s = 0.0
        for i in range(nr):
            s += float(a_arr[i, j])
        out[0, j] = s
    return out


def _spm_H(a: np.ndarray) -> float:
    """Differential entropy of a Dirichlet distribution (MATLAB local `spm_H`).

    MATLAB ``spm_H`` applies ``sum`` to vectors in linear-index order (column-major
    storage). Flatten ``a`` with Fortran order before accumulating so marginal/joint
    entropy paths match MATLAB ``spm_dir_MI`` cancellation behavior on tiny MI.
    """
    av = np.asarray(a, dtype=np.float64).reshape(-1, order="F")
    a0 = 0.0
    for x in av:
        a0 += float(x)
    if a0 == 0.0:
        raise ValueError("spm_H: sum(a) is zero")
    s = 0.0
    for i in range(av.size):
        s += float(av[i]) * float(psi(float(av[i]) + 1.0))
    return float(psi(a0 + 1.0) - s / a0)


def spm_dir_MI(
    a: ArrayLike,
    c: Any = _MISSING,
    h: Any = _MISSING,
) -> float:
    """
    FORMAT E = spm_dir_MI(a)
    FORMAT E = spm_dir_MI(a, c)
    FORMAT E = spm_dir_MI(a, c, h)

    Use ``spm_dir_MI(a, [], h)`` to supply ``h`` with an empty outcome preference
    vector (matches MATLAB ``spm_dir_MI(a, [], h)`` with ``nargin > 1``).
    """
    if _iscell_arg(a):
        total = 0.0
        ng = _numel_cell(a)  # type: ignore[arg-type]
        for g in range(ng):
            ag = _cell_get(a, g)  # type: ignore[arg-type]
            if h is not _MISSING:
                cg = _cell_get(c, g)  # type: ignore[arg-type,union-attr]
                hg = _cell_get(h, g)  # type: ignore[arg-type,union-attr]
                total += spm_dir_MI(ag, cg, hg)
            elif c is not _MISSING:
                cg = _cell_get(c, g)  # type: ignore[arg-type,union-attr]
                total += spm_dir_MI(ag, cg)
            else:
                total += spm_dir_MI(ag)
        return float(total)

    a_arr = np.asarray(a, dtype=np.float64)
    if a_arr.ndim != 2:
        n0 = int(a_arr.shape[0])
        a_arr = np.reshape(a_arr, (n0, -1), order="F")

    col_sums = np.sum(a_arr, axis=1, keepdims=True)
    row_sums = np.sum(a_arr, axis=0, keepdims=True)
    flat = np.reshape(a_arr, (-1, 1), order="F")

    e_val = _spm_H(col_sums) + _spm_H(row_sums) - _spm_H(flat)

    big_a: Optional[np.ndarray] = None
    if c is not _MISSING or h is not _MISSING:
        denom = float(np.sum(a_arr))
        if denom == 0.0:
            raise ValueError("spm_dir_MI: sum(a,'all') is zero")
        big_a = a_arr / denom

    if c is not _MISSING:
        c_arr = as_matlab_array(np.asarray(c, dtype=np.float64))
        c_col = np.reshape(c_arr, (-1, 1), order="F")
        if big_a is None:
            raise RuntimeError("internal: big_a unset")
        if c_col.size > 0:
            c_sum = float(np.sum(c_col))
            if c_sum != 0.0:
                c_col = c_col / c_sum
            cap_c = spm_log(c_col)
            s2 = _sum_axis1_matlab_like(big_a)
            e_val = e_val + float(np.asarray(cap_c.T @ s2, dtype=np.float64).reshape(-1)[0])

    if h is not _MISSING:
        if big_a is None:
            raise ValueError(
                "spm_dir_MI: third argument h requires second argument c to be "
                "passed (use [] for empty c, matching MATLAB nargin > 1)."
            )
        h_wrapped: Any = h
        h_cat = spm_cat(h_wrapped)
        h_mat = np.asarray(h_cat.todense() if hasattr(h_cat, "todense") else h_cat, dtype=np.float64)
        h_col = np.reshape(h_mat, (-1, 1), order="F")
        if h_col.size > 0:
            h_sum = float(np.sum(h_col))
            if h_sum != 0.0:
                h_col = h_col / h_sum
            cap_h = spm_log(h_col)
            s1 = _sum_axis0_matlab_like(big_a)
            e_val = e_val + float(np.asarray(s1 @ cap_h, dtype=np.float64).reshape(-1)[0])

    return float(e_val)
