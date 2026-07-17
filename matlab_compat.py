import os
from typing import Callable

import numpy as np
from scipy import sparse
from scipy.linalg import lapack


def as_matlab_array(x):
    x = full(x)
    x = np.asarray(x)
    if x.ndim == 1:
        x = x.reshape((1, x.shape[0]))
    return x


def full(x):
    if sparse.issparse(x):
        return x.toarray()
    return x


def matlab_scalar(x):
    if sparse.issparse(x):
        if x.shape == (1, 1):
            return x.toarray().reshape(-1, order="F")[0]
        return x
    x = np.asarray(x)
    if x.ndim == 0 or x.shape == (1, 1):
        return x.reshape(-1, order="F")[0]
    return x


def trim_trailing_singletons(x):
    siz = _trim_size(np.shape(x))
    if siz != np.shape(x):
        x = np.reshape(x, siz, order="F")
    return x


def matlab_size(x):
    if sparse.issparse(x):
        siz = x.shape
    else:
        x = np.asarray(x)
        if x.ndim == 0:
            siz = (1, 1)
        elif x.ndim == 1:
            if x.size == 0:
                siz = (0, 0)
            else:
                siz = (1, x.shape[0])
        else:
            siz = x.shape
    return _trim_size(siz)


def matlab_ndims(x):
    return len(matlab_size(x))


def _trim_size(siz):
    siz = tuple(siz)
    while len(siz) > 2 and siz[-1] == 1:
        siz = siz[:-1]
    if len(siz) == 0:
        return (1, 1)
    if len(siz) == 1:
        return siz + (1,)
    return siz


# ---------------------------------------------------------------------------
# MATLAB ``eig(A,'nobalance')`` — LAPACK *GEEVX* (``balanc='N'``) when SciPy exposes it.
# LAPACK *GEEV* (``dgeev``) applies internal balancing (``DGEBAL``) — not a nobalance substitute.
# ---------------------------------------------------------------------------

def geevx_available() -> bool:
    """True when SciPy links LAPACK ``*geevx`` (required for ``balanc='N'``)."""
    try:
        lapack.get_lapack_funcs("geevx", (np.zeros((2, 2), dtype=np.float64),))
        return True
    except ValueError:
        return False


def _env_eig_backend() -> str:
    """``RGMS_SPM_RDP_SORT_EIG_BACKEND``: ``auto`` | ``lapack_geevx`` | ``lapack_dgeev`` | ``numpy``."""
    return str(os.getenv("RGMS_SPM_RDP_SORT_EIG_BACKEND", "auto")).strip().lower()


def _env_principal_rule() -> str:
    """``RGMS_SPM_RDP_SORT_PRINCIPAL``: ``argmax`` | ``min_tie`` | ``closest_unity``."""
    return str(os.getenv("RGMS_SPM_RDP_SORT_PRINCIPAL", "min_tie")).strip().lower()


def principal_eig_column_index(w: np.ndarray) -> int:
    """
    Column index for ``[~,j]=max(real(diag(v)))`` / ``abs(e(:,j))`` in ``spm_RDP_sort``.

    ``min_tie`` (default): smallest index among eigenvalues tied at ``max(real(w))``
    (MATLAB ``max`` on the diagonal is first-occurring maximum).
    ``closest_unity``: smallest index with ``real(w)`` closest to 1 (NESS unit eigenvalue).
    ``argmax``: ``numpy.argmax(real(w))`` (legacy Pass-1).
    """
    wr = np.real(np.asarray(w, dtype=np.complex128).ravel(order="F"))
    rule = _env_principal_rule()
    if rule in ("column0", "matlab_jj1", "jj1"):
        return 0
    if rule in ("argmax", "legacy"):
        return int(np.argmax(wr))
    if rule in ("min_tie", "first_max", "matlab_max"):
        mx = float(np.max(wr))
        tol = max(1e-12, 1e-15 * max(abs(mx), 1.0))
        cands = np.flatnonzero(wr >= mx - tol)
        return int(cands[0])
    if rule in ("closest_unity", "unity", "unit"):
        dev = np.abs(wr - 1.0)
        m = float(np.min(dev))
        tol = max(1e-12, 1e-15 * max(abs(1.0), m))
        cands = np.flatnonzero(dev <= m + tol)
        return int(cands[0])
    raise ValueError(f"unknown RGMS_SPM_RDP_SORT_PRINCIPAL={rule!r}")


