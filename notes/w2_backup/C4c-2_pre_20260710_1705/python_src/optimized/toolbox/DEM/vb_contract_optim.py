"""Phase 6-C — fused native contractions on ``VbWorkspace`` layout.

Hot-path replacements for generic ``spm_dot`` / sparse slice-sum patterns.
Math authority: ``spm_MDP_VB_XXX.m`` local subs — not fidelity Python cosplay.

Gate: ``--vb-optim-tier3f`` per sub-step.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import scipy.sparse as sp

from python_src.spm_dot import spm_dot


def _dense_ndarray(x: Any) -> bool:
    return isinstance(x, np.ndarray) and x.dtype != object


def _flat_f64(q: np.ndarray) -> np.ndarray:
    """Column/row belief vector as 1-D float64 (view when possible)."""
    if q.ndim == 2 and q.shape[1] == 1:
        return q[:, 0]
    return q.reshape(-1, order="F")


def forwards_dot_cell_chain(x: np.ndarray, q_cells: list[np.ndarray]) -> np.ndarray:
    """``spm_dot(X, {q1..qn})`` — dense tensordot chain without ``matlab_compat`` tax."""
    xs = [_flat_f64(np.asarray(q, dtype=np.float64)) for q in q_cells]
    if len(xs) == 1 and xs[0].size == 1:
        return np.asarray(x, dtype=np.float64) * float(xs[0][0])
    out = np.asarray(x, dtype=np.float64)
    n = len(xs)
    dims_1b = list(range(1 + max(out.ndim, n) - n, 1 + max(out.ndim, n) - n + n))
    for d in range(n):
        axis = int(dims_1b[d]) - 1
        if axis >= out.ndim or out.shape[axis] != xs[d].size:
            raise ValueError("forwards dot cell: axis mismatch")
        out = np.tensordot(out, xs[d], axes=(axis, 0))
        dims_1b = [di - 1 for di in dims_1b]
    return np.asarray(out, dtype=np.float64)


def forwards_dot_A_qj(a: Any, qj: list[Any]) -> Any:
    """``spm_dot(A, qj)`` — policy-loop likelihood / ambiguity (**6-C-2**)."""
    if not _dense_ndarray(a):
        return spm_dot(a, qj)
    for q in qj:
        if not _dense_ndarray(q):
            return spm_dot(a, qj)
    try:
        return forwards_dot_cell_chain(a, qj)
    except (ValueError, IndexError):
        return spm_dot(a, qj)


def forwards_dot_vec_match(x: Any, q: Any) -> Any:
    """``spm_dot(X, q)`` — single matching-dim vector (e.g. log(C) with one Q factor)."""
    if not _dense_ndarray(x) or not _dense_ndarray(q):
        return spm_dot(x, q)
    xa = np.asarray(x, dtype=np.float64)
    qa = _flat_f64(np.asarray(q, dtype=np.float64))
    if qa.size == 1:
        return xa * float(qa[0])
    matches = np.where(np.array(xa.shape, dtype=np.int64) == int(qa.size))[0]
    if matches.size == 0:
        return spm_dot(x, q)
    dim = int(matches[0])
    return np.tensordot(xa, qa, axes=(dim, 0))


def forwards_dot_R_qcells(r: Any, q_cells: list[Any]) -> Any:
    """``spm_dot(R, q_cells)`` — induction risk contraction in forwards."""
    if not _dense_ndarray(r):
        return spm_dot(r, q_cells)
    for q in q_cells:
        if not _dense_ndarray(q):
            return spm_dot(r, q_cells)
    try:
        return forwards_dot_cell_chain(np.asarray(r, dtype=np.float64), list(q_cells))
    except (ValueError, IndexError):
        return spm_dot(r, q_cells)


def _ind_backward_any_rows_dense(prev: np.ndarray, bf_work: np.ndarray) -> np.ndarray:
    """MATLAB ``any(Bf(I(:,n),:),1)`` for dense ``Bf`` — active-row slice."""
    rows = np.flatnonzero(prev)
    ncols = int(bf_work.shape[1])
    if rows.size == 0:
        return np.zeros(ncols, dtype=bool)
    sub = bf_work[rows, :]
    if sub.dtype == bool:
        return np.any(sub, axis=0)
    return np.any(sub > 0, axis=0)


def ind_backward_paths_into(
    pf_col: np.ndarray,
    bf_prop: Any,
    horizon_n: int,
    i_big: np.ndarray,
    prev_f: np.ndarray,
    next_f: np.ndarray | None = None,
) -> None:
    """In-place backwards bool propagation — MATLAB ``any(Bf(I(:,n),:),1)`` per step.

    **C4b:** Dense ``Bf`` uses row-slice ``any`` when ``prev`` is sparse; scipy ``Bf`` keeps
    ``prev @ Bf`` (MATLAB sparse slice-sum); dense BLAS when most rows are active.
    """
    if next_f is None:
        next_f = np.empty(int(i_big.shape[0]), dtype=np.float64)
    i_big.fill(False)
    i_big[:, 0] = np.asarray(pf_col, dtype=bool)
    h = int(horizon_n)
    nrows = int(i_big.shape[0])

    if sp.issparse(bf_prop):
        for n in range(h):
            prev = i_big[:, n]
            if not np.any(prev):
                break
            rows = np.flatnonzero(prev)
            sub = bf_prop[rows, :]
            i_big[:, n + 1] = np.asarray(sub.sum(axis=0)).ravel() > 0
        return

    bf_f64: np.ndarray | None = None
    if isinstance(bf_prop, np.ndarray):
        bf_f64 = (
            bf_prop
            if bf_prop.dtype != bool
            else bf_prop.astype(np.float64, copy=False)
        )

    for n in range(h):
        prev = i_big[:, n]
        if not np.any(prev):
            break
        if bf_f64 is not None:
            nnz = int(np.count_nonzero(prev))
            if nnz > max(nrows // 4, 48):
                np.dot(prev, bf_f64, out=next_f)
                i_big[:, n + 1] = next_f > 0
                continue
            i_big[:, n + 1] = _ind_backward_any_rows_dense(prev, bf_prop)
        else:
            next_f[:] = prev.astype(np.float64) @ bf_prop
            i_big[:, n + 1] = next_f > 0
