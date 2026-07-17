"""DEMO2 fork of ``python_src/toolbox/DEM/spm_RDP_sort.py`` (uses demo2 ``spm_RDP_compress``)."""

from __future__ import annotations

import copy
from typing import Any, Callable

import numpy as np
from scipy import sparse

from python_src.spm_dir_norm import spm_dir_norm
from python_src_demo2.toolbox.DEM.spm_RDP_compress import spm_RDP_compress


def spm_RDP_sort_flow_B(MDP: list[dict[str, Any]]) -> np.ndarray:
    """Same `B` as MATLAB `spm_dir_norm(sum(MDP{end}.b{1},3) > 0)` (oracle helper)."""
    end = MDP[-1]
    b0 = end["b"][0]
    if isinstance(b0, list) and len(b0) == 1:
        b1 = np.asarray(b0[0], dtype=np.float64)
    else:
        b1 = np.asarray(b0, dtype=np.float64)
    if b1.ndim == 2:
        b1 = np.reshape(b1, (b1.shape[0], b1.shape[1], 1), order="F")
    s = np.sum(b1, axis=2)
    b = spm_dir_norm((s > 0).astype(np.float64))
    return np.asarray(b, dtype=np.float64)


def spm_RDP_sort(
    MDP: list[dict[str, Any]],
    *args: Any,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """MATLAB ``spm_RDP_sort(MDP)`` — DEMO2 lane uses demo2 ``spm_RDP_compress``."""
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
    B = spm_RDP_sort_flow_B(mdp)
    ns = int(B.shape[0])

    if eig is not None:
        _eig = eig
    else:
        from matlab_compat import resolve_spm_RDP_sort_eig

        _eig = resolve_spm_RDP_sort_eig()
    w, V = _eig(B)
    from matlab_compat import principal_eig_column_index

    j_eig = principal_eig_column_index(w)
    vec = np.abs(V[:, j_eig])
    p_col = spm_dir_norm(np.reshape(vec, (-1, 1), order="F"))
    p = np.asarray(p_col, dtype=np.float64).ravel(order="F")
    idx = np.arange(ns, dtype=np.int64)

    j_mask = np.ones(ns, dtype=bool)

    if len(args) == 0:
        k = np.lexsort((idx, p))
        for i in k:
            d = j_mask.copy()
            d[int(i)] = False
            if not np.any(d):
                continue
            b_dd = B[np.ix_(d, d)]
            col_any = np.any(b_dd, axis=0)
            if np.all(col_any):
                j_mask = d

    j_ix = np.flatnonzero(j_mask)
    order = np.lexsort((j_ix, -p[j_ix]))
    j_order = j_ix[order]

    r_full = sparse.eye(ns, format="csr", dtype=np.float64)
    r_sub = r_full[:, j_order]
    mdp_out = spm_RDP_compress(mdp, r_sub, "first")
    j_out = (j_order + 1).astype(np.int64).reshape(-1, 1)
    return mdp_out, j_out
