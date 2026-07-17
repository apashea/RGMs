"""Pass 1 transliteration of spm_mdp2rdp_a.m (Dirichlet MDP → nested RDP)."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_MDP_checkX import spm_mdp_normalize_rdp_matlab_containers


def spm_mdp2rdp_a(MDP: list[dict[str, Any]], p=None, q=None, T=None, FIX=None):
    """MATLAB ``RDP = spm_mdp2rdp_a(MDP,p,q,T,FIX)``."""
    if p is None:
        p = 0
    if q is None:
        q = 0
    if T is None:
        T = 2
    if FIX is None:
        FIX = {"A": True, "B": True}

    mdp = copy.deepcopy(MDP)
    nm = len(mdp)

    sb0 = np.asarray(mdp[0]["sB"], dtype=np.int64).ravel(order="F")
    ns_streams = int(np.max(sb0)) if sb0.size else 1
    p = _expand_param(p, ns_streams)
    q = _expand_param(q, ns_streams)

    if nm < 2:
        rdp = copy.deepcopy(mdp[0])
        rdp["L"] = 1
        rdp["T"] = T
        spm_mdp_normalize_rdp_matlab_containers(rdp)
        return rdp

    # --- trim trailing factors at last level (MATLAB n = Nm) ---
    n_last = nm - 1
    if len(mdp[n_last]["b"]) > 1:
        mdp[n_last]["b"] = [mdp[n_last]["b"][0]]
        if "G" in mdp[n_last]:
            mdp[n_last]["G"] = _matlab_index_one(mdp[n_last]["G"])
        if "sB" in mdp[n_last]:
            mdp[n_last]["sB"] = _matlab_index_one(mdp[n_last]["sB"])

        na = len(mdp[n_last]["a"])
        d_la = np.zeros(na, dtype=bool)
        for g in range(na):
            id_ag = np.asarray(_unwrap_cell(mdp[n_last]["id"]["A"][g]), dtype=np.float64).ravel()
            d_la[g] = not np.any(id_ag > 1)
        i_la = np.flatnonzero(d_la) + 1

        mdp[n_last]["a"] = [mdp[n_last]["a"][g] for g in range(na) if d_la[g]]
        mdp[n_last]["id"]["A"] = [mdp[n_last]["id"]["A"][g] for g in range(na) if d_la[g]]
        if "C" in mdp[n_last]:
            mdp[n_last]["C"] = [mdp[n_last]["C"][g] for g in range(na) if d_la[g]]

        _remap_subordinate_de(i_la, mdp[n_last - 1])

    # --- remove unitary mappings (MATLAB for n = flip(2:Nm)) ---
    for n_ml in range(nm, 1, -1):
        idx = n_ml - 1

        na = len(mdp[idx]["a"])
        d_ua = np.ones(na, dtype=bool)
        for g in range(na):
            ag = _unwrap_cell(mdp[idx]["a"][g])
            if callable(ag):
                continue
            ag_arr = np.asarray(ag, dtype=np.float64)
            if ag_arr.shape[0] < 2:
                d_ua[g] = False
        i_ua = np.flatnonzero(d_ua) + 1

        mdp[idx]["a"] = [mdp[idx]["a"][g] for g in range(na) if d_ua[g]]
        mdp[idx]["id"]["A"] = [mdp[idx]["id"]["A"][g] for g in range(na) if d_ua[g]]
        if "C" in mdp[idx]:
            mdp[idx]["C"] = [mdp[idx]["C"][g] for g in range(na) if d_ua[g]]
        if "sA" in mdp[idx]:
            mdp[idx]["sA"] = [mdp[idx]["sA"][g] for g in range(na) if d_ua[g]]
            mdp[idx]["sC"] = [mdp[idx]["sC"][g] for g in range(na) if d_ua[g]]

        _remap_subordinate_de(i_ua, mdp[idx - 1])

        nb = len(mdp[idx]["b"])
        d_ub = np.ones(nb, dtype=bool)
        for f in range(nb):
            bf = _unwrap_cell(mdp[idx]["b"][f])
            if callable(bf):
                continue
            if np.asarray(bf, dtype=np.float64).size == 1:
                d_ub[f] = False

        nz = np.flatnonzero(~d_ub)
        c_orig = int(nz[0]) + 1 if nz.size else 1
        d_ub[c_orig - 1] = True
        i_ub = np.flatnonzero(d_ub) + 1
        k_drop = np.flatnonzero(~d_ub) + 1

        mdp[idx]["b"] = [mdp[idx]["b"][f] for f in range(nb) if d_ub[f]]
        mdp[idx]["id"]["D"] = [mdp[idx]["id"]["D"][f] for f in range(nb) if d_ub[f]]
        mdp[idx]["id"]["E"] = [mdp[idx]["id"]["E"][f] for f in range(nb) if d_ub[f]]
        if "U" in mdp[idx]:
            u_row = np.asarray(mdp[idx]["U"], dtype=bool).ravel()
            mdp[idx]["U"] = np.array([u_row[f] for f in range(nb) if d_ub[f]], dtype=bool).reshape(1, -1)
        if "sB" in mdp[idx]:
            sb = mdp[idx]["sB"]
            if isinstance(sb, list):
                mdp[idx]["sB"] = [sb[f] for f in range(nb) if d_ub[f]]
            else:
                sb_arr = np.asarray(sb, dtype=np.int64).ravel()
                mdp[idx]["sB"] = [int(sb_arr[f]) for f in range(nb) if d_ub[f]]

        for j in range(len(mdp[idx]["id"]["A"])):
            iaj = np.asarray(_unwrap_cell(mdp[idx]["id"]["A"][j]), dtype=np.float64).ravel()
            if np.any(np.isin(iaj.astype(np.int64), k_drop.astype(np.int64))):
                mdp[idx]["id"]["A"][j] = np.array([[float(c_orig)]], dtype=np.float64)
            else:
                pos = _find_ismember_positions(i_ub, iaj.astype(np.int64))
                mdp[idx]["id"]["A"][j] = np.asarray(pos, dtype=np.float64).reshape(1, -1)

    for n in range(nm):
        if "U" not in mdp[n]:
            nf = len(mdp[n]["b"])
            mdp[n]["U"] = np.zeros((1, nf), dtype=bool)

    for n in range(nm):
        for f in range(len(mdp[n]["b"])):
            if not bool(np.asarray(mdp[n]["U"], dtype=bool).ravel()[f]):
                continue
            b = _unwrap_cell(mdp[n]["b"][f])
            if callable(b):
                continue
            b_arr = np.asarray(b, dtype=np.float64)
            ns = int(b_arr.shape[1])
            nu = int(b_arr.shape[2]) if b_arr.ndim >= 3 else 1
            if nu > 1 and ns > 1:
                for u in range(nu):
                    for s in range(ns):
                        col = b_arr[:, s, u]
                        if not np.any(col):
                            slab = np.asarray(b_arr[:, s, :], dtype=np.float64)
                            col_max = np.max(slab, axis=1)
                            j_val, i_lin = _matlab_max_twostep(col_max)
                            i_lin = int(i_lin)
                            b_arr[i_lin, s, u] = float(j_val)
                mdp[n]["b"][f] = b_arr

    fix_a = bool(FIX["A"])
    fix_b = bool(FIX["B"])

    for n in range(nm):
        if fix_a:
            ng = len(mdp[n]["a"])
            mdp[n]["A"] = [None] * ng
            for g in range(ng):
                ag = _unwrap_cell(mdp[n]["a"][g])
                if callable(ag):
                    continue
                mdp[n]["A"][g] = spm_dir_norm(np.asarray(ag, dtype=np.float64))
            del mdp[n]["a"]
        else:
            for g in range(len(mdp[n]["a"])):
                ag = _unwrap_cell(mdp[n]["a"][g])
                if callable(ag):
                    continue
                sc = mdp[n]["sC"]
                s_ix = int(sc[g]) - 1 if isinstance(sc, list) else int(np.asarray(sc).ravel()[g]) - 1
                mdp[n]["a"][g] = np.asarray(ag, dtype=np.float64) + float(p[s_ix])

        if fix_b:
            nf = len(mdp[n]["b"])
            mdp[n]["B"] = [None] * nf
            for f in range(nf):
                bf = _unwrap_cell(mdp[n]["b"][f])
                if callable(bf):
                    continue
                sb = mdp[n]["sB"]
                s_ix = int(sb[f]) - 1 if isinstance(sb, list) else int(np.asarray(sb).ravel()[f]) - 1
                b = np.asarray(bf, dtype=np.float64)
                mdp[n]["B"][f] = spm_dir_norm(b + float(q[s_ix]))
            del mdp[n]["b"]
        else:
            for f in range(len(mdp[n]["b"])):
                bf = _unwrap_cell(mdp[n]["b"][f])
                if callable(bf):
                    continue
                sb = mdp[n]["sB"]
                s_ix = int(sb[f]) - 1 if isinstance(sb, list) else int(np.asarray(sb).ravel()[f]) - 1
                mdp[n]["b"][f] = np.asarray(bf, dtype=np.float64) + float(q[s_ix])

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
    spm_mdp_normalize_rdp_matlab_containers(out)
    return out


def _matlab_max_twostep(col_max: np.ndarray):
    """MATLAB ``[j,i] = max(max(squeeze(b(:,s,:)),[],2));`` second max on column."""
    v = np.asarray(col_max, dtype=np.float64).ravel(order="F")
    if v.size == 0:
        return 0.0, 0
    j = float(np.max(v))
    i_lin = int(np.argmax(v))
    return j, i_lin


def _find_ismember_positions(i_vec: np.ndarray, parents: np.ndarray) -> list[int]:
    """MATLAB ``find(ismember(i, MDP.id.D{j}))`` — positions into ``i`` (1-based output list)."""
    i_vec = np.asarray(i_vec, dtype=np.int64).ravel()
    parents = np.asarray(parents, dtype=np.int64).ravel()
    out: list[int] = []
    for t in range(i_vec.size):
        if np.any(i_vec[t] == parents):
            out.append(t + 1)
    return out


def _remap_subordinate_de(i_vec: np.ndarray, sub: dict[str, Any]) -> None:
    """MATLAB ``find(ismember(i, ...))`` for id.D and id.E at level below."""
    i_vec = np.asarray(i_vec, dtype=np.int64).ravel()
    for j in range(len(sub["id"]["D"])):
        dj = np.asarray(_unwrap_cell(sub["id"]["D"][j]), dtype=np.int64).ravel()
        pos = _find_ismember_positions(i_vec, dj)
        sub["id"]["D"][j] = np.asarray(pos, dtype=np.float64).reshape(1, -1)
    for j in range(len(sub["id"]["E"])):
        ej = np.asarray(_unwrap_cell(sub["id"]["E"][j]), dtype=np.int64).ravel()
        pos = _find_ismember_positions(i_vec, ej)
        sub["id"]["E"][j] = np.asarray(pos, dtype=np.float64).reshape(1, -1)


def _expand_param(val, n_needed: int) -> np.ndarray:
    arr = np.asarray(val, dtype=np.float64).ravel(order="F")
    if arr.size >= n_needed:
        return arr[:n_needed].astype(np.float64)
    fill = float(arr.flat[0]) if arr.size else 0.0
    out = np.full(n_needed, fill, dtype=np.float64)
    if arr.size:
        out[: arr.size] = arr
    return out


def _matlab_index_one(x: Any) -> Any:
    """MATLAB ``x(1)`` on cell / struct-array group fields (e.g. ``G``, ``sB``)."""
    if isinstance(x, dict):
        if 1 in x:
            x = x[1]
        elif x:
            x = x[min(x.keys())]
    if isinstance(x, (list, tuple)) and len(x) >= 1:
        x = x[0]
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x


def _unwrap_cell(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x
