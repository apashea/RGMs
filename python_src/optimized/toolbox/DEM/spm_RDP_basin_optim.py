"""OPTIM1 — ``spm_RDP_basin`` (Cv0/Ca/Cc compress + Cb ``spm_set_goals_optim``)."""

from __future__ import annotations

import numpy as np

from python_src.optimized.toolbox.DEM.spm_RDP_compress_optim import spm_RDP_compress_columns_first
from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim


def spm_RDP_basin_optim(MDP, S, chi, L=None):
    mdp = spm_set_goals_optim(MDP, S, chi)
    h = _as_int_vector(mdp[-1]["id"].get("hid", []))
    c = _as_int_vector(mdp[-1]["id"].get("cid", []))

    if L is None:
        l_vec = np.asarray([32, 1], dtype=np.int64)
    else:
        l_vec = np.asarray(L, dtype=np.int64).ravel(order="F")
        if l_vec.size < 2:
            l_vec = np.asarray([int(l_vec[0]), 1], dtype=np.int64)

    b = np.sum(np.asarray(_unwrap_cell(mdp[-1]["b"][0]), dtype=np.float64), axis=2) > 0
    if c.size:
        b[c - 1, :] = False

    ns = int(b.shape[0])

    nt_p = max(int(l_vec[0]), 1)
    p = np.zeros((nt_p + 1, ns), dtype=bool)
    if h.size:
        p[0, h - 1] = True
    for t in range(1, nt_p + 1):
        p_next = np.any(b[p[t - 1, :], :], axis=0) if np.any(p[t - 1, :]) else np.zeros((ns,), dtype=bool)
        p[t, :] = p_next
        if not np.any(p_next):
            break

    nt_c = max(int(l_vec[1]), 1)
    c_paths = np.zeros((nt_c + 1, ns), dtype=bool)
    if h.size:
        c_paths[0, h - 1] = True
    for t in range(1, nt_c + 1):
        c_next = np.any(b[:, c_paths[t - 1, :]], axis=1) if np.any(c_paths[t - 1, :]) else np.zeros((ns,), dtype=bool)
        c_paths[t, :] = c_next
        if not np.any(c_next):
            break

    r_keep = np.ones((ns,), dtype=bool)
    if c.size:
        r_keep[c - 1] = False
    r_keep = r_keep & (np.any(p, axis=0) | np.any(c_paths, axis=0))

    j = np.flatnonzero(r_keep).astype(np.int64, copy=False)
    mdp = spm_RDP_compress_columns_first(mdp, j)

    mdp = spm_set_goals_optim(mdp, S, chi)
    b_post = np.sum(np.asarray(_unwrap_cell(mdp[-1]["b"][0]), dtype=np.float64), axis=2)
    d = np.any(b_post, axis=0)
    o = np.any(b_post, axis=1)
    h = _as_int_vector(mdp[-1]["id"].get("hid", []))
    c = _as_int_vector(mdp[-1]["id"].get("cid", []))
    return mdp, d, o, h, c


def _unwrap_cell(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _as_int_vector(x) -> np.ndarray:
    arr = np.asarray(x, dtype=np.int64).ravel(order="F")
    return arr
