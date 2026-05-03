"""Pass 1 transliteration of spm_RDP_sort.m (DEM / RDP NESS sort + compress)."""

from __future__ import annotations

import copy
from typing import Any, Callable

import numpy as np
from scipy import sparse

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_RDP_compress import spm_RDP_compress


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
    """MATLAB `spm_RDP_sort(MDP)` or `spm_RDP_sort(MDP,~)`.

    When a second argument is supplied (``nargin >= 2`` in MATLAB), pruning of small
    NESS states is skipped. A single-argument call runs the pruning loop.

    Parameters
    ----------
    eig :
        Optional ``(B,) -> (w, V)`` matching :func:`numpy.linalg.eig` layout
        (1-D eigenvalues, columns of ``V`` are eigenvectors). For MATLAB-oracle
        work only, pass an Engine-backed ``eig(B,'nobalance')`` bridge; default
        ``None`` uses :func:`numpy.linalg.eig`.
    """
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

    _eig = eig if eig is not None else np.linalg.eig
    w, V = _eig(B)
    j_eig = int(np.argmax(np.real(w)))
    vec = np.abs(V[:, j_eig])
    p_col = spm_dir_norm(np.reshape(vec, (-1, 1), order="F"))
    p = np.asarray(p_col, dtype=np.float64).ravel(order="F")
    idx = np.arange(ns, dtype=np.int64)

    j_mask = np.ones(ns, dtype=bool)

    if len(args) == 0:
        # MATLAB stable `sort(p,'ascend')`: ascending p, then lower linear index on ties.
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
    # Descending p on retained states; lower state index first on ties (MATLAB stable sort).
    order = np.lexsort((j_ix, -p[j_ix]))
    j_order = j_ix[order]

    r_full = sparse.eye(ns, format="csr", dtype=np.float64)
    r_sub = r_full[:, j_order]
    mdp_out = spm_RDP_compress(mdp, r_sub, "first")
    j_out = (j_order + 1).astype(np.int64).reshape(-1, 1)
    return mdp_out, j_out
