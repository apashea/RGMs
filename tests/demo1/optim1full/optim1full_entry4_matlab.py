"""OPTIM1FULL Product B — Entry **4** structure-learning MATLAB fences (MI + eig).

Entry **4** structure learning has the same narrow MATLAB-reuse contract as the original
FSL Product B oracle: MATLAB supplies the numerically non-reproducible ``MI`` and
``eig(...,'nobalance')`` pieces, while our own translated
``spm_faster_structure_learning_optim`` / ``spm_rgm_group`` still owns the Python control
flow, grouping selection, and ``a``/``b``/``G`` assembly. ``spm_dir_MI`` is also reused
for linked stream matrices when exact ``ss.ID`` / ``ss.IE`` parity is required.

This is a **means**, not the shipped library: the native Product A path uses native
``MI`` / eig / link MI and does not wire these hooks.

OPTIM1FULL-only env (default **on** for parity):
``RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG=1``,
``RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI=1``,
``RGMS_OPTIM1FULL_ENTRY4_LINK_DIR_MI=1``.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Tuple

import numpy as np


def optim1full_entry4_matlab_eig_enabled() -> bool:
    """``RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG`` — default **on** for Product B parity."""
    raw = str(os.getenv("RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def optim1full_entry4_matlab_mi_enabled() -> bool:
    """``RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI`` — default **on** for Product B parity."""
    raw = str(os.getenv("RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def optim1full_entry4_link_dir_mi_enabled() -> bool:
    """``RGMS_OPTIM1FULL_ENTRY4_LINK_DIR_MI`` — default **on** for exact SS parity."""
    raw = str(os.getenv("RGMS_OPTIM1FULL_ENTRY4_LINK_DIR_MI", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def make_optim1full_rgm_eig_pair(
    eng: Any,
) -> Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]:
    """Build an ``eig_pair`` for :func:`spm_rgm_group` using MATLAB ``eig(...,'nobalance')``.

    Mirrors ``[e,v] = eig(MI(i,i),'nobalance')`` in ``spm_rgm_group.m`` so Python's
    spectral partition matches MATLAB's when SciPy/OpenBLAS eigenvectors differ at
    ULP-level ties. Only the eigendecomposition is delegated; ``spm_rgm_group`` still
    performs ``max(diag(v))`` / ``sort(abs(e(:,j)),'descend')`` selection in Python.

    The returned callable matches the ``eig_pair`` contract expected by
    ``spm_rgm_group``: ``sub -> (vals, vecs)`` with ``vals`` length ``n`` (one
    eigenvalue per column) and ``vecs`` shape ``(n, n)`` (eigenvectors as columns),
    both ``complex128`` in column-major (MATLAB) order.
    """
    import matlab

    call_i = {"n": 0}

    def _eig_pair(sub: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        sub = np.asarray(sub, dtype=np.float64)
        n = int(sub.shape[0])
        if sub.shape != (n, n):
            raise ValueError("optim1full rgm eig_pair expects a square MI block")
        call_i["n"] = call_i["n"] + 1
        tag = f"{call_i['n']}_{id(sub) & 0xFFFFFF:x}"
        mname = f"rgms_o1f_MI_{tag}"
        ename = f"rgms_o1f_e_{tag}"
        vname = f"rgms_o1f_v_{tag}"
        eng.workspace[mname] = matlab.double(sub.tolist())
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

    return _eig_pair


def _matlab_mi_from_o_cell_var(eng: Any, cell_name: str, m: int) -> np.ndarray:
    """MATLAB ``MI`` for a cell ``O`` already in the Engine.

    Mirrors the ``spm_rgm_group.m`` MI construction exactly: Kronecker reduction,
    ``spm_cat``, activity flags, and symmetric ``spm_MDP_MI`` accumulation. This is the
    established FSL oracle bridge, moved into the OPTIM1FULL parity helper so the
    integrated Product B lane does not depend on test-private helpers.
    """
    eng.eval(
        f"rgms_Os_loc = {cell_name}; "
        "[rgms_No0,rgms_ntB] = size(rgms_Os_loc); "
        f"rgms_mB = {int(m)}; "
        "rgms_Rb = {}; "
        "for rgms_tb = 1:rgms_ntB, "
        "  rgms_ii = 1; "
        "  for rgms_oo = 1:rgms_mB:rgms_No0, "
        "    p = rgms_Os_loc{rgms_oo,rgms_tb}; "
        "    for rgms_rr = 1:(rgms_mB - 1), "
        "      p = kron(p, rgms_Os_loc{rgms_oo + rgms_rr,rgms_tb}); "
        "    end; "
        "    rgms_Rb{rgms_ii,rgms_tb} = p; "
        "    rgms_ii = rgms_ii + 1; "
        "  end; "
        "end; "
        "rgms_No1 = size(rgms_Rb,1); "
        "rgms_nb = false(1,rgms_No1); "
        "rgms_rb = cell(1,rgms_No1); "
        "for rgms_ox = 1:rgms_No1, "
        "  rgms_rb{rgms_ox} = spm_cat(rgms_Rb(rgms_ox,:)); "
        "  rgms_nb(rgms_ox) = any(diff(rgms_rb{rgms_ox},[],2),'all'); "
        "end; "
        "rgms_MI_out = zeros(rgms_No1,rgms_No1); "
        "for rgms_ix = 1:rgms_No1, "
        "  for rgms_jx = rgms_ix:rgms_No1, "
        "    if rgms_nb(rgms_ix) && rgms_nb(rgms_jx), "
        "      rgms_pb = rgms_rb{rgms_ix}*rgms_rb{rgms_jx}'; "
        "      rgms_MI_out(rgms_ix,rgms_jx) = spm_MDP_MI(rgms_pb); "
        "      rgms_MI_out(rgms_jx,rgms_ix) = rgms_MI_out(rgms_ix,rgms_jx); "
        "    end; "
        "  end; "
        "end;",
        nargout=0,
    )
    return np.asarray(eng.eval("rgms_MI_out"), dtype=np.float64)


def make_optim1full_rgm_mi_override_fn(
    eng: Any,
) -> Callable[[list[Any], int], np.ndarray]:
    """Build the ``rgm_mi_override_fn`` bridge for ``spm_rgm_group``.

    Each Python ``o_sub`` slice is pushed to MATLAB and reduced by the exact MATLAB
    ``spm_rgm_group`` MI construction. This is intentionally slow and intentionally
    parity-only; it prevents ULP-level MI differences from flipping discrete grouping.
    """
    import matlab

    seq = {"i": 0}

    def _mi_fn(o_sub: list[Any], m: int) -> np.ndarray:
        seq["i"] += 1
        cname = f"rgms_o1f_Ob{seq['i']}"
        no = len(o_sub)
        nt = len(o_sub[0]) if no else 0
        for o in range(no):
            for t in range(nt):
                arr = np.asarray(o_sub[o][t], dtype=np.float64)
                ns = int(arr.shape[0])
                eng.workspace["rgms_o1f_O_tmp"] = matlab.double(arr.tolist(), size=(ns, 1))
                eng.eval(f"{cname}{{{o+1},{t+1}}} = rgms_o1f_O_tmp;", nargout=0)
        mi = _matlab_mi_from_o_cell_var(eng, cname, int(m))
        eng.eval(f"clear {cname} rgms_o1f_O_tmp", nargout=0)
        return mi

    return _mi_fn


def make_optim1full_link_dir_mi_fn(eng: Any) -> Callable[[np.ndarray], float]:
    """Build a MATLAB ``spm_dir_MI(a)`` bridge for linked stream matrices."""
    import matlab

    seq = {"i": 0}

    def _link_mi(a_mat: np.ndarray) -> float:
        seq["i"] += 1
        tag = seq["i"]
        mname = f"rgms_o1f_am_link_{tag}"
        outname = f"rgms_o1f_E_link_{tag}"
        a_mat = np.asarray(a_mat, dtype=np.float64)
        nr, nc = int(a_mat.shape[0]), int(a_mat.shape[1])
        eng.workspace[mname] = matlab.double(a_mat.tolist(), size=(nr, nc))
        eng.eval(f"{outname} = spm_dir_MI({mname});", nargout=0)
        val = float(np.asarray(eng.eval(outname), dtype=np.float64).reshape(-1)[0])
        eng.eval(f"clear {mname} {outname}", nargout=0)
        return val

    return _link_mi


def validation_entry4_metadata() -> dict[str, Any]:
    """Provenance for Entry 4 MATLAB fences (recorded beside Entry 10 metadata)."""
    return {
        "entry4_eig_source": "matlab_engine"
        if optim1full_entry4_matlab_eig_enabled()
        else "native",
        "entry4_mi_source": "matlab_engine"
        if optim1full_entry4_matlab_mi_enabled()
        else "native",
        "entry4_link_dir_mi_source": "matlab_engine"
        if optim1full_entry4_link_dir_mi_enabled()
        else "native",
        "RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG": optim1full_entry4_matlab_eig_enabled(),
        "RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI": optim1full_entry4_matlab_mi_enabled(),
        "RGMS_OPTIM1FULL_ENTRY4_LINK_DIR_MI": optim1full_entry4_link_dir_mi_enabled(),
    }
