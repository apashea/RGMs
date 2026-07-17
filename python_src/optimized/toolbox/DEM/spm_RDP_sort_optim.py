"""OPTIM1 — ``spm_RDP_sort`` (Tier E10: NESS prune + compress optim).

**File scope:** NESS prune uses incremental column-support counts (E10v1; same
semantics as fidelity ``j_mask`` loop); ``spm_RDP_compress_optim`` on the sort path.
Slow/general paths unchanged vs fidelity (``spm_dir_norm``, ``eig`` contract).
"""

from __future__ import annotations

import copy
from typing import Any, Callable

import numpy as np
from scipy import sparse

from python_src.optimized.toolbox.DEM.spm_RDP_compress_optim import spm_RDP_compress_optim
from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort_flow_B


def spm_RDP_sort_optim(
    MDP: list[dict[str, Any]],
    *args: Any,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Optim lane — same API/semantics as ``spm_RDP_sort`` (native or injected ``eig``)."""
    mdp = copy.deepcopy(MDP)
    end = mdp[-1]
    b0 = end["b"][0]
    if isinstance(b0, list) and len(b0) == 1:
        b1 = np.asarray(b0[0], dtype=np.float64)
    else:
        b1 = np.asarray(b0, dtype=np.float64)
    if b1.ndim == 2:
        b1 = np.reshape(b1, (b1.shape[0], b1.shape[1], 1), order="F")
        end["b"][0] = [b1]
    b_mat = spm_RDP_sort_flow_B(mdp)
    ns = int(b_mat.shape[0])

    if eig is not None:
        _eig = eig
    else:
        from matlab_compat import resolve_spm_RDP_sort_eig

        _eig = resolve_spm_RDP_sort_eig()

    w, v = _eig(b_mat)
    from matlab_compat import principal_eig_column_index

    j_eig = principal_eig_column_index(w)
    vec = np.abs(v[:, j_eig])
    p_col = spm_dir_norm(np.reshape(vec, (-1, 1), order="F"))
    p = np.asarray(p_col, dtype=np.float64).ravel(order="F")
    idx = np.arange(ns, dtype=np.int64)

    if len(args) == 0:
        j_mask = _ness_prune_mask_col_support(b_mat, p, ns)
    else:
        j_mask = np.ones(ns, dtype=bool)

    j_ix = np.flatnonzero(j_mask)
    order = np.lexsort((j_ix, -p[j_ix]))
    j_order = j_ix[order]

    r_full = sparse.eye(ns, format="csr", dtype=np.float64)
    r_sub = r_full[:, j_order]
    mdp_out = spm_RDP_compress_optim(mdp, r_sub, "first")
    j_out = (j_order + 1).astype(np.int64).reshape(-1, 1)
    return mdp_out, j_out


def _ness_prune_mask_col_support(b_mat: np.ndarray, p: np.ndarray, ns: int) -> np.ndarray:
    """MATLAB ``for i = k`` prune loop — column-support counts (no submatrix ``ix_``)."""
    b_bool = np.asarray(b_mat > 0, dtype=np.uint8)
    col_support = b_bool.sum(axis=0, dtype=np.int32)

    idx = np.arange(ns, dtype=np.int64)
    k = np.lexsort((idx, p))
    active = np.arange(ns, dtype=np.int64)
    n_act = ns

    for i in k:
        i_i = int(i)
        pos = int(np.searchsorted(active[:n_act], i_i))
        if pos >= n_act or int(active[pos]) != i_i:
            continue
        trial_n = n_act - 1
        if trial_n == 0:
            continue
        rem = int(active[pos])
        ok = True
        if pos > 0:
            cols0 = active[:pos]
            if not np.all(col_support[cols0] - b_bool[rem, cols0] > 0):
                ok = False
        if ok:
            cols1 = active[pos + 1 : n_act]
            if not np.all(col_support[cols1] - b_bool[rem, cols1] > 0):
                ok = False
        if ok:
            col_support -= b_bool[rem, :]
            active[pos:trial_n] = active[pos + 1 : n_act]
            n_act = trial_n

    j_mask = np.zeros(ns, dtype=bool)
    j_mask[active[:n_act]] = True
    return j_mask


def _ness_prune_mask_shrinking_active(b_mat: np.ndarray, p: np.ndarray, ns: int) -> np.ndarray:
    """MATLAB ``for i = k`` prune loop with shrinking ``active`` (fidelity-equivalent)."""
    idx = np.arange(ns, dtype=np.int64)
    k = np.lexsort((idx, p))
    active = np.arange(ns, dtype=np.int64)
    n_act = ns

    for i in k:
        i_i = int(i)
        pos = int(np.searchsorted(active[:n_act], i_i))
        if pos >= n_act or int(active[pos]) != i_i:
            continue
        trial_n = n_act - 1
        if trial_n == 0:
            continue
        if pos > 0:
            trial = np.empty(trial_n, dtype=np.int64)
            trial[:pos] = active[:pos]
            trial[pos:] = active[pos + 1 : n_act]
        else:
            trial = active[1:n_act].copy()
        b_dd = b_mat[np.ix_(trial, trial)]
        if np.all(np.any(b_dd, axis=0)):
            active[:trial_n] = trial
            n_act = trial_n

    j_mask = np.zeros(ns, dtype=bool)
    j_mask[active[:n_act]] = True
    return j_mask