def _real_geev_evecs_to_complex(vr: np.ndarray, wi: np.ndarray) -> np.ndarray:
    """LAPACK real ``geev``/``geevx`` right eigenvectors → complex columns (MATLAB layout)."""
    vr = np.asarray(vr, dtype=np.float64)
    wi = np.asarray(wi, dtype=np.float64).ravel(order="F")
    n = int(vr.shape[0])
    vc = np.zeros((n, n), dtype=np.complex128, order="F")
    k = 0
    while k < n:
        if abs(float(wi[k])) < 1e-300:
            vc[:, k] = vr[:, k]
            k += 1
        else:
            vc[:, k] = vr[:, k] + 1j * vr[:, k + 1]
            vc[:, k + 1] = vr[:, k] - 1j * vr[:, k + 1]
            k += 2
    return vc


def _eig_lapack_dgeev_real(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """LAPACK ``*geev`` (balanced ``DGEBAL`` path) — experimental only, not MATLAB ``nobalance``."""
    a_f = np.asarray(a, dtype=np.float64, order="F")
    wr, wi, _vl, vr, info = lapack.dgeev(a_f, compute_vl=0, compute_vr=1)
    if int(info) != 0:
        raise RuntimeError(f"LAPACK dgeev failed with info={int(info)}")
    w = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    V = _real_geev_evecs_to_complex(np.asarray(vr, dtype=np.float64), wi)
    return w, V


def _eig_lapack_geevx_real(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """LAPACK ``*geevx`` with ``balanc='N'`` (MATLAB ``nobalance`` semantics when available)."""
    a_f = np.asarray(a, dtype=np.float64, order="F")
    try:
        geevx = lapack.get_lapack_funcs("geevx", (a_f,))
    except ValueError as exc:
        raise RuntimeError("LAPACK geevx not available in this SciPy build") from exc
    out = geevx(a_f, balanc="N", jobvl="N", jobvr="V", sense="N")
    # Real ``dgeevx``: (wr, wi, vl, vr, ilo, ihi, scale, abnrm, rconde, rcondv, info)
    wr, wi, _vl, vr = out[0], out[1], out[2], out[3]
    info = int(out[-1])
    if info != 0:
        raise RuntimeError(f"LAPACK geevx failed with info={info}")
    w = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    V = _real_geev_evecs_to_complex(np.asarray(vr, dtype=np.float64), wi)
    return w, V


def eig_matlab_nobalance(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Dense eigenpairs in ``numpy.linalg.eig`` layout: 1-D ``w``, columns of ``V``.

    Uses LAPACK ``geevx(..., balanc='N')`` when linked (MATLAB ``eig(...,'nobalance')``).
    When ``geevx`` is missing, falls back to ``numpy.linalg.eig`` (Pass-1 legacy) — **not**
    ``dgeev``, which is a balanced driver and empirically worsens FSL NESS prune parity.
    """
    a_arr = np.asarray(a, dtype=np.float64)
    if a_arr.ndim != 2 or a_arr.shape[0] != a_arr.shape[1]:
        raise ValueError("eig_matlab_nobalance expects a square 2-D matrix")
    if np.iscomplexobj(a_arr):
        raise NotImplementedError("eig_matlab_nobalance: complex matrices not implemented yet")
    try:
        return _eig_lapack_geevx_real(a_arr)
    except RuntimeError:
        # Pass-1 fallback (pre-2026-06 ``auto`` wrongly used balanced ``dgeev`` here):
        # return _eig_lapack_dgeev_real(a_arr)
        return np.linalg.eig(a_arr)


def resolve_spm_RDP_sort_eig() -> Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]:
    """
    Select eigen backend for ``spm_RDP_sort`` when ``eig=`` is not passed.

    Env ``RGMS_SPM_RDP_SORT_EIG_BACKEND``:
    - ``auto`` (default): ``eig_matlab_nobalance`` (geevx if linked, else ``numpy.linalg.eig``)
    - ``lapack_geevx``: geevx only (raises if missing)
    - ``lapack_dgeev``: balanced LAPACK ``dgeev`` (diagnostic / not nobalance)
    - ``numpy``: legacy Pass-1 ``numpy.linalg.eig``
    """
    backend = _env_eig_backend()
    if backend in ("numpy", "numpy_linalg", "legacy"):
        return np.linalg.eig
    if backend in ("lapack_dgeev", "dgeev"):
        return _eig_lapack_dgeev_real
    if backend in ("lapack_geevx", "geevx"):
        return _eig_lapack_geevx_real
    if backend in ("auto", ""):
        return eig_matlab_nobalance
    raise ValueError(f"unknown RGMS_SPM_RDP_SORT_EIG_BACKEND={backend!r}")
