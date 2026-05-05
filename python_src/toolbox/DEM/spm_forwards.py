"""
Deep policy / path search and expected free energy (``spm_forwards`` from ``spm_MDP_VB_XXX.m``).

Pass 1 transliteration: MATLAB source is ``matlab_src/toolbox/DEM/spm_forwards.m`` (extracted
with local ``spm_induction(B,H,Q,N,id)`` and ``spm_children`` subfunctions).

``spm_figure`` branches in MATLAB ``spm_induction`` are omitted (``if false`` in source).
"""

from __future__ import annotations

from typing import Any, List, Sequence

import numpy as np
import scipy.sparse as sp

from matlab_compat import full as mfull
from python_src.spm_cross import spm_cross
from python_src.spm_dot import spm_dot
from python_src.spm_kron import spm_kron
from python_src.spm_log import spm_log
from python_src.spm_softmax import spm_softmax
from python_src.spm_vec import spm_vec
from python_src.toolbox.DEM.spm_MDP_BMR import spm_MDP_BMR
from python_src.toolbox.DEM.spm_index import spm_index
from python_src.toolbox.DEM.spm_parents import spm_parents
from python_src.toolbox.DEM.spm_VBX import spm_VBX


def spm_children(id_dict: dict) -> np.ndarray:
    """Local ``spm_children`` from ``spm_MDP_VB_XXX.m`` / ``spm_forwards.m``."""
    if "g" in id_dict:
        gcell = id_dict["g"]
        if "i" in id_dict:
            ii = int(np.asarray(id_dict["i"], dtype=np.int64).ravel()[0])
            gi = gcell[ii - 1]
            arr = np.atleast_1d(np.asarray(gi, dtype=np.int64).ravel())
            return arr.astype(np.int64).reshape(1, -1)
        flat = spm_vec(gcell)
        u = np.unique(np.asarray(flat, dtype=np.int64).ravel())
        return u.astype(np.int64).reshape(1, -1)
    na = len(id_dict["A"])
    return np.arange(1, na + 1, dtype=np.int64).reshape(1, -1)


def _numel(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, (list, tuple)):
        return len(x)
    return int(np.asarray(x, dtype=object).size)


def _cell_get_Qj(Q: list, j) -> list:
    jv = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
    return [Q[int(jj) - 1] for jj in jv.tolist()]


