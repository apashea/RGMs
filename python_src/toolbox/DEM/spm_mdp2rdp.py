"""Pass 1 transliteration of spm_mdp2rdp.m (MDP cell array → nested RDP)."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_mdp2rdp_a import spm_mdp2rdp_a


def spm_mdp2rdp(MDP: list[dict[str, Any]], p=None, q=None, T=None, FIX=None):
    """MATLAB ``RDP = spm_mdp2rdp(MDP,p,q,T,FIX)``."""
    if p is None:
        p = 0
    if q is None:
        q = 0
    if T is None:
        T = 2
    if FIX is None:
        FIX = {"A": True, "B": True}

    if "a" in MDP[0]:
        return spm_mdp2rdp_a(MDP, p, q, T, FIX)

    mdp = copy.deepcopy(MDP)
    nm = len(mdp)

    p = _expand_param_nm(p, nm)
    q = _expand_param_nm(q, nm)

    if nm < 2:
        rdp = copy.deepcopy(mdp[0])
        rdp["L"] = 1
        rdp["T"] = T
        return rdp

    n_last = nm - 1
    if len(mdp[n_last]["B"]) > 1:
        mdp[n_last]["B"] = [mdp[n_last]["B"][0]]
        g = mdp[n_last]["G"]
        if isinstance(g, dict):
            mdp[n_last]["G"] = {1: g[1]} if 1 in g else {min(g.keys()): g[min(g.keys())]}
        else:
            mdp[n_last]["G"] = [g[0]]

        na = len(mdp[n_last]["A"])
        d_la = np.zeros(na, dtype=bool)
        for g in range(na):
            id_ag = np.asarray(_unwrap_cell(mdp[n_last]["id"]["A"][g]), dtype=np.float64).ravel()
            d_la[g] = not np.any(id_ag > 1)
        i_la = np.flatnonzero(d_la) + 1

        mdp[n_last]["A"] = [mdp[n_last]["A"][g] for g in range(na) if d_la[g]]
        mdp[n_last]["id"]["A"] = [mdp[n_last]["id"]["A"][g] for g in range(na) if d_la[g]]
        if "C" in mdp[n_last]:
            mdp[n_last]["C"] = [mdp[n_last]["C"][g] for g in range(na) if d_la[g]]

        _remap_subordinate_de_py(i_la, mdp[n_last - 1])

    for n_ml in range(nm, 1, -1):
        idx = n_ml - 1

        na = len(mdp[idx]["A"])
        d_ua = np.ones(na, dtype=bool)
        for g in range(na):
            ag = _unwrap_cell(mdp[idx]["A"][g])
            if callable(ag):
                continue
            ag_arr = np.asarray(ag, dtype=np.float64)
            if ag_arr.shape[0] < 2:
                d_ua[g] = False
        i_ua = np.flatnonzero(d_ua) + 1

        mdp[idx]["A"] = [mdp[idx]["A"][g] for g in range(na) if d_ua[g]]
        mdp[idx]["id"]["A"] = [mdp[idx]["id"]["A"][g] for g in range(na) if d_ua[g]]
        if "C" in mdp[idx]:
            mdp[idx]["C"] = [mdp[idx]["C"][g] for g in range(na) if d_ua[g]]

        _remap_subordinate_de_py(i_ua, mdp[idx - 1])

        nb = len(mdp[idx]["B"])
        d_ub = np.ones(nb, dtype=bool)
        for f in range(nb):
            bf = _unwrap_cell(mdp[idx]["B"][f])
            if callable(bf):
                continue
            if np.asarray(bf, dtype=np.float64).size == 1:
                d_ub[f] = False

        nz = np.flatnonzero(~d_ub)
        c_orig = int(nz[0]) + 1 if nz.size else 1
        d_ub[c_orig - 1] = True
        i_ub = np.flatnonzero(d_ub) + 1
        k_drop = np.flatnonzero(~d_ub) + 1

        mdp[idx]["B"] = [mdp[idx]["B"][f] for f in range(nb) if d_ub[f]]
        mdp[idx]["id"]["D"] = [mdp[idx]["id"]["D"][f] for f in range(nb) if d_ub[f]]
        mdp[idx]["id"]["E"] = [mdp[idx]["id"]["E"][f] for f in range(nb) if d_ub[f]]

        if "U" in mdp[idx]:
            u_row = np.asarray(mdp[idx]["U"], dtype=bool).ravel()
            mdp[idx]["U"] = np.array([u_row[f] for f in range(nb) if d_ub[f]], dtype=bool).reshape(1, -1)

        for j in range(len(mdp[idx]["id"]["A"])):
            iaj = np.asarray(_unwrap_cell(mdp[idx]["id"]["A"][j]), dtype=np.float64).ravel()
            if np.any(np.isin(iaj.astype(np.int64), k_drop.astype(np.int64))):
                mdp[idx]["id"]["A"][j] = np.array([[float(c_orig)]], dtype=np.float64)
            else:
                pos = _find_ismember_positions_py(i_ub, iaj.astype(np.int64))
                mdp[idx]["id"]["A"][j] = np.asarray(pos, dtype=np.float64).reshape(1, -1)

    for n in range(nm):
        if "U" not in mdp[n]:
            nf = len(mdp[n]["B"])
            mdp[n]["U"] = np.zeros((1, nf), dtype=bool)

    for n in range(nm):
        for f in range(len(mdp[n]["B"])):
            if not bool(np.asarray(mdp[n]["U"], dtype=bool).ravel()[f]):
                continue
            b = _unwrap_cell(mdp[n]["B"][f])
            if callable(b):
                continue
            b_arr = np.asarray(b, dtype=bool if np.asarray(b).dtype == bool else np.float64)
            if b_arr.dtype == bool or np.issubdtype(b_arr.dtype, np.bool_):
                b_arr = np.asarray(b_arr, dtype=np.float64)
            b_arr = np.asarray(b_arr, dtype=np.float64)
            ns = int(b_arr.shape[1])
            nu = int(b_arr.shape[2]) if b_arr.ndim >= 3 else 1
            if nu > 1 and ns > 1:
                for u in range(nu):
                    for s in range(ns):
                        col = b_arr[:, s, u]
                        if not np.any(col):
                            slab = np.asarray(b_arr[:, s, :], dtype=np.float64)
                            row_any = np.any(np.asarray(slab, dtype=np.float64) > 0, axis=1)
                            i_pick = int(np.flatnonzero(row_any)[0])
                            b_arr[i_pick, s, u] = 1.0
                mdp[n]["B"][f] = b_arr

    fix_a = bool(FIX["A"])
    fix_b = bool(FIX["B"])

    for n in range(nm):
        ng = len(mdp[n]["A"])
        a_cells: list[Any] = [None] * ng
        for g in range(ng):
            ag = _unwrap_cell(mdp[n]["A"][g])
            if callable(ag):
                a_cells[g] = ag
            else:
                a_cells[g] = np.asarray(ag, dtype=np.float64) + float(p[n])

        nf = len(mdp[n]["B"])
        b_cells: list[Any] = [None] * nf
        for f in range(nf):
            bf = _unwrap_cell(mdp[n]["B"][f])
            if callable(bf):
                b_cells[f] = bf
            else:
                b_cells[f] = np.asarray(bf, dtype=np.float64) + float(q[n])

        if fix_a:
            mdp[n]["A"] = spm_dir_norm(copy.deepcopy(a_cells))
        else:
            mdp[n]["a"] = a_cells
            del mdp[n]["A"]

        if fix_b:
            mdp[n]["B"] = spm_dir_norm(copy.deepcopy(b_cells))
        else:
            mdp[n]["b"] = b_cells
            del mdp[n]["B"]

    try:
        if "id" in mdp[-1]:
            if "D" in mdp[-1]["id"]:
                del mdp[-1]["id"]["D"]
            if "E" in mdp[-1]["id"]:
                del mdp[-1]["id"]["E"]
    except Exception:
        pass

    sdp = copy.deepcopy(mdp[0])
    if "T" not in sdp:
        sdp["T"] = T
    sdp["L"] = 1
    out = sdp
    for n in range(2, nm + 1):
        rdp = copy.deepcopy(mdp[n - 1])
        rdp["MDP"] = out
        out = rdp
        out["T"] = T
        out["L"] = n
    out["L"] = nm
    return out


def _expand_param_nm(val, nm: int) -> np.ndarray:
    arr = np.asarray(val, dtype=np.float64).ravel(order="F")
    if arr.size >= nm:
        return arr[:nm].astype(np.float64)
    fill = float(arr.flat[0]) if arr.size else 0.0
    out = np.full(nm, fill, dtype=np.float64)
    if arr.size:
        out[: arr.size] = arr
    return out


def _find_ismember_positions_py(i_vec: np.ndarray, parents: np.ndarray) -> list[int]:
    i_vec = np.asarray(i_vec, dtype=np.int64).ravel()
    parents = np.asarray(parents, dtype=np.int64).ravel()
    out: list[int] = []
    for t in range(i_vec.size):
        if np.any(i_vec[t] == parents):
            out.append(t + 1)
    return out


def _remap_subordinate_de_py(i_vec: np.ndarray, sub: dict[str, Any]) -> None:
    i_vec = np.asarray(i_vec, dtype=np.int64).ravel()
    for j in range(len(sub["id"]["D"])):
        dj = np.asarray(_unwrap_cell(sub["id"]["D"][j]), dtype=np.int64).ravel()
        pos = _find_ismember_positions_py(i_vec, dj)
        sub["id"]["D"][j] = np.asarray(pos, dtype=np.float64).reshape(1, -1)
    for j in range(len(sub["id"]["E"])):
        ej = np.asarray(_unwrap_cell(sub["id"]["E"][j]), dtype=np.int64).ravel()
        pos = _find_ismember_positions_py(i_vec, ej)
        sub["id"]["E"][j] = np.asarray(pos, dtype=np.float64).reshape(1, -1)


def _unwrap_cell(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x
