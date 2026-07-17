"""OPTIM1 — ``spm_RDP_compress`` (Tier Cv0 fork + Ca/Cc/Ce basin-first column select)."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_dir_reduce import spm_dir_reduce


def spm_RDP_compress_optim(MDP, R, OPT=None):
    mdp = MDP
    j_idx = _column_selector_indices(R)
    if j_idx is not None:
        _compress_top_selector(mdp[-1], j_idx)
    else:
        r_mat = _as_dense_r(R)
        _compress_top_generic(mdp[-1], r_mat)

    if OPT is not None:
        return mdp

    for n in range(len(mdp), 1, -1):
        mdp_n = mdp[n - 1]
        mdp_prev = mdp[n - 2]
        d_sets = [_as_int_set(mdp_prev["id"]["D"][f - 1]) for f in range(1, len(mdp_prev["id"]["D"]) + 1)]
        e_sets = [_as_int_set(mdp_prev["id"]["E"][f - 1]) for f in range(1, len(mdp_prev["id"]["E"]) + 1)]
        a_children = _children_by_factor(mdp_prev["id"]["A"])

        for i in range(1, len(mdp_n["a"]) + 1):
            g = _cell_scalar_int(mdp_n["id"]["A"][i - 1])
            if int(mdp_n["sA"][g - 1]) == 1 and int(mdp_n["sC"][g - 1]) == 1:
                a_g = np.asarray(_unwrap_cell(mdp_n["a"][g - 1]), dtype=np.float64)
                r_loc = spm_dir_reduce(a_g.T)
                r_loc = np.asarray(r_loc.toarray() if hasattr(r_loc, "toarray") else r_loc, dtype=np.float64)
                mdp_n["a"][g - 1] = [r_loc.T @ a_g]

                for f in range(1, len(mdp_prev["id"]["D"]) + 1):
                    if g in d_sets[f - 1]:
                        ns_f = int(r_loc.shape[1])
                        nu_f = 0
                        b_comp = None
                        try:
                            b_f = np.asarray(_unwrap_cell(mdp_prev["b"][f - 1]), dtype=np.float64)
                            nu_f = int(b_f.shape[2]) if b_f.ndim > 2 else 1
                            b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                            for u in range(nu_f):
                                b_comp[:, :, u] = r_loc.T @ b_f[:, :, u] @ r_loc
                            mdp_prev["b"][f - 1] = [b_comp]
                        except Exception:
                            b_f = np.asarray(_unwrap_cell(mdp_prev["B"][f - 1]), dtype=np.float64)
                            nu_f = int(b_f.shape[2]) if b_f.ndim > 2 else 1
                            b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                            for u in range(nu_f):
                                b_comp[:, :, u] = spm_dir_norm(r_loc.T @ b_f[:, :, u] @ r_loc)
                            mdp_prev["B"][f - 1] = [b_comp]

                        for gf in a_children.get(f, ()):
                            a_gf = np.asarray(_unwrap_cell(mdp_prev["a"][gf - 1]), dtype=np.float64)
                            mdp_prev["a"][gf - 1] = [a_gf @ r_loc]

                for f in range(1, len(mdp_prev["id"]["E"]) + 1):
                    if g in e_sets[f - 1]:
                        nu_f = int(r_loc.shape[1])
                        b_f = np.asarray(_unwrap_cell(mdp_prev["b"][f - 1]), dtype=np.float64)
                        ns_f = int(b_f.shape[1])
                        b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                        try:
                            b_perm = np.transpose(b_f, (0, 2, 1))
                            for s in range(ns_f):
                                b_comp[:, s, :] = b_perm[:, :, s] @ r_loc
                            mdp_prev["b"][f - 1] = [b_comp]
                        except Exception:
                            b_f = np.asarray(_unwrap_cell(mdp_prev["B"][f - 1]), dtype=np.float64)
                            b_perm = np.transpose(b_f, (0, 2, 1))
                            for s in range(ns_f):
                                b_comp[:, s, :] = b_perm[:, :, s] @ r_loc
                            mdp_prev["B"][f - 1] = [b_comp]

    return mdp


def spm_RDP_compress_columns_first(MDP, j_idx) -> list:
    """Top-level column select only (``OPT='first'``) — direct ``j`` indices (basin lane)."""
    mdp = MDP
    j_arr = np.asarray(j_idx, dtype=np.int64).ravel(order="F")
    _compress_top_selector(mdp[-1], j_arr)
    return mdp


def _compress_top_selector(top, j_idx: np.ndarray) -> None:
    """``R = speye(Ns,Ns)(:,j)`` — submatrix / column select without dense ``R``."""
    for g in range(1, len(top["a"]) + 1):
        if _cell_scalar_int(top["id"]["A"][g - 1]) == 1:
            try:
                a_g = np.asarray(_unwrap_cell(top["a"][g - 1]), dtype=np.float64)
                top["a"][g - 1] = [a_g[:, j_idx]]
            except Exception:
                a_g = np.asarray(_unwrap_cell(top["A"][g - 1]), dtype=np.float64)
                top["A"][g - 1] = [spm_dir_norm(a_g[:, j_idx])]

    try:
        b0 = np.asarray(_unwrap_cell(top["b"][0]), dtype=np.float64)
        b_new = b0[np.ix_(j_idx, j_idx)]
        u_mask = np.any(b_new, axis=(0, 1))
        top["b"][0] = [b_new[:, :, u_mask]]
    except Exception:
        b0 = np.asarray(_unwrap_cell(top["B"][0]), dtype=np.float64)
        nu = int(b0.shape[2]) if b0.ndim > 2 else 1
        b_sub = b0[np.ix_(j_idx, j_idx)]
        b_new = np.zeros((j_idx.size, j_idx.size, nu), dtype=np.float64)
        for u in range(nu):
            b_new[:, :, u] = spm_dir_norm(b_sub[:, :, u])
        u_mask = np.any(b_new, axis=(0, 1))
        top["B"][0] = [b_new[:, :, u_mask]]


def _compress_top_generic(top, r_mat: np.ndarray) -> None:
    ns = int(r_mat.shape[1])
    for g in range(1, len(top["a"]) + 1):
        if _cell_scalar_int(top["id"]["A"][g - 1]) == 1:
            try:
                a_g = np.asarray(_unwrap_cell(top["a"][g - 1]), dtype=np.float64)
                top["a"][g - 1] = [a_g @ r_mat]
            except Exception:
                a_g = np.asarray(_unwrap_cell(top["A"][g - 1]), dtype=np.float64)
                top["A"][g - 1] = [spm_dir_norm(a_g @ r_mat)]

    b0 = None
    nu = 1
    try:
        b0 = np.asarray(_unwrap_cell(top["b"][0]), dtype=np.float64)
        nu = int(b0.shape[2]) if b0.ndim > 2 else 1
        b_new = np.zeros((ns, ns, nu), dtype=np.float64)
        for u in range(nu):
            b_new[:, :, u] = r_mat.T @ b0[:, :, u] @ r_mat
        u_mask = np.any(b_new, axis=(0, 1))
        top["b"][0] = [b_new[:, :, u_mask]]
    except Exception:
        if b0 is None:
            b0 = np.asarray(_unwrap_cell(top["B"][0]), dtype=np.float64)
            nu = int(b0.shape[2]) if b0.ndim > 2 else 1
        b_new = np.zeros((ns, ns, nu), dtype=np.float64)
        for u in range(nu):
            b_new[:, :, u] = spm_dir_norm(r_mat.T @ b0[:, :, u] @ r_mat)
        u_mask = np.any(b_new, axis=(0, 1))
        top["B"][0] = [b_new[:, :, u_mask]]


def _column_selector_indices(R) -> np.ndarray | None:
    """Row indices ``j`` when ``R`` is ``speye(Ns,Ns)(:,j)`` (one-hot columns)."""
    if sparse.issparse(R):
        r_csr = R.tocsr()
        k = int(r_csr.shape[1])
        if k == 0:
            return np.array([], dtype=np.int64)
        if int(r_csr.nnz) != k:
            return None
        rows = np.empty(k, dtype=np.int64)
        for c in range(k):
            start = int(r_csr.indptr[c])
            end = int(r_csr.indptr[c + 1])
            if end - start != 1 or float(r_csr.data[start]) != 1.0:
                return None
            rows[c] = int(r_csr.indices[start])
        return rows

    r = np.asarray(R, dtype=np.float64)
    if r.ndim != 2:
        return None
    k = int(r.shape[1])
    if k == 0:
        return np.array([], dtype=np.int64)
    rows = np.empty(k, dtype=np.int64)
    for c in range(k):
        col = r[:, c]
        nz = np.flatnonzero(col)
        if nz.size != 1 or float(col[nz[0]]) != 1.0:
            return None
        rows[c] = int(nz[0])
    return rows


def _as_dense_r(R) -> np.ndarray:
    return np.asarray(R.toarray() if hasattr(R, "toarray") else R, dtype=np.float64)


def _unwrap_cell(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _cell_scalar_int(x) -> int:
    return int(np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")[0])


def _as_int_set(x) -> frozenset[int]:
    arr = np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")
    return frozenset(int(v) for v in arr.tolist())


def _children_by_factor(id_a: list) -> dict[int, tuple[int, ...]]:
    buckets: dict[int, list[int]] = {}
    for i, item in enumerate(id_a, start=1):
        f = _cell_scalar_int(item)
        buckets.setdefault(f, []).append(i)
    return {f: tuple(v) for f, v in buckets.items()}
