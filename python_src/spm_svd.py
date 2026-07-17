"""Pass-1 ``spm_svd`` — native NumPy path + optional Engine / callable inject.

OPTIM1FULL Product B plot-orbits (policy B): parity uses MATLAB ``spm_svd`` via
``optim1full_dir_orbits_matlab.make_dir_orbits_matlab_svd`` (or ``svd_fn`` /
``eng`` when ``RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_SVD=1``). Pure NumPy SVD is
**not** the Product B parity path.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Optional

import numpy as np


def _dir_orbits_matlab_svd_env_on() -> bool:
    raw = str(os.getenv("RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_SVD", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def _spm_en_columns(X: np.ndarray) -> np.ndarray:
    """Inline ``spm_en`` column Euclidean normalize (no detrend)."""
    out = np.array(X, dtype=np.float64, copy=True, order="F")
    for i in range(out.shape[1]):
        col = out[:, i]
        if np.any(col):
            nrm = float(np.sqrt(np.sum(col * col)))
            if nrm > 0.0:
                out[:, i] = col / nrm
    return out


def spm_svd_native(X: np.ndarray, U: float = 1e-6) -> np.ndarray:
    """Native approximation of MATLAB ``spm_svd`` single-output ``U`` (Product A)."""
    X0 = np.asarray(X, dtype=np.float64)
    if X0.ndim != 2:
        raise ValueError("spm_svd expects a 2-D matrix")
    thresh = float(U)
    if thresh >= 1.0:
        thresh = thresh - 1e-6
    if thresh <= 0.0:
        thresh = float(64 * np.finfo(float).eps)

    M, N = int(X0.shape[0]), int(X0.shape[1])
    p = np.flatnonzero(np.any(X0, axis=1))
    q = np.flatnonzero(np.any(X0, axis=0))
    if p.size == 0 or q.size == 0:
        return np.zeros((M, 0), dtype=np.float64)
    Xs = X0[np.ix_(p, q)]
    m, n = int(Xs.shape[0]), int(Xs.shape[1])

    # Diagonal-only sparse-like path when off-diagonals are zero.
    i_idx, j_idx = np.nonzero(Xs)
    if i_idx.size and np.all(i_idx == j_idx):
        s = np.diag(Xs).astype(np.float64, copy=True)
        order = np.argsort(-s)
        s = s[order]
        u = np.eye(m, n, dtype=np.float64)[:, order]
        s2 = s * s
        keep = np.flatnonzero(s2 * float(len(s2)) / max(float(np.sum(s2)), 1e-300) > thresh)
        u = u[:, keep]
    else:
        if m > n:
            _, s_arr, vt = np.linalg.svd(Xs.T @ Xs, full_matrices=False)
            # svd of X'*X → singular values are eigenvalues; take sqrt later
            s = np.asarray(s_arr, dtype=np.float64).ravel()
            v = vt.T
            keep = np.flatnonzero(s * float(len(s)) / max(float(np.sum(s)), 1e-300) > thresh)
            v = v[:, keep]
            u = _spm_en_columns(Xs @ v)
        elif m < n:
            u0, s_arr, _ = np.linalg.svd(Xs @ Xs.T, full_matrices=False)
            s = np.asarray(s_arr, dtype=np.float64).ravel()
            keep = np.flatnonzero(s * float(len(s)) / max(float(np.sum(s)), 1e-300) > thresh)
            u = u0[:, keep]
        else:
            u0, s_arr, _ = np.linalg.svd(Xs, full_matrices=False)
            s = np.asarray(s_arr, dtype=np.float64).ravel() ** 2
            keep = np.flatnonzero(s * float(len(s)) / max(float(np.sum(s)), 1e-300) > thresh)
            u = u0[:, keep]

    j = int(u.shape[1]) if u.ndim == 2 else 0
    U_full = np.zeros((M, j), dtype=np.float64)
    if j:
        U_full[p, :] = u
    return U_full


def spm_svd(
    X: Any,
    U: float = 1e-6,
    *,
    svd_fn: Optional[Callable[..., np.ndarray]] = None,
    eng: Any = None,
) -> np.ndarray:
    """
    ``spm_svd`` single-output ``U`` (as used by ``spm_dir_orbits``).

    Precedence: explicit ``svd_fn`` → Engine when env on and ``eng`` given → native.
    """
    X_arr = np.asarray(X, dtype=np.float64)
    if svd_fn is not None:
        return np.asarray(svd_fn(X_arr, float(U)), dtype=np.float64)
    if eng is not None and _dir_orbits_matlab_svd_env_on():
        from tests.demo1.optim1full.optim1full_dir_orbits_matlab import (
            make_dir_orbits_matlab_svd,
        )

        return np.asarray(make_dir_orbits_matlab_svd(eng)(X_arr, float(U)), dtype=np.float64)
    return spm_svd_native(X_arr, float(U))
