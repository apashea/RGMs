"""
Compression of a (Dirichlet) probability tensor — spectral grouping of outcomes.

Translated from spm_rgm_group.m (Pass 1). Uses `spm_cat`, `spm_MDP_MI`, and
`numpy.kron` in the same order as MATLAB `kron` inside the multimodal loop.
"""

from __future__ import annotations

import os
from typing import Any, Callable, List, Optional, Sequence, Tuple

import numpy as np
import scipy.linalg as spla
from scipy.linalg import lapack

from python_src.spm_cat import spm_cat
from python_src.spm_MDP_MI import spm_MDP_MI


def _sort_abs_descend_matlab_like(absv: np.ndarray) -> np.ndarray:
    """MATLAB ``sort(abs(e(:,jmax)),'descend')`` — ``eig_spectral_policy`` (optional tie-band §4.1 B5.3)."""
    from python_src.utils.eig_spectral_policy import sort_abs_descend_for_spm_rgm

    return sort_abs_descend_for_spm_rgm(absv)


def _spm_mdp_mi_scalar(p: np.ndarray) -> float:
    """Single-output `spm_MDP_MI(p)` (mutual information term only)."""
    out = spm_MDP_MI(np.asarray(p, dtype=np.float64))
    if isinstance(out, tuple):
        v = out[0]
    else:
        v = out
    return float(np.real(np.asarray(v, dtype=float)).reshape(-1)[0])


def _spm_cat_row(cells: Sequence[Any]) -> np.ndarray:
    """Horizontal concatenation of one row of cells (MATLAB `spm_cat(R(o,:))`)."""
    nt = len(cells)
    time_mode = _env_text("RGMS_RGM_EXPERIMENT_R_TIME_ORDER")
    if time_mode in ("rev", "reverse", "backward"):
        t_seq = range(nt - 1, -1, -1)
    elif time_mode in ("", "fwd", "forward", "default", "none", "off", "0", "false", "no"):
        t_seq = range(nt)
    else:
        raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_R_TIME_ORDER mode: {time_mode!r}")
    row = [[cells[t] for t in t_seq]]
    cat = spm_cat(row)
    if hasattr(cat, "toarray"):
        cat = cat.toarray()
    return np.asarray(cat, dtype=np.float64)


def _kron_modal_chain(vecs: Sequence[np.ndarray]) -> np.ndarray:
    """Kronecker stack for one composite outcome (MATLAB ``p = O{o,t}; for r=1:m-1 ...``).

    Default matches ``spm_rgm_group.m``. Optional chains are diagnostics-only for
    ``m>1``; when ``m==1`` all modes reduce to the single modality vector.
    """
    mode = _env_text("RGMS_RGM_EXPERIMENT_R_KRON_CHAIN")
    vlist = [np.asarray(v, dtype=np.float64) for v in vecs]
    m = len(vlist)
    if m == 0:
        raise ValueError("spm_rgm_group: empty modality list for Kronecker chain")
    if mode in ("", "matlab", "default", "fwd", "none", "off", "0", "false", "no"):
        p = vlist[0]
        for r in range(1, m):
            p = np.kron(p, vlist[r])
        return p
    if mode in ("rev_assoc", "right_deep_rev"):
        # kron(v_{m-1}, kron(v_{m-2}, ... kron(v_1, v_0)...)) — not MATLAB-default.
        p = vlist[m - 1]
        for r in range(m - 2, -1, -1):
            p = np.kron(p, vlist[r])
        return p
    if mode in ("left_deep_swap", "swap", "left_deep"):
        # kron(v_{m-1}, kron(v_{m-2}, ... kron(v_1, v_0))) — not MATLAB-default.
        p = vlist[0]
        for r in range(1, m):
            p = np.kron(vlist[r], p)
        return p
    raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_R_KRON_CHAIN mode: {mode!r}")


EigPairFn = Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]


