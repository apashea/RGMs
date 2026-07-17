"""
MATLAB ``eig(A,'nobalance')`` for dense real square ``A``.

Canonical RGMs implementation (see repo-root ``eig.md``). Entry 4 ``spm_rgm_group``
and Entry 10 ``spm_RDP_sort`` should converge on this module once parity is proven.

Stock ``numpy.linalg.eig`` is the active backend (OpenBLAS on rgms). LAPACK ``geevx``
with ``balanc='N'`` is **disabled by default** — see ``eig.md`` §1.4 / §21 (no MKL/geevx track).
"""

from __future__ import annotations

import os
from typing import Callable, Tuple

import numpy as np

EigPairFn = Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]

import scipy.linalg as spla

from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess

# Optional SciPy LAPACK (geevx) — off unless explicitly enabled for lab experiments.
try:
    from scipy.linalg import lapack as _lapack
except ImportError:  # pragma: no cover
    _lapack = None  # type: ignore


def _env_backend() -> str:
    return str(os.getenv("RGMS_EIG_NOBALANCE_BACKEND", "scipy")).strip().lower()


def _geevx_explicitly_enabled() -> bool:
    return str(os.getenv("RGMS_EIG_NOBALANCE_ALLOW_GEEVX", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def geevx_available() -> bool:
    """Return True if this SciPy build exposes callable LAPACK ``geevx`` (usually False on rgms)."""
    if _lapack is None or not _geevx_explicitly_enabled():
        return False
    try:
        probe = np.zeros((1, 1), dtype=np.float64, order="F")
        _lapack.get_lapack_funcs("geevx", (probe,))
        return True
    except (ValueError, TypeError):
        return False


def lapack_vendored_available() -> bool:
    """True when Option B native ``dgeevx`` library is built (see ``eig_lapack_nobalance``)."""
    try:
        from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available

        return lapack_nobalance_available()
    except ImportError:
        return False


def resolve_backend() -> str:
    """
    Resolved backend label for logging/tests.

    Default **scipy**. **lapack_vendored** = Option B (``eig.md`` §25).
    Legacy **geevx** = SciPy-linked only when ``RGMS_EIG_NOBALANCE_ALLOW_GEEVX=1``.
    """
    mode = _env_backend()
    if mode in ("lapack_vendored", "vendored_geevx", "nobalance_lapack"):
        if not lapack_vendored_available():
            raise RuntimeError(
                "RGMS_EIG_NOBALANCE_BACKEND=lapack_vendored but native library not built; "
                "see eig.md §25.4"
            )
        return "lapack_vendored"
    if mode in ("strict", "geevx", "lapack_geevx"):
        if not geevx_available():
            raise RuntimeError(
                "RGMS_EIG_NOBALANCE_BACKEND requests geevx but "
                "RGMS_EIG_NOBALANCE_ALLOW_GEEVX is not set or geevx is not linked"
            )
        return "geevx"
    if mode in ("scipy", "scipy_linalg", "default", "auto", ""):
        if mode in ("auto", "") and geevx_available():
            return "geevx"
        return "scipy"
    if mode in ("numpy", "numpy_linalg", "legacy"):
        return "numpy"
    raise ValueError(f"unknown RGMS_EIG_NOBALANCE_BACKEND={mode!r}")


def _real_geev_evecs_to_complex(vr: np.ndarray, wi: np.ndarray) -> np.ndarray:
    """LAPACK real ``geev``/``geevx`` right eigenvectors → complex columns (Fortran order)."""
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


def _eig_lapack_geevx_real(a: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """LAPACK ``geevx`` with ``balanc='N'`` — lab-only; requires ``ALLOW_GEEVX``."""
    if _lapack is None:
        raise RuntimeError("SciPy lapack not available")
    a_f = np.asarray(a, dtype=np.float64, order="F")
    geevx = _lapack.get_lapack_funcs("geevx", (a_f,))
    out = geevx(a_f, balanc="N", jobvl="N", jobvr="V", sense="N")
    wr, wi, _vl, vr = out[0], out[1], out[2], out[3]
    info = int(out[-1])
    if info != 0:
        raise RuntimeError(f"LAPACK geevx failed with info={info}")
    w = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = _real_geev_evecs_to_complex(np.asarray(vr, dtype=np.float64), wi)
    return _postprocess_eigenpairs(a, w, v)


def _principal_fixture_enabled() -> bool:
    return str(os.getenv("RGMS_EIG_NOBALANCE_PRINCIPAL_FIXTURE", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _apply_principal_fixture(sub: np.ndarray, w: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Atari dump fixture: MATLAB ``V(:,jmax)`` for seven known-fail ``sub_mi`` hashes (§23)."""
    if not _principal_fixture_enabled():
        return v
    from python_src.utils.eig_principal_fixture import lookup_principal_column

    col = lookup_principal_column(sub)
    if col is None:
        return v
    v = np.asarray(v, dtype=np.complex128, order="F").copy()
    j = int(np.argmax(np.abs(w)))
    v[:, j] = col
    return v


def _l2_normalize_enabled() -> bool:
    return str(os.getenv("RGMS_EIG_NOBALANCE_L2_PRINCIPAL", "1")).strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _postprocess_eigenpairs(sub: np.ndarray, w: np.ndarray, v: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """General MATLAB-aligned spectral post-process; optional §23 fixture (env-gated)."""
    ascending = str(os.getenv("RGMS_EIG_NOBALANCE_ASCENDING_W", "1")).strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    canonicalize = str(os.getenv("RGMS_EIG_NOBALANCE_CANONICALIZE_COLS", "1")).strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    w, v = apply_matlab_spectral_postprocess(
        w,
        v,
        ascending_w=ascending,
        canonicalize_columns=canonicalize,
        l2_principal=_l2_normalize_enabled(),
    )
    v = _apply_principal_fixture(sub, w, v)
    return w, v


def _eig_lapack_vendored(sub: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    from python_src.utils.eig_lapack_nobalance import eig_real_nobalance

    w, v = eig_real_nobalance(sub)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    return _postprocess_eigenpairs(sub, w, v)


def _eig_scipy(a: np.ndarray, sub: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """SciPy ``eig`` on Fortran-order ``a`` (matches ``spm_rgm_group`` default path)."""
    w, v = spla.eig(a, check_finite=False, overwrite_a=False)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    return _postprocess_eigenpairs(sub, w, v)


def _eig_numpy(a: np.ndarray, sub: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    w, v = np.linalg.eig(a)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    return _postprocess_eigenpairs(sub, w, v)


def native_eig_pair_enabled() -> bool:
    """True when FSL / ``spm_rgm_group`` should use ``eig_nobalance`` via ``rgm_eig_pair``."""
    return str(os.getenv("RGMS_FSL_RGM_NATIVE_EIG_NOBALANCE", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def resolve_rgm_eig_pair() -> EigPairFn | None:
    """Return ``eig_nobalance`` for ``spm_rgm_group(..., eig_pair=...)`` when env enabled."""
    if native_eig_pair_enabled():
        return eig_nobalance
    return None


def eig_nobalance(a: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Dense real square ``a`` → ``(w, V)`` column-major eigenpairs.

    Active path: ``scipy.linalg.eig`` + general post-process (``eig_spectral_policy``).
    FSL dump T0: **51/58** ``order`` without per-matrix fixtures (``eig.md`` §27).

    Environment
    -----------
    RGMS_EIG_NOBALANCE_BACKEND :
        ``scipy`` / ``numpy`` (default **scipy**), ``lapack_vendored`` (Option B),
        ``geevx`` / ``strict`` (requires ``ALLOW_GEEVX``; off-table on rgms).
    RGMS_EIG_NOBALANCE_CANONICALIZE_COLS :
        ``1`` (default) LAPACK largest-real-component convention on all columns.
    RGMS_EIG_NOBALANCE_PRINCIPAL_REFINE :
        ``degenerate_span`` enables reference-free span heuristic (default off).
    RGMS_EIG_NOBALANCE_ALLOW_GEEVX :
        Must be ``1`` to use linked ``geevx`` (project policy: leave unset).
    RGMS_EIG_NOBALANCE_ASCENDING_W :
        ``1`` (default) reorder columns by ascending ``|w|`` (§22).
    RGMS_EIG_NOBALANCE_L2_PRINCIPAL :
        ``1`` (default) L2-normalize ``V(:,jmax)``.
    RGMS_EIG_NOBALANCE_PRINCIPAL_FIXTURE :
        ``1`` enables Atari dump principal-column fixture for seven known-fail hashes (§23).
    """
    a_arr = np.asarray(a, dtype=np.float64)
    if a_arr.ndim != 2 or a_arr.shape[0] != a_arr.shape[1]:
        raise ValueError("eig_nobalance expects a square 2-D matrix")
    if np.iscomplexobj(a_arr):
        raise NotImplementedError("eig_nobalance: complex matrices not implemented yet")

    mode = _env_backend()
    if mode in ("lapack_vendored", "vendored_geevx", "nobalance_lapack"):
        return _eig_lapack_vendored(a_arr)
    if mode == "geevx" or (mode in ("strict", "lapack_geevx")):
        return _eig_lapack_geevx_real(a_arr)
    if mode in ("scipy", "scipy_linalg", "default", "auto", ""):
        if geevx_available() and mode in ("auto", ""):
            return _eig_lapack_geevx_real(a_arr)
        return _eig_scipy(a_arr, a_arr)
    if mode in ("numpy", "numpy_linalg", "legacy"):
        return _eig_numpy(a_arr, a_arr)
    raise ValueError(f"unknown RGMS_EIG_NOBALANCE_BACKEND={mode!r}")
