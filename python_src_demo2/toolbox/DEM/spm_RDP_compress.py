"""DEMO2 fork of ``python_src/toolbox/DEM/spm_RDP_compress.py`` (``_as_b_3d`` / narrow ``b`` path)."""

from __future__ import annotations

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_dir_reduce import spm_dir_reduce


def spm_RDP_compress(MDP, R, OPT=None):
    mdp = MDP
    r_mat = np.asarray(R.toarray() if hasattr(R, "toarray") else R, dtype=np.float64)

    n_top = len(mdp)
    top = mdp[n_top - 1]

    for g in range(1, len(top["a"]) + 1):
        if _cell_scalar_int(top["id"]["A"][g - 1]) == 1:
            try:
                a_g = np.asarray(_unwrap_cell(top["a"][g - 1]), dtype=np.float64)
                top["a"][g - 1] = [a_g @ r_mat]
            except Exception:
                a_g = np.asarray(_unwrap_cell(top["A"][g - 1]), dtype=np.float64)
                top["A"][g - 1] = [spm_dir_norm(a_g @ r_mat)]

    ns = int(r_mat.shape[1])
    try:
        b1 = _as_b_3d(top["b"][0])
        nu = int(b1.shape[2])
        b_new = np.zeros((ns, ns, nu), dtype=np.float64)
        for u in range(nu):
            b_new[:, :, u] = r_mat.T @ b1[:, :, u] @ r_mat
        u_mask = np.any(b_new, axis=(0, 1))
        top["b"][0] = [b_new[:, :, u_mask]]
    except (KeyError, IndexError, TypeError):
        b1 = _as_b_3d(top["B"][0])
        nu = int(b1.shape[2])
        b_new = np.zeros((ns, ns, nu), dtype=np.float64)
        for u in range(nu):
            b_new[:, :, u] = spm_dir_norm(r_mat.T @ b1[:, :, u] @ r_mat)
        u_mask = np.any(b_new, axis=(0, 1))
        top["B"][0] = [b_new[:, :, u_mask]]

    if OPT is not None:
        return mdp

    for n in range(len(mdp), 1, -1):
        mdp_n = mdp[n - 1]
        mdp_prev = mdp[n - 2]
        for i in range(1, len(mdp_n["a"]) + 1):
            g = _cell_scalar_int(mdp_n["id"]["A"][i - 1])
            if int(mdp_n["sA"][g - 1]) == 1 and int(mdp_n["sC"][g - 1]) == 1:
                r_loc = spm_dir_reduce(np.asarray(_unwrap_cell(mdp_n["a"][g - 1]), dtype=np.float64).T)
                r_loc = np.asarray(r_loc.toarray() if hasattr(r_loc, "toarray") else r_loc, dtype=np.float64)
                mdp_n["a"][g - 1] = [r_loc.T @ np.asarray(_unwrap_cell(mdp_n["a"][g - 1]), dtype=np.float64)]

                for f in range(1, len(mdp_prev["id"]["D"]) + 1):
                    if g in set(_as_int_list(mdp_prev["id"]["D"][f - 1])):
                        ns_f = int(r_loc.shape[1])
                        try:
                            b_f = _as_b_3d(mdp_prev["b"][f - 1])
                            nu_f = int(b_f.shape[2])
                            b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                            for u in range(nu_f):
                                b_comp[:, :, u] = r_loc.T @ b_f[:, :, u] @ r_loc
                            mdp_prev["b"][f - 1] = [b_comp]
                        except (KeyError, IndexError, TypeError):
                            b_f = _as_b_3d(mdp_prev["B"][f - 1])
                            nu_f = int(b_f.shape[2])
                            b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                            for u in range(nu_f):
                                b_comp[:, :, u] = spm_dir_norm(r_loc.T @ b_f[:, :, u] @ r_loc)
                            mdp_prev["B"][f - 1] = [b_comp]

                        for gf in _find_id_a_children(mdp_prev["id"]["A"], f):
                            a_gf = np.asarray(_unwrap_cell(mdp_prev["a"][gf - 1]), dtype=np.float64)
                            mdp_prev["a"][gf - 1] = [a_gf @ r_loc]

                for f in range(1, len(mdp_prev["id"]["E"]) + 1):
                    if g in set(_as_int_list(mdp_prev["id"]["E"][f - 1])):
                        nu_f = int(r_loc.shape[1])
                        try:
                            b_f = _as_b_3d(mdp_prev["b"][f - 1])
                            ns_f = int(b_f.shape[1])
                            b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                            b_perm = np.transpose(b_f, (0, 2, 1))
                            for s in range(ns_f):
                                b_comp[:, s, :] = b_perm[:, :, s] @ r_loc
                            mdp_prev["b"][f - 1] = [b_comp]
                        except (KeyError, IndexError, TypeError):
                            b_f = _as_b_3d(mdp_prev["B"][f - 1])
                            ns_f = int(b_f.shape[1])
                            b_comp = np.zeros((ns_f, ns_f, nu_f), dtype=np.float64)
                            b_perm = np.transpose(b_f, (0, 2, 1))
                            for s in range(ns_f):
                                b_comp[:, s, :] = b_perm[:, :, s] @ r_loc
                            mdp_prev["B"][f - 1] = [b_comp]

    return mdp


def _unwrap_cell(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _as_b_3d(x) -> np.ndarray:
    """``B(:,:,u)`` slice access for 2-D or 3-D transition tensors."""
    b = np.asarray(_unwrap_cell(x), dtype=np.float64)
    if b.ndim == 2:
        b = np.reshape(b, (b.shape[0], b.shape[1], 1), order="F")
    return b


def _cell_scalar_int(x) -> int:
    return int(np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")[0])


def _as_int_list(x) -> list[int]:
    arr = np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")
    return [int(v) for v in arr.tolist()]


def _find_id_a_children(id_a: list, f: int) -> list[int]:
    out: list[int] = []
    for i, item in enumerate(id_a, start=1):
        if _cell_scalar_int(item) == int(f):
            out.append(i)
    return out