def _spm_induction_vb(
    B: List[List[np.ndarray]],
    H: list,
    Q: list,
    N: int,
    id_dict: dict,
) -> tuple[Any, np.ndarray]:
    """
    Local ``spm_induction(B,H,Q,N,id)`` from ``spm_MDP_VB_XXX.m`` (five arguments).
    """
    if "hid" in id_dict and id_dict["hid"] is not None:
        hid_m = id_dict["hid"]
        if callable(hid_m):
            raise NotImplementedError("spm_induction: id.hid function_handle not translated")
        hid_full = np.asarray(hid_m, dtype=np.float64)
        if hid_full.ndim < 2:
            # MATLAB may pass a **column** as a 1-D array; treat as ``Ns×1`` for ``any(...,1)`` over states.
            hid_full = np.reshape(hid_full, (-1, 1), order="F")
        hif = (np.flatnonzero(np.any(hid_full != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
        hid = hid_full
    else:
        hid_list: list[float] = []
        hif_list: list[int] = []
        for f in range(len(H)):
            Hf = H[f]
            if _numel(Hf) > 0:
                hf = np.asarray(mfull(Hf), dtype=np.float64).reshape(-1, order="F")
                s = int(np.argmax(hf) + 1)
                hid_list.append(float(s))
                hif_list.append(int(f + 1))
        if not hid_list:
            hid = np.zeros((0, 0), dtype=np.float64)
        else:
            hid = np.asarray(hid_list, dtype=np.float64).reshape(-1, 1)
        hif = np.asarray(hif_list, dtype=np.int64).reshape(1, -1)

    if "cid" in id_dict and id_dict["cid"] is not None:
        cid_raw = id_dict["cid"]
        if callable(cid_raw):
            raise NotImplementedError("spm_induction: id.cid function_handle not translated")
        cid_arr = np.asarray(cid_raw, dtype=np.float64)
        if cid_arr.size == 0:
            d_tensor = True
            d_flat = None
        else:
            cid = cid_arr
            nid = cid.copy()
            hif = (np.flatnonzero(np.all(cid != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
            for f in hif.ravel().tolist():
                nid[int(f) - 1, :] = 0
            ns_list = [int(B[int(f) - 1][0].shape[0]) for f in hif.ravel().tolist()] + [1]
            ns_tuple = tuple(ns_list)
            d_tensor = np.ones(ns_tuple, dtype=bool)
            for i in range(cid.shape[1]):
                qv = 1.0
                for f0 in range(cid.shape[0]):
                    if nid[f0, i] != 0:
                        f1 = f0 + 1
                        cidx = int(nid[f0, i])
                        qcol = np.asarray(Q[f1 - 1], dtype=np.float64).reshape(-1, order="F")
                        qv *= float(qcol[cidx - 1])
                if qv > (1.0 - 1.0 / 8.0):
                    inds = [int(cid[int(f) - 1, i]) for f in hif.ravel().tolist()]
                    lin = int(np.ravel_multi_index(tuple(x - 1 for x in inds), tuple(ns_list[:-1]), order="F"))
                    d_tensor[np.unravel_index(lin, d_tensor.shape, order="F")] = False
            d_flat = d_tensor.reshape(-1, order="F")
    else:
        d_tensor = True
        d_flat = None

    hif_list = [int(x) for x in np.asarray(hif, dtype=np.int64).ravel().tolist()]
    hid = np.asarray(hid, dtype=np.float64)
    if hid.ndim == 2 and hid.shape[0] > len(hif_list) and len(hif_list) > 0:
        hid = hid[np.asarray(hif_list, dtype=int) - 1, :]

    if len(hif_list) == 0:
        return np.array([]), np.array([], dtype=np.int64)
    if hid.size == 0 or np.all(hid == 0):
        if d_tensor is True:
            return np.array([]), np.asarray(hif_list, dtype=np.int64)
        r32 = (32.0 * np.asarray(d_flat, dtype=np.float32).ravel(order="F")).astype(np.float32)
        return r32, np.asarray(hif_list, dtype=np.int64)

    N = int(min(int(N), 64))
    if "D" in id_dict and N < 4:
        N = 64
    if N <= 0:
        return np.array([]), np.asarray(hif_list, dtype=np.int64)

    u_thr = 1.0 / 32.0
    if not B or len(B) == 0:
        return np.array([]), np.array([], dtype=np.int64)
    nk = len(B[0])
    if nk == 0:
        return np.array([]), np.array([], dtype=np.int64)
    b_map: dict[int, np.ndarray] = {}
    for f in hif_list:
        if f < 1 or f > len(B) or len(B[f - 1]) == 0:
            continue
        acc = None
        nk_f = len(B[f - 1])
        for k in range(min(nk, nk_f)):
            try:
                bfk = np.asarray(B[f - 1][k], dtype=np.float64)
            except Exception:
                bfk = np.asarray(B[f - 1][0], dtype=np.float64)
            thr = bfk > u_thr
            acc = thr if acc is None else (acc | thr)
        if acc is None:
            continue
        b_map[f] = np.asarray(acc, dtype=bool)
    if not b_map:
        return np.array([]), np.array([], dtype=np.int64)
    hif_kept = [f for f in hif_list if f in b_map]

    hid = np.asarray(hid, dtype=np.float64)
    if hid.ndim == 2 and len(hif_kept) > 0:
        idx_kept = [hif_list.index(f) for f in hif_kept]
        hid = hid[np.asarray(idx_kept, dtype=int), :]

    Bf = sp.csr_matrix([[1.0]], dtype=np.float64)
    Qf = sp.csr_matrix([[1.0]], dtype=np.float64)
    ns_by_pos: list[int] = []
    for f in hif_kept:
        ns_by_pos.append(int(B[f - 1][0].shape[0]))
        Bf = spm_kron(b_map[f], Bf)
        Qcol = np.asarray(Q[f - 1], dtype=np.float64).reshape(-1, 1, order="F")
        Qf = spm_kron(sp.csr_matrix(Qcol), Qf)

    if d_flat is None:
        d_mul = np.ones(int(Bf.shape[0] * Bf.shape[1]), dtype=np.float64)
    else:
        d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")
        if d_mul.size != int(Bf.shape[0] * Bf.shape[1]):
            raise ValueError("spm_induction: D size mismatch with Bf")
    bf_dense = Bf.toarray(order="F")
    bf_dense = bf_dense * d_mul.reshape(bf_dense.shape, order="F")
    Bf = sp.csr_matrix(bf_dense)

    hid_arr = np.asarray(hid, dtype=np.float64)
    if hid_arr.ndim == 1:
        hid_arr = hid_arr.reshape(-1, 1)
    nh = int(hid_arr.shape[1])
    pf_cols: list[np.ndarray] = []
    for i in range(nh):
        I = np.array([[True]], dtype=bool)
        for pos, f in enumerate(hif_kept):
            nsf = ns_by_pos[pos]
            hvec = np.zeros((nsf, 1), dtype=bool)
            hidx = int(hid_arr[pos, i])
            if hidx > 0:
                hvec[hidx - 1, 0] = True
            I = spm_kron(hvec, I).toarray().astype(bool)
        pf_cols.append(I.ravel(order="F"))

    l_dim = int(pf_cols[0].size)
    Pf = np.zeros((l_dim, nh), dtype=bool)
    for i in range(nh):
        Pf[:, i] = pf_cols[i]

    G = np.zeros((N, nh), dtype=np.float64)
    p_store: list[np.ndarray] = []
    qf_dense = Qf.toarray(order="F").ravel(order="F").reshape(-1, 1, order="F")

    for i in range(nh):
        I = np.asarray(Pf[:, i], dtype=bool).reshape(-1, 1)
        ncols = N + 1
        I_big = np.zeros((I.shape[0], ncols), dtype=bool)
        I_big[:, 0] = I.ravel()
        for n in range(N):
            prev = I_big[:, n]
            if not np.any(prev):
                break
            rows = np.flatnonzero(prev)
            sub = Bf[rows, :]
            nxt = np.asarray(sub.sum(axis=0) > 0).ravel()
            I_big[:, n + 1] = nxt
        vec = (I_big.astype(np.float64).T @ qf_dense).ravel(order="F")
        nvec = int(vec.size)
        take = int(min(N, nvec))
        G[:take, i] = vec[:take]
        p_store.append(I_big.copy())

    G[0, :] = 0.0
    dmx = np.max(G, axis=0)
    nmx = np.argmax(G, axis=0)
    mask = dmx > u_thr
    if not np.any(mask):
        return np.array([]), np.asarray(hif_kept, dtype=np.int64)

    p_sel = [p_store[j] for j in range(nh) if mask[j]]
    n_sel = nmx[mask]
    j0 = int(np.argmin(n_sel))
    p_use = p_sel[j0]
    n_use = int(n_sel[j0])
    col_idx = max(n_use - 1, 1) - 1
    p_vec = p_use[:, col_idx].astype(np.float64)
    ns_shape = tuple(ns_by_pos)
    r_body = p_vec.reshape(ns_shape, order="F").astype(np.float32)
    if d_tensor is True:
        d_reshape = np.ones(r_body.shape, dtype=bool)
    else:
        d_reshape = np.asarray(d_tensor, dtype=bool).reshape(ns_shape, order="F")
    R = 32.0 * np.logical_and(r_body.astype(bool), d_reshape.astype(bool)).astype(np.float32)
    return R, np.asarray(hif_kept, dtype=np.int64)


def spm_forwards(
    O: list,
    P: list,
    A: list,
    B: list,
    C: list,
    H: list,
    K: list,
    W: list,
    I: list,
    t: int,
    T: int,
    N: int,
    m: int,
    id_list: list,
    pA: list,
    qa: Any | None = None,
) -> tuple[np.ndarray, Any, float, list, dict]:
    """
    FORMAT G, P, F, id, Pa = spm_forwards(O,P,A,B,C,H,K,W,I,t,T,N,m,id,pA,qa)

    ``m``, ``t``, ``T``, ``N`` use **1-based** time / horizon conventions matching MATLAB.
    ``O{m,g,t}`` / ``P{m,f,t}`` are indexed as ``O[m-1][g-1][t-1]`` in Python storage.
    """
    mi = int(m) - 1
    idm = id_list[mi]
    Ni = len(idm["g"])
    nk = len(B[mi][0])
    nf = len(B[mi])
    G = np.zeros((nk, Ni), dtype=np.float64)
    Pa: dict[int, Any] = {}

    O_row = [O[mi][g][t - 1] for g in range(len(O[mi]))]
    P_row = [P[mi][f][t - 1] for f in range(len(P[mi]))]
    A_row = A[mi]
    Q_upd, F = spm_VBX(O_row, P_row, A_row, idm)
    for f in range(len(Q_upd)):
        P[mi][f][t - 1] = Q_upd[f]

    if t > T or (nk * Ni == 1):
        return G, P, float(F), id_list, Pa

    B_slice = B[mi]
    H_slice = H[mi]
    P_now = [P[mi][f][t - 1] for f in range(nf)]
    R, r = _spm_induction_vb(B_slice, H_slice, P_now, int(T - t), idm)
    if np.asarray(R).size and np.asarray(R).ndim >= 1:
        Rv = np.asarray(R, dtype=np.float64)
        if Rv.ndim == 1 or (Rv.ndim == 2 and min(Rv.shape) == 1):
            Rv = Rv.reshape(1, -1)
        R = Rv

    Qp: list[Any] = [None] * nf
    id_fp = np.asarray(idm.get("fp", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    for f in id_fp.tolist():
        Bf1 = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
        Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
        Qp[int(f) - 1] = Bf1 @ Pf

    id_fu = np.asarray(idm.get("fu", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_iH = np.asarray(idm.get("iH", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_iI = np.asarray(idm.get("iI", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()

    for k in range(nk):
        for f in id_fu.tolist():
            Bfk = np.asarray(B_slice[int(f) - 1][k], dtype=np.float64)
            Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Qp[int(f) - 1] = Bfk @ Pf

        for f in id_iH.tolist():
            Qf = np.asarray(Qp[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Hf = np.asarray(H_slice[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            G[k, :] -= float((Qf.T @ (spm_log(Qf) - spm_log(Hf))).reshape(-1)[0])

        for f in id_iI.tolist():
            Pmf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(1, -1, order="F")
            Iblk = np.asarray(I[mi][int(f) - 1][k], dtype=np.float64)
            Qf = np.asarray(Qp[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            G[k, :] += float(Pmf @ Iblk @ Qf)

        if _numel(R) > 0:
            q_cells = _cell_get_Qj(Qp, r)
            g_risk = np.asarray(spm_dot(R, q_cells), dtype=np.float64).reshape(-1)
            if g_risk.size == 1:
                G[k, :] += float(g_risk[0])
            elif g_risk.size == Ni:
                G[k, :] += g_risk
            else:
                # Fallback for unexpected shapes: keep run alive using the leading entry.
                G[k, :] += float(g_risk[0])

        No = np.zeros((1, Ni), dtype=np.float64)
        for i_cov in range(Ni):
            gi = idm["g"][i_cov]
            if "ge" in idm:
                ge = np.asarray(idm["ge"], dtype=np.int64).ravel()
                gi = np.array([x for x in np.atleast_1d(np.asarray(gi).ravel()) if x in set(ge.tolist())], dtype=np.int64)
            for ig in np.atleast_1d(np.asarray(gi, dtype=np.int64).ravel()):
                j, gg = spm_parents(idm, int(ig), Qp)
                for g in np.atleast_1d(np.asarray(gg, dtype=np.int64).ravel()):
                    Amg = A[mi][int(g) - 1]
                    qj = _cell_get_Qj(Qp, j)
                    if callable(Amg):
                        raise NotImplementedError("spm_forwards: A{m,g} function_handle not translated")
                    qo = np.asarray(spm_dot(Amg, qj), dtype=np.float64).reshape(-1, 1, order="F")
                    No[0, i_cov] += float(
                        np.asarray(spm_log(np.array([[float(np.size(qo))]], dtype=np.float64)), dtype=np.float64).reshape(-1)[0]
                    )
                    G[k, i_cov] -= float((qo.T @ spm_log(qo)).reshape(-1)[0])
                    Cmg = C[mi][int(g) - 1]
                    if _numel(Cmg) > 0:
                        c_cells = idm.get("C", [])
                        cg = None
                        if isinstance(c_cells, (list, tuple)) and len(c_cells) >= int(g):
                            cg = c_cells[int(g) - 1]
                        if cg is not None and _numel(cg) > 0:
                            fC = int(np.asarray(cg, dtype=np.int64).ravel()[0])
                            U = np.asarray(
                                spm_dot(spm_log(np.asarray(Cmg, dtype=np.float64)), Qp[int(fC) - 1]),
                                dtype=np.float64,
                            ).reshape(-1, 1, order="F")
                        else:
                            U = np.asarray(spm_log(np.asarray(Cmg, dtype=np.float64)), dtype=np.float64).reshape(-1, 1, order="F")
                        G[k, i_cov] += float((qo.T @ U).reshape(-1)[0])
                    Kmg = K[mi][int(g) - 1]
                    if _numel(Kmg) > 0:
                        G[k, i_cov] += float(np.asarray(spm_dot(Kmg, qj), dtype=np.float64).reshape(-1)[0])
                    Wmg = W[mi][int(g) - 1]
                    if _numel(Wmg) > 0:
                        G[k, i_cov] += float((qo.T @ np.asarray(spm_dot(Wmg, qj), dtype=np.float64).reshape(-1, 1)).reshape(-1)[0])
                    pAg = pA[mi][int(g) - 1]
                    if _numel(pAg) > 0:
                        if qa is None:
                            raise ValueError("spm_forwards: qa required when pA is non-empty")
                        da = spm_cross(qo, qj)
                        Pa[int(g)] = spm_MDP_BMR(np.asarray(qa[mi][int(g) - 1], dtype=np.float64), pAg)
                        Pg = spm_MDP_BMR(np.asarray(qa[mi][int(g) - 1], dtype=np.float64) + np.asarray(da, dtype=np.float64), pAg)
                        pal = np.asarray(Pa[int(g)], dtype=np.float64).reshape(-1, 1, order="F")
                        pgl = np.asarray(Pg, dtype=np.float64).reshape(-1, 1, order="F")
                        G[k, i_cov] += float((pgl.T @ (spm_log(pgl) - spm_log(pal))).reshape(-1)[0])
                    else:
                        Pa[int(g)] = {}

    G = G + No
    if "i" in idm:
        col_max = np.max(G, axis=0)
        i_sel = int(np.argmax(col_max) + 1)
        G = G[:, i_sel - 1 : i_sel]
        idm["i"] = i_sel
    else:
        G = np.sum(G, axis=1, keepdims=True)
        i_sel = 1

    if t < N:
        ng = len(pA[mi])
        pA[mi] = [None] * ng
        ig = idm["g"][i_sel - 1]
        ig = np.atleast_1d(np.asarray(ig, dtype=np.int64).ravel())
        u = np.asarray(spm_softmax(G), dtype=np.float64)
        mxu = float(np.max(u)) / 16.0
        k_plausible = u > mxu
        G = np.asarray(G, dtype=np.float64)
        G = np.where(k_plausible, G, float(np.max(G) - 512.0))

        for k in range(nk):
            if not bool(np.asarray(k_plausible, dtype=bool).reshape(-1)[k]):
                continue
            for f in id_fu.tolist():
                Bfk = np.asarray(B_slice[int(f) - 1][k], dtype=np.float64)
                Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
                Qp[int(f) - 1] = Bfk @ Pf

            j_acc: list[int] = []
            for g in ig.tolist():
                j1, _ = spm_parents(idm, int(g), Qp)
                j1a = np.unique(np.atleast_1d(np.asarray(j1, dtype=np.int64).ravel())).tolist()
                j_acc = sorted(set(j_acc + [int(x) for x in j1a]))
            j = np.asarray(j_acc, dtype=np.int64)

            s_list: list[np.ndarray] = []
            S_list: list[np.ndarray] = []
            n_list: list[int] = []
            for jf in j.tolist():
                Qjf = np.asarray(Qp[int(jf) - 1], dtype=np.float64).reshape(-1, order="F")
                s_idx = np.flatnonzero(Qjf > np.exp(-8.0)) + 1
                s_list.append(s_idx.astype(np.int64))
                S_list.append(Qjf[s_idx - 1].reshape(-1, 1, order="F"))
                n_list.append(int(s_idx.size))

            q = spm_cross(S_list)
            q = np.asarray(q, dtype=np.float64).reshape(tuple(n_list) + (1,), order="F")
            flat = q.ravel(order="F").copy()
            order_idx = np.argsort(-flat)
            if flat.size > 4:
                flat[order_idx[4:]] = 0.0
            zs = float(np.sum(flat))
            if zs > 0:
                flat = flat / zs
            q = flat.reshape(q.shape, order="F")
            EFE = np.zeros_like(q, dtype=np.float64)
            for ii_lin in range(int(q.size)):
                if float(flat[ii_lin]) == 0.0:
                    continue
                ind = spm_index(np.asarray(q.shape, dtype=float).reshape(-1), float(ii_lin + 1))
                ind_arr = np.asarray(ind, dtype=np.int64).ravel()
                fi = np.zeros(nf, dtype=np.int64)
                for pos, jf in enumerate(j.tolist()):
                    fi[int(jf) - 1] = int(s_list[pos][int(ind_arr[pos]) - 1])
                for g in ig.tolist():
                    fac, gg = spm_parents(idm, int(g), Qp)
                    ind_cell = [int(fi[int(ff) - 1]) for ff in np.atleast_1d(np.asarray(fac, dtype=np.int64).ravel())]
                    Amg = A[mi][int(g) - 1]
                    for o in np.atleast_1d(np.asarray(gg, dtype=np.int64).ravel()):
                        if callable(Amg):
                            raise NotImplementedError("spm_forwards: function_handle A in recursion")
                        sl = tuple(slice(int(x - 1), int(x)) for x in ind_cell)
                        if Amg.ndim == len(ind_cell) + 1:
                            col = np.asarray(Amg[(slice(None),) + sl], dtype=np.float64).reshape(-1, 1, order="F")
                        else:
                            col = np.asarray(Amg[sl], dtype=np.float64).reshape(-1, 1, order="F")
                        O[mi][int(o) - 1][t] = col
                for f in range(nf):
                    P[mi][f][t] = Qp[f]
                E = spm_forwards(O, P, A, B, C, H, K, W, I, t + 1, T, N, m, id_list, pA, qa)[0]
                Es = np.asarray(spm_softmax(E), dtype=np.float64).reshape(-1, 1, order="F")
                Ea = np.asarray(E, dtype=np.float64).reshape(-1, 1, order="F")
                EFE.ravel(order="F")[ii_lin] = float((Es.T @ Ea).reshape(-1)[0])

            G[k, 0] += float(np.sum(EFE * q))

    return G, P, float(F), id_list, Pa


__all__ = ["spm_forwards", "spm_children"]
