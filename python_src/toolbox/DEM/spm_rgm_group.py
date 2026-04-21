"""
Compression of a (Dirichlet) probability tensor — spectral grouping of outcomes.

Translated from spm_rgm_group.m (Pass 1). Uses `spm_cat`, `spm_MDP_MI`, and
`numpy.kron` in the same order as MATLAB `kron` inside the multimodal loop.
"""

from __future__ import annotations

from typing import Any, List, Sequence, Union

import numpy as np
import scipy.linalg as spla

from python_src.spm_cat import spm_cat
from python_src.spm_MDP_MI import spm_MDP_MI


def _sort_abs_descend_matlab_like(absv: np.ndarray) -> np.ndarray:
    """Row order after MATLAB ``sort(abs(e(:,jmax)),'descend')`` on a column vector.

    Verified against MATLAB Engine on the structure-learning exhaustive
    checkpoint: MATLAB's permutation matches NumPy
    ``argsort(-abs(x), kind='mergesort')``.
    """
    a = np.asarray(absv, dtype=np.float64).ravel()
    n = int(a.size)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    return np.argsort(-a, kind="mergesort").astype(np.int64, copy=False)


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
    row = [[cells[t] for t in range(len(cells))]]
    cat = spm_cat(row)
    if hasattr(cat, "toarray"):
        cat = cat.toarray()
    return np.asarray(cat, dtype=np.float64)


def spm_rgm_group(
    O: Sequence[Sequence[Any]],
    dx: int = 16,
    m: int = 1,
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
            p = np.asarray(O[o][t], dtype=np.float64)
            for r in range(1, m):
                p = np.kron(p, np.asarray(O[o + r][t], dtype=np.float64))
            r_grid[i][t] = p
            i += 1

    no = n_comp
    n_flags = np.zeros(no, dtype=bool)
    r_cells: List[np.ndarray] = []
    for o in range(no):
        r_o = _spm_cat_row(r_grid[o])
        r_cells.append(r_o)
        d = np.diff(r_o, axis=1)
        n_flags[o] = bool(np.any(np.abs(d) > 1e-14))

    mi = np.zeros((no, no), dtype=np.float64)
    for i in range(no):
        for j in range(i, no):
            if n_flags[i] and n_flags[j]:
                p = r_cells[i] @ r_cells[j].T
                val = _spm_mdp_mi_scalar(p)
                mi[i, j] = val
                mi[j, i] = val

    dx = int(np.fix(dx))
    u_thresh = float(np.exp(-16.0))

    active = np.arange(1, no + 1, dtype=np.int64)
    groups: List[np.ndarray] = []

    while active.size > 0:
        sub = mi[np.ix_(active - 1, active - 1)]
        sub = np.asarray(sub, dtype=np.float64)
        # `MI` should be symmetric; enforce exact symmetry to match MATLAB's treatment
        # of the mutual-information matrix as a real symmetric operator in this path.
        sub = 0.5 * (sub + sub.T)
        # MATLAB: `[e,v] = eig(MI(i,i),'nobalance'); [~,j] = max(diag(v),[],1);`
        #
        # `MI(i,i)` is symmetric, but MATLAB still uses the general-real `eig` path.
        # SciPy's LAPACK-backed `eig` matches MATLAB's returned eigenpairs far more
        # closely than `numpy.linalg.eigh` for the exhaustive structure-learning
        # checkpoint (byte-level `sort(abs(e(:,j)),'descend')` parity).
        vals, vecs = spla.eig(sub, check_finite=False, overwrite_a=False)
        vals = np.asarray(vals, dtype=np.complex128).ravel(order="F")
        vecs = np.asarray(vecs, dtype=np.complex128)
        # MATLAB: `[~,j] = max(diag(v),[],1);` on the eigenvalue ordering returned
        # by `eig`. For complex eigenvalues this is magnitude order; ties pick the
        # first occurrence (MATLAB `max` behavior on vectors).
        jmax = int(np.argmax(np.abs(vals)))
        col = vecs[:, jmax]
        if np.max(np.abs(np.imag(col))) <= 1e-12 * max(1.0, float(np.max(np.abs(col)))):
            vec = np.real(col)
        else:
            vec = col
        # MATLAB uses abs(complex) magnitude here, not abs(real-part only).
        absv = np.abs(vec)
        order = _sort_abs_descend_matlab_like(absv)
        j_take = order[: min(len(order), dx)]
        e_top = absv[j_take]
        j_take = j_take[e_top >= u_thresh]
        chosen = active[j_take]
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