def _normalize_eig_vals(vals: np.ndarray) -> np.ndarray:
    """Return eigenvalues as a 1-D vector from either vector or square matrix input."""
    arr = np.asarray(vals, dtype=np.complex128)
    if arr.ndim == 2 and arr.shape[0] == arr.shape[1]:
        # MATLAB's second `eig` output is a diagonal matrix; SciPy returns a vector.
        return np.diag(arr).astype(np.complex128, copy=False).ravel(order="F")
    return arr.ravel(order="F")


def _env_flag(name: str) -> bool:
    v = str(os.getenv(name, "")).strip().lower()
    return v not in ("", "0", "false", "no", "off")


def _env_text(name: str) -> str:
    return str(os.getenv(name, "")).strip().lower()


def _eig_dgeev_real(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute eigenpairs through raw LAPACK dgeev for experiment parity checks."""
    wr, wi, _vl, vr, info = lapack.dgeev(
        np.asarray(a, dtype=np.float64), compute_vl=0, compute_vr=1
    )
    if int(info) != 0:
        raise RuntimeError(f"dgeev failed with info={int(info)}")
    vals = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    vals = np.asarray(vals, dtype=np.complex128).ravel(order="F")
    vr = np.asarray(vr, dtype=np.float64)
    n = int(vr.shape[0])
    vecs = np.zeros((n, n), dtype=np.complex128)
    k = 0
    while k < n:
        if abs(float(wi[k])) < 1e-300:
            vecs[:, k] = vr[:, k]
            k += 1
        else:
            vecs[:, k] = vr[:, k] + 1j * vr[:, k + 1]
            vecs[:, k + 1] = vr[:, k] - 1j * vr[:, k + 1]
            k += 2
    return vals, vecs


def _condition_submatrix(a: np.ndarray) -> np.ndarray:
    """Optional global conditioning experiments before eig (disabled by default)."""
    mode = _env_text("RGMS_RGM_EXPERIMENT_SUB_CONDITION")
    x = np.asarray(a, dtype=np.float64)
    if mode in ("", "none", "off", "0", "false", "no"):
        return x

    if mode in ("scale_maxabs", "scale"):
        m = float(np.max(np.abs(x))) if x.size else 0.0
        return x if m == 0.0 else (x / m)

    if mode in ("psd_clip", "psd"):
        vals, vecs = np.linalg.eigh(x)
        vals = np.maximum(np.asarray(vals, dtype=np.float64), 0.0)
        y = (vecs @ np.diag(vals) @ vecs.T).astype(np.float64, copy=False)
        return 0.5 * (y + y.T)

    if mode in ("scale_psd", "scale_then_psd"):
        m = float(np.max(np.abs(x))) if x.size else 0.0
        y = x if m == 0.0 else (x / m)
        vals, vecs = np.linalg.eigh(y)
        vals = np.maximum(np.asarray(vals, dtype=np.float64), 0.0)
        y = (vecs @ np.diag(vals) @ vecs.T).astype(np.float64, copy=False)
        return 0.5 * (y + y.T)

    raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_SUB_CONDITION mode: {mode!r}")


def _mi_pair_matrix(ri: np.ndarray, rj: np.ndarray) -> np.ndarray:
    """Build pairwise MI input matrix with optional formation-order experiments."""
    mode = _env_text("RGMS_RGM_EXPERIMENT_MI_FORMATION")
    a = np.asarray(ri, dtype=np.float64)
    b = np.asarray(rj, dtype=np.float64)
    if mode in ("", "none", "off", "0", "false", "no", "matmul", "default"):
        return a @ b.T
    if mode in ("fortran_matmul", "f_matmul"):
        return np.asfortranarray(a) @ np.asfortranarray(b).T
    if mode in ("outer_fwd", "kron_fwd"):
        out = np.zeros((a.shape[0], b.shape[0]), dtype=np.float64)
        for k in range(int(a.shape[1])):
            out += np.outer(a[:, k], b[:, k])
        return out
    if mode in ("outer_rev", "kron_rev"):
        out = np.zeros((a.shape[0], b.shape[0]), dtype=np.float64)
        for k in range(int(a.shape[1]) - 1, -1, -1):
            out += np.outer(a[:, k], b[:, k])
        return out
    raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_MI_FORMATION mode: {mode!r}")


def spm_rgm_group(
    O: Sequence[Sequence[Any]],
    dx: int = 16,
    m: int = 1,
    *,
    eig_pair: Optional[EigPairFn] = None,
    mi_override: Optional[np.ndarray] = None,
    spectral_probe_fn: Optional[Callable[[dict], None]] = None,
) -> List[np.ndarray]:
    """
    FORMAT G = spm_rgm_group(O,dx)
    FORMAT G = spm_rgm_group(O,dx,m)

    Parameters
    ----------
    O :
        ``No × Nt`` layout: outer index outcome ``o`` (0-based), inner time ``t``.
        Each entry is array-like (column vector / matrix as in MATLAB ``O{o,t}``).
    dx :
        Upper bound on group size (default 16).
    m :
        Modalities per outcome (default 1). ``O`` must have ``No`` divisible by ``m``.
    eig_pair :
        Optional ``(sub) -> (vals, vecs)`` replacing ``scipy.linalg.eig`` on each
        active ``MI(i,i)`` block. Must match SciPy convention: ``vals`` length ``n``
        (one eigenvalue per column), ``vecs`` shape ``(n, n)`` with eigenvectors as
        columns. Intended for oracle / MATLAB-numeric bridges only (default ``None``
        uses SciPy).
    mi_override :
        Optional composite-layout ``MI`` matrix of shape ``(no, no)`` to use instead
        of values from :func:`_spm_mdp_mi_scalar`. With a MATLAB ``eig_pair``, this
        carries MATLAB’s exact ``MI`` bytes so the spectral while-loop matches
        ``spm_rgm_group.m``. Default ``None`` builds ``MI`` from ``O`` as in MATLAB.
    spectral_probe_fn :
        Optional callback receiving per-iteration spectral workload records for
        capture/replay diagnostics. Oracle-only; omitted in production usage.

    Returns
    -------
    G :
        List of ``int64`` 1-based index vectors (MATLAB ``G{g}``), after expansion
        from composite outcomes to original modality rows.
    """
    no_orig = len(O)
    if no_orig == 0:
        return []
    nt = len(O[0]) if no_orig else 0

    if no_orig < dx:
        return [np.arange(1, no_orig + 1, dtype=np.int64)]

    if no_orig % m != 0:
        raise ValueError(
            f"spm_rgm_group: number of outcomes No={no_orig} must be divisible by m={m}"
        )

    n_comp = no_orig // m
    r_grid: List[List[np.ndarray]] = [
        [None] * nt for _ in range(n_comp)  # type: ignore[misc]
    ]
    for t in range(nt):
        i = 0
        for o in range(0, no_orig, m):
            vecs = [np.asarray(O[o + r][t], dtype=np.float64) for r in range(m)]
            r_grid[i][t] = _kron_modal_chain(vecs)
            i += 1

    no = n_comp
    n_flags = np.zeros(no, dtype=bool)
    r_cells: List[np.ndarray] = []
    for o in range(no):
        r_o = _spm_cat_row(r_grid[o])
        r_cells.append(r_o)
        d = np.diff(r_o, axis=1)
        n_flags[o] = bool(np.any(np.abs(d) > 1e-14))

    if mi_override is None:
        mi = np.zeros((no, no), dtype=np.float64)
        for i in range(no):
            for j in range(i, no):
                if n_flags[i] and n_flags[j]:
                    p = _mi_pair_matrix(r_cells[i], r_cells[j])
                    val = _spm_mdp_mi_scalar(p)
                    mi[i, j] = val
                    mi[j, i] = val
    else:
        mi = np.asarray(mi_override, dtype=np.float64)
        if mi.shape != (no, no):
            raise ValueError(
                f"spm_rgm_group: mi_override shape {mi.shape} != ({no}, {no})"
            )

    dx = int(np.fix(dx))
    u_thresh = float(np.exp(-16.0))

    active = np.arange(1, no + 1, dtype=np.int64)
    groups: List[np.ndarray] = []

    iter_idx = 0
    while active.size > 0:
        iter_idx += 1
        active_before = np.asarray(active, dtype=np.int64, copy=True)
        sub = mi[np.ix_(active - 1, active - 1)]
        sub = np.asarray(sub, dtype=np.float64)
        # `MI` should be symmetric; enforce exact symmetry to match MATLAB's treatment
        # of the mutual-information matrix as a real symmetric operator in this path.
        sub = 0.5 * (sub + sub.T)
        sub = _condition_submatrix(sub)
        # Optional global conditioning experiment: quantize submatrix to 15 decimals
        # before eig. This is diagnostics-only and remains disabled by default.
        if _env_flag("RGMS_RGM_EXPERIMENT_SUB_ROUND15"):
            sub = np.round(sub, decimals=15)
        # MATLAB: `[e,v] = eig(MI(i,i),'nobalance'); [~,j] = max(diag(v),[],1);`
        #
        # `MI(i,i)` is symmetric, but MATLAB still uses the general-real `eig` path.
        # SciPy's LAPACK-backed `eig` matches MATLAB's returned eigenpairs far more
        # closely than `numpy.linalg.eigh` for the exhaustive structure-learning
        # checkpoint (byte-level `sort(abs(e(:,j)),'descend')` parity).
        if _env_flag("RGMS_RGM_EXPERIMENT_USE_DGEEV"):
            vals_py, vecs_py = _eig_dgeev_real(sub)
        else:
            vals_py, vecs_py = spla.eig(sub, check_finite=False, overwrite_a=False)
        vals_mat = None
        vecs_mat = None
        if eig_pair is None:
            vals, vecs = vals_py, vecs_py
            eig_source = "scipy"
        else:
            vals_mat, vecs_mat = eig_pair(sub)
            vals, vecs = vals_mat, vecs_mat
            eig_source = "eig_pair"
        vals_py = _normalize_eig_vals(vals_py)
        vecs_py = np.asarray(vecs_py, dtype=np.complex128)
        if vecs_py.shape != sub.shape:
            vecs_py = np.reshape(vecs_py, sub.shape, order="F")
        vals = _normalize_eig_vals(vals)
        vecs = np.asarray(vecs, dtype=np.complex128)
        if vecs.shape != sub.shape:
            vecs = np.reshape(vecs, sub.shape, order="F")
        # MATLAB: `[~,j] = max(diag(v),[],1);` on the eigenvalue ordering returned
        # by `eig`. For complex eigenvalues this is magnitude order; ties pick the
        # first occurrence (MATLAB `max` behavior on vectors).
        jmax = int(np.argmax(np.abs(vals)))
        col = vecs[:, jmax]
        # MATLAB: `sort(abs(e(:,j)),'descend')` with `e` complex from `eig`.
        # Use complex magnitude directly (do not strip imaginary parts before
        # `abs`), so near-degenerate noise in real/imag parts matches MATLAB's
        # `abs` pipeline for tie ordering.
        absv = np.asarray(np.abs(col), dtype=np.float64).ravel()
        if _env_flag("RGMS_RGM_EXPERIMENT_ABSV_ROUND15"):
            absv = np.round(absv, decimals=15)
        order = _sort_abs_descend_matlab_like(absv)
        j_take = order[: min(len(order), dx)]
        e_top = absv[j_take]
        j_take = j_take[e_top >= u_thresh]
        chosen = active[j_take]
        jmax_py = int(np.argmax(np.abs(vals_py)))
        col_py = vecs_py[:, jmax_py]
        absv_py = np.asarray(np.abs(col_py), dtype=np.float64).ravel()
        if _env_flag("RGMS_RGM_EXPERIMENT_ABSV_ROUND15"):
            absv_py = np.round(absv_py, decimals=15)
        order_py = _sort_abs_descend_matlab_like(absv_py)
        j_take_py = order_py[: min(len(order_py), dx)]
        e_top_py = absv_py[j_take_py]
        j_take_py = j_take_py[e_top_py >= u_thresh]
        chosen_py = active_before[j_take_py]
        if vals_mat is not None and vecs_mat is not None:
            vals_mat = _normalize_eig_vals(vals_mat)
            vecs_mat = np.asarray(vecs_mat, dtype=np.complex128)
            if vecs_mat.shape != sub.shape:
                vecs_mat = np.reshape(vecs_mat, sub.shape, order="F")
            jmax_mat = int(np.argmax(np.abs(vals_mat)))
            col_mat = vecs_mat[:, jmax_mat]
            absv_mat = np.asarray(np.abs(col_mat), dtype=np.float64).ravel()
            if _env_flag("RGMS_RGM_EXPERIMENT_ABSV_ROUND15"):
                absv_mat = np.round(absv_mat, decimals=15)
            order_mat = _sort_abs_descend_matlab_like(absv_mat)
            j_take_mat = order_mat[: min(len(order_mat), dx)]
            e_top_mat = absv_mat[j_take_mat]
            j_take_mat = j_take_mat[e_top_mat >= u_thresh]
            chosen_mat = active_before[j_take_mat]
        else:
            jmax_mat = None
            absv_mat = None
            order_mat = None
            chosen_mat = None
        if spectral_probe_fn is not None:
            spectral_probe_fn(
                {
                    "iter_idx": int(iter_idx),
                    "m": int(m),
                    "dx": int(dx),
                    "u_thresh": float(u_thresh),
                    "active_before": np.asarray(active_before, dtype=np.int64, copy=True),
                    "sub_mi": np.asarray(sub, dtype=np.float64, copy=True),
                    "eig_source": str(eig_source),
                    "vals_py": np.asarray(vals_py, dtype=np.complex128, copy=True),
                    "vecs_py": np.asarray(vecs_py, dtype=np.complex128, copy=True),
                    "jmax_py": int(jmax_py),
                    "absv_py": np.asarray(absv_py, dtype=np.float64, copy=True),
                    "order_py": np.asarray(order_py, dtype=np.int64, copy=True),
                    "chosen_py": np.asarray(chosen_py, dtype=np.int64, copy=True),
                    "vals_use": np.asarray(vals, dtype=np.complex128, copy=True),
                    "vecs_use": np.asarray(vecs, dtype=np.complex128, copy=True),
                    "jmax_use": int(jmax),
                    "absv_use": np.asarray(absv, dtype=np.float64, copy=True),
                    "order_use": np.asarray(order, dtype=np.int64, copy=True),
                    "chosen_use": np.asarray(chosen, dtype=np.int64, copy=True),
                    "vals_mat": None
                    if vals_mat is None
                    else np.asarray(vals_mat, dtype=np.complex128, copy=True),
                    "vecs_mat": None
                    if vecs_mat is None
                    else np.asarray(vecs_mat, dtype=np.complex128, copy=True),
                    "jmax_mat": jmax_mat,
                    "absv_mat": None
                    if absv_mat is None
                    else np.asarray(absv_mat, dtype=np.float64, copy=True),
                    "order_mat": None
                    if order_mat is None
                    else np.asarray(order_mat, dtype=np.int64, copy=True),
                    "chosen_mat": None
                    if chosen_mat is None
                    else np.asarray(chosen_mat, dtype=np.int64, copy=True),
                }
            )
        groups.append(chosen.astype(np.int64))
        mask = np.ones(active.shape, dtype=bool)
        mask[j_take] = False
        active = active[mask]

    for g_idx in range(len(groups)):
        comp_ids = groups[g_idx]
        k_list: List[int] = []
        for c in comp_ids:
            j_base = (int(c) - 1) * m
            k_list.extend(range(j_base + 1, j_base + m + 1))
        groups[g_idx] = np.asarray(k_list, dtype=np.int64)

    return groups
