"""OPTIM1FULL Product B — plot-orbits spectral injects for ``spm_dir_orbits``.

Policy B (2026-07-16): Pass-1 Python owns glue; Engine-inject **only**
``eig(...,'nobalance')`` and ``spm_svd`` — same Product B class as Entry **10**
``eig`` / Entry **4** MI+eig / ``spm_RDP_sort``. Not wholesale MATLAB
``spm_dir_orbits``; not pure NumPy SVD as the parity path.

Envs (default **on** for Product B parity):
- ``RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_EIG=1``
- ``RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_SVD=1``
"""
from __future__ import annotations

import os
from typing import Any, Callable

import numpy as np


def optim1full_dir_orbits_matlab_eig_enabled() -> bool:
    raw = str(os.getenv("RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_EIG", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def optim1full_dir_orbits_matlab_svd_enabled() -> bool:
    raw = str(os.getenv("RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_SVD", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def make_dir_orbits_matlab_eig(
    eng: Any,
) -> Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]:
    """``(B,) -> (vals, vecs)`` via MATLAB ``eig(B,'nobalance')``.

    Contract matches Entry **10** / ``matlab_eig_callable``: eigenvalue vector
    ``vals`` length ``n``, eigenvector matrix ``vecs`` shape ``(n, n)``.
    """
    import matlab

    call_i = {"n": 0}

    def _eig(B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        B = np.asarray(B, dtype=np.float64)
        n = int(B.shape[0])
        if B.shape != (n, n):
            raise ValueError("dir_orbits eig expects a square matrix")
        call_i["n"] = call_i["n"] + 1
        tag = f"{call_i['n']}_{id(B) & 0xFFFFFF:x}"
        mname = f"rgms_o1f_orb_B_{tag}"
        ename = f"rgms_o1f_orb_e_{tag}"
        vname = f"rgms_o1f_orb_v_{tag}"
        eng.workspace[mname] = matlab.double(B.tolist())
        eng.eval(f"[{ename},{vname}] = eig({mname},'nobalance');", nargout=0)
        lam = eng.eval(f"diag({vname})")
        vals = np.asarray(lam, dtype=np.complex128).reshape(-1, order="F").ravel()
        evecs = np.asarray(eng.eval(ename), dtype=np.complex128)
        if evecs.size != n * n:
            raise RuntimeError(
                f"MATLAB eig returned size {evecs.size}, expected {n * n} for n={n}"
            )
        if evecs.shape != (n, n):
            evecs = np.reshape(evecs, (n, n), order="F")
        eng.eval(f"clear {mname} {ename} {vname}", nargout=0)
        return vals, evecs

    return _eig


def make_dir_orbits_matlab_ness_order(
    eng: Any,
) -> Callable[[np.ndarray, int], np.ndarray]:
    """``(B, N) -> j0`` — MATLAB NESS ``max`` + ``sort(p,'descend')`` subset indices.

    Same eig stream as ``make_dir_orbits_matlab_eig``; closes ULP tie-order drift on
    ``p`` that reorders ``j`` vs MATLAB ``spm_dir_orbits`` (still not wholesale orbits).
    Returns **0-based** indices length ``min(N, Ns)``.
    """
    import matlab

    call_i = {"n": 0}

    def _order(B: np.ndarray, N: int) -> np.ndarray:
        B = np.asarray(B, dtype=np.float64)
        n = int(B.shape[0])
        if B.shape != (n, n):
            raise ValueError("dir_orbits ness_order expects a square matrix")
        call_i["n"] = call_i["n"] + 1
        tag = f"{call_i['n']}_{id(B) & 0xFFFFFF:x}"
        mname = f"rgms_o1f_orb_Bn_{tag}"
        jname = f"rgms_o1f_orb_j_{tag}"
        eng.workspace[mname] = matlab.double(B.tolist())
        eng.workspace["rgms_o1f_orb_N"] = float(int(N))
        eng.eval(
            f"[e,v]=eig({mname},'nobalance'); v=diag(v); "
            f"[~,i]=max(real(v)); p=spm_dir_norm(abs(e(:,i))); "
            f"[~,j]=sort(p,'descend'); "
            f"{jname}=j(1:min(end-0,rgms_o1f_orb_N));",
            nargout=0,
        )
        j1 = np.asarray(eng.eval(jname), dtype=np.int64).reshape(-1, order="F").ravel()
        eng.eval(f"clear {mname} {jname} e v i p j rgms_o1f_orb_N", nargout=0)
        return j1 - 1

    return _order


def make_dir_orbits_matlab_svd(
    eng: Any,
) -> Callable[[np.ndarray, float | None], np.ndarray]:
    """``(X, thresh=None) -> U`` via MATLAB ``spm_svd`` (single-output orbits use)."""
    import matlab

    call_i = {"n": 0}

    def _svd(X: np.ndarray, thresh: float | None = None) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2:
            raise ValueError("dir_orbits svd expects a 2-D matrix")
        call_i["n"] = call_i["n"] + 1
        tag = f"{call_i['n']}_{id(X) & 0xFFFFFF:x}"
        mname = f"rgms_o1f_orb_X_{tag}"
        uname = f"rgms_o1f_orb_U_{tag}"
        nr, nc = int(X.shape[0]), int(X.shape[1])
        eng.workspace[mname] = matlab.double(X.tolist(), size=(nr, nc))
        if thresh is None:
            eng.eval(f"{uname} = full(spm_svd({mname}));", nargout=0)
        else:
            eng.workspace["rgms_o1f_orb_u"] = float(thresh)
            eng.eval(f"{uname} = full(spm_svd({mname}, rgms_o1f_orb_u));", nargout=0)
        u_raw = eng.eval(uname)
        u = np.asarray(u_raw, dtype=np.float64)
        if u.ndim == 1:
            u = u.reshape(-1, 1, order="F")
        elif u.ndim == 2 and u.shape[0] != nr:
            u = np.reshape(u, (nr, -1), order="F")
        eng.eval(f"clear {mname} {uname} rgms_o1f_orb_u", nargout=0)
        return u

    return _svd


def bind_dir_orbits_matlab_injects(eng: Any) -> dict[str, Any]:
    """Return ``eig`` / ``svd`` / ``ness_order`` callables honoring Product B env flags."""
    out: dict[str, Any] = {"eig": None, "svd": None, "ness_order": None}
    if optim1full_dir_orbits_matlab_eig_enabled():
        out["eig"] = make_dir_orbits_matlab_eig(eng)
        # NESS max+sort rides with eig inject (ULP tie order on p).
        out["ness_order"] = make_dir_orbits_matlab_ness_order(eng)
    if optim1full_dir_orbits_matlab_svd_enabled():
        out["svd"] = make_dir_orbits_matlab_svd(eng)
    return out


def validation_dir_orbits_metadata() -> dict[str, Any]:
    return {
        "dir_orbits_eig_source": (
            "matlab_engine" if optim1full_dir_orbits_matlab_eig_enabled() else "native"
        ),
        "dir_orbits_svd_source": (
            "matlab_engine" if optim1full_dir_orbits_matlab_svd_enabled() else "native"
        ),
        "RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_EIG": optim1full_dir_orbits_matlab_eig_enabled(),
        "RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_SVD": optim1full_dir_orbits_matlab_svd_enabled(),
    }
