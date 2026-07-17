"""
General MATLAB-aligned spectral post-processing for ``eig(...,'nobalance')`` pairs.

Used by ``eig_nobalance`` (OSS utils) and mirrored by ``spm_rgm_group`` sort behavior.
Entry 4 dumps are **validation only** — no Atari-specific logic here.
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np


def abs_tie_band_sort_enabled() -> bool:
    """B5.3 experiment: ULP tie-band buckets before ``sort(abs(...),'descend')`` (``eig.md`` §4.1)."""
    return str(os.getenv("RGMS_EIG_SPECTRAL_ABS_TIE_BAND_SORT", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def sort_abs_descend_matlab_tie_band(absv: np.ndarray, *, rtol: float = 1e-14) -> np.ndarray:
    """
    Descending ``sort(abs(e(:,jmax)))`` with **ULP tie bands** (reference-free).

    Values with ``|a[i]-a[j]| <= rtol * max(|a|)`` share a magnitude bucket; within a
    bucket, sort by increasing index (MATLAB stable-sort behavior among ties).
    """
    a = np.asarray(absv, dtype=np.float64).ravel()
    n = int(a.size)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    m = float(np.max(a))
    tol = max(1e-300, rtol * max(m, 1.0))
    level = np.floor(a / tol).astype(np.int64)
    idx = np.arange(n, dtype=np.int64)
    return np.lexsort((idx, -level)).astype(np.int64, copy=False)


def sort_abs_descend_for_spm_rgm(absv: np.ndarray) -> np.ndarray:
    """Active sort for ``spm_rgm_group`` / T0 (tie-band when env enabled)."""
    if abs_tie_band_sort_enabled():
        return sort_abs_descend_matlab_tie_band(absv)
    return sort_abs_descend_matlab_like(absv)


def sort_abs_descend_matlab_like(absv: np.ndarray) -> np.ndarray:
    """
    Permutation after MATLAB ``sort(abs(e(:,jmax)),'descend')`` on a column vector.

    Stable descending sort on ``|x|``; ties keep lower indices first (``mergesort``).
    """
    a = np.asarray(absv, dtype=np.float64).ravel()
    n = int(a.size)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    return np.argsort(-a, kind="mergesort").astype(np.int64, copy=False)


def canonicalize_eigenvector_column_matlab(col: np.ndarray) -> np.ndarray:
    """
    LAPACK/MATLAB-style column normalization: unit 2-norm; largest-magnitude entry real.

    Applies to one eigenvector column (general ``A``, not Entry-specific).
    """
    col = np.asarray(col, dtype=np.complex128).ravel(order="F").copy()
    nrm = float(np.linalg.norm(col))
    if nrm > 0.0:
        col /= nrm
    k = int(np.argmax(np.abs(col)))
    z = col[k]
    if abs(z) < 1e-300:
        return col
    col *= np.exp(-1j * np.angle(z))
    if col[k].real < 0.0:
        col *= -1.0
    return col


def canonicalize_all_eigenvector_columns(v: np.ndarray) -> np.ndarray:
    """Apply :func:`canonicalize_eigenvector_column_matlab` to every column of ``V``."""
    v = np.asarray(v, dtype=np.complex128, order="F").copy()
    n = int(v.shape[1])
    for j in range(n):
        v[:, j] = canonicalize_eigenvector_column_matlab(v[:, j])
    return v


def reorder_eigenpairs_ascending_abs_w(
    w: np.ndarray, v: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Reorder columns so ``|w[0]| <= |w[1]| <= ...`` (MATLAB ``diag(v)`` layout on FSL dumps)."""
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    idx = np.argsort(np.abs(w), kind="mergesort")
    return w[idx].copy(), v[:, idx].copy()


def l2_normalize_principal_column(w: np.ndarray, v: np.ndarray) -> np.ndarray:
    """L2-normalize ``V(:,jmax)`` where ``jmax = argmax |w|``."""
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F").copy()
    j = int(np.argmax(np.abs(w)))
    col = v[:, j]
    nrm = float(np.linalg.norm(col))
    if nrm > 0.0:
        v[:, j] = col / nrm
    return v


def _principal_refine_mode() -> str:
    return str(os.getenv("RGMS_EIG_NOBALANCE_PRINCIPAL_REFINE", "")).strip().lower()


def refine_principal_column_degenerate_span(
    w: np.ndarray, v: np.ndarray, *, rtol: float = 1e-13
) -> np.ndarray:
    """
    Optional reference-free refinement: unit vector in span of near-``|w|`` columns.

    Maximizes the gap between the two largest ``|entry|`` magnitudes (tie-break
    heuristic). Default **off**; does not recover MATLAB ``order`` on FSL corpus (51/58).
    """
    v = np.asarray(v, dtype=np.complex128, order="F").copy()
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    aw = np.abs(w)
    m = float(np.max(aw)) if aw.size else 0.0
    tol = max(1e-300, m * rtol)
    cands = np.flatnonzero(aw >= m - tol)
    jmax = int(np.argmax(aw))
    if cands.size <= 1:
        return v
    col = v[:, jmax].copy()
    best = col / max(float(np.linalg.norm(col)), 1e-300)
    best_gap = -1.0
    for j in cands:
        if j == jmax:
            continue
        partner = v[:, j]
        for alpha in np.linspace(-2.0, 2.0, 401):
            cand = col + alpha * partner
            nrm = float(np.linalg.norm(cand))
            if nrm < 1e-300:
                continue
            cand = cand / nrm
            s = np.sort(np.abs(cand))[::-1]
            gap = float(s[0] - s[1]) if s.size > 1 else float(s[0])
            if gap > best_gap:
                best_gap = gap
                best = cand
    v[:, jmax] = best
    return v


def apply_matlab_spectral_postprocess(
    w: np.ndarray,
    v: np.ndarray,
    *,
    ascending_w: bool = True,
    canonicalize_columns: bool = True,
    l2_principal: bool = True,
    principal_refine: bool | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    General post-``eig`` policy (matrix-agnostic).

    Parameters
    ----------
    ascending_w :
        Reorder by ascending ``|w|`` (FSL dump invariant; disable only for experiments).
    canonicalize_columns :
        LAPACK largest-real-component convention on all columns.
    l2_principal :
        Re-normalize principal column after canonicalization.
    principal_refine :
        Degenerate-span gap heuristic; default from ``RGMS_EIG_NOBALANCE_PRINCIPAL_REFINE``.
    """
    if ascending_w:
        w, v = reorder_eigenpairs_ascending_abs_w(w, v)
    if canonicalize_columns:
        v = canonicalize_all_eigenvector_columns(v)
    if principal_refine is None:
        principal_refine = _principal_refine_mode() in (
            "1",
            "true",
            "yes",
            "on",
            "degenerate_span",
            "span",
        )
    if principal_refine:
        v = refine_principal_column_degenerate_span(w, v)
    if l2_principal:
        v = l2_normalize_principal_column(w, v)
    return w, v
