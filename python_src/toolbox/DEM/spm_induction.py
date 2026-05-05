"""
Inductive inference about next state (MATLAB-compatible).

Translated from local ``spm_induction`` in ``spm_MDP_generate.m`` (Pass 1).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import scipy.sparse as sp

from python_src.spm_kron import spm_kron


def _q_posterior_entry(Q_item, idx_1based: int) -> float:
    """Posterior mass at 1-based state index (dense column or CSR column)."""
    if sp.issparse(Q_item):
        return float(Q_item[int(idx_1based) - 1, 0])
    qf = np.asarray(Q_item, dtype=np.float64).reshape(-1, order="F")
    return float(qf[int(idx_1based) - 1])


def _spm_shiftdim_m32(r_tensor: np.ndarray) -> np.ndarray:
    """MATLAB ``shiftdim(single(32*R), -1)`` layout used by ``spm_induction``."""
    x = np.asarray(r_tensor, dtype=np.float32)
    if x.ndim == 2:
        return np.reshape(x, (1, x.shape[0], x.shape[1]), order="C")
    if x.ndim == 3 and x.shape[-1] == 1:
        y = np.asarray(x[:, :, 0], dtype=np.float32)
        return np.reshape(y, (1, y.shape[0], y.shape[1]), order="C")
    if x.ndim == 1:
        return np.reshape(x, (1, x.size, 1), order="C")
    return x


def spm_induction(
    B: List[List[np.ndarray]],
    Q: List[sp.csr_matrix | np.ndarray],
    N: int,
    id_dict: dict,
) -> Tuple[Any, np.ndarray]:
    """
    FORMAT R, hif = spm_induction(B, Q, N, id)

    ``B`` mirrors MATLAB ``B(1,f,k)``: ``B[f][k]`` contains the transition for
    factor ``f`` and policy ``k``.
    """
    if "hid" in id_dict and id_dict["hid"] is not None:
        hid = np.asarray(id_dict["hid"], dtype=np.float64)
    else:
        hid = np.zeros((0, 0))

    if hid.size == 0:
        hif = np.zeros((0,), dtype=np.int64)
    else:
        hif = np.flatnonzero(np.any(hid != 0, axis=1)) + 1

    if "cid" in id_dict and id_dict["cid"] is not None and np.asarray(id_dict["cid"]).size > 0:
        cid = np.asarray(id_dict["cid"], dtype=np.float64)
        nid = cid.copy()
        hif = np.flatnonzero(np.all(cid != 0, axis=1)) + 1
        for f in hif.tolist():
            nid[int(f) - 1, :] = 0
        ns_list = [int(B[int(f) - 1][0].shape[0]) for f in hif.tolist()] + [1]
        ns_tuple = tuple(ns_list)
        d_tensor = np.ones(ns_tuple, dtype=bool)
        for i in range(cid.shape[1]):
            qv = 1.0
            for f0 in range(cid.shape[0]):
                if nid[f0, i] != 0:
                    f = f0 + 1
                    cidx = int(nid[f0, i])
                    qv = float(qv * _q_posterior_entry(Q[f - 1], cidx))
            if qv > (1.0 - 1.0 / 8.0):
                inds = [int(cid[int(f) - 1, i]) for f in hif.tolist()]
                lin = int(np.ravel_multi_index(tuple(x - 1 for x in inds), tuple(ns_list[:-1]), order="F"))
                d_tensor[np.unravel_index(lin, d_tensor.shape, order="F")] = False
        d_flat = d_tensor.reshape(-1, order="F")
    else:
        d_flat = None

    if hif.size == 0:
        return False, np.array([], dtype=np.int64)

    if hid.size == 0 or np.all(hid == 0):
        if d_flat is None:
            return False, hif.astype(np.int64)
        r32 = (32.0 * d_flat.astype(np.float32)).astype(np.float32)
        return r32, hif.astype(np.int64)

    u_thr = 1.0 / 16.0
    b_map: Dict[int, np.ndarray] = {}
    for f in hif.tolist():
        fi = int(f) - 1
        acc = None
        for k in range(len(B[fi])):
            bfk = np.asarray(B[fi][k], dtype=np.float64)
            mx = float(np.max(bfk))
            thr = bfk > (mx * u_thr)
            acc = thr if acc is None else (acc | thr)
        b_map[int(f)] = np.asarray(acc, dtype=bool)

    Bf = sp.csr_matrix([[1.0]], dtype=np.float64)
    Qf = sp.csr_matrix([[1.0]], dtype=np.float64)
    ns_by_f: Dict[int, int] = {}
    for f in hif.tolist():
        fi = int(f) - 1
        ns_by_f[int(f)] = int(B[fi][0].shape[0])
        Bf = spm_kron(b_map[int(f)], Bf)
        Qf = spm_kron(Q[fi], Qf)

    if d_flat is None:
        d_mul = np.ones(int(Bf.shape[0] * Bf.shape[1]), dtype=np.float64)
    else:
        if int(d_flat.size) != int(Bf.shape[0] * Bf.shape[1]):
            raise ValueError("spm_induction: D size mismatch with Bf")
        d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")

    bf_dense = Bf.toarray(order="F")
    bf_dense = bf_dense * d_mul.reshape(bf_dense.shape, order="F")
    Bf = sp.csr_matrix(bf_dense)

    hif_list = [int(x) for x in np.asarray(hif, dtype=np.int64).ravel(order="F")]
    ni_hid = int(hid.shape[1])
    pf_cols: List[np.ndarray] = []
    for i in range(ni_hid):
        h_vecs: Dict[int, np.ndarray] = {}
        for f in hif_list:
            nsf = ns_by_f[f]
            col = np.zeros((nsf, 1), dtype=bool)
            hfi = int(f) - 1
            idx = int(hid[hfi, i])
            if idx > 0:
                col[idx - 1, 0] = True
            h_vecs[f] = col
        acc = np.array([[True]], dtype=bool)
        for f in hif_list:
            acc = spm_kron(h_vecs[f], acc).toarray().astype(bool)
        pf_cols.append(acc.ravel(order="F"))

    l_dim = int(pf_cols[0].size)
    pf_mat = np.zeros((l_dim, ni_hid), dtype=bool)
    for i in range(ni_hid):
        pf_mat[:, i] = pf_cols[i]

    ncut = int(min(int(N), 16))
    g_mat = np.zeros((ncut + 1, ni_hid), dtype=np.float64)
    p_store: List[np.ndarray] = []
    qf_dense = Qf.toarray(order="F").ravel(order="F").reshape(-1, 1, order="F")

    for i in range(ni_hid):
        i_big = np.zeros((l_dim, ncut + 1), dtype=bool)
        i_big[:, 0] = pf_mat[:, i]
        for n in range(ncut):
            prev = i_big[:, n]
            if not np.any(prev):
                break
            rows = np.flatnonzero(prev)
            sub = Bf[rows, :]
            nxt = np.asarray(sub.sum(axis=0) > 0).ravel()
            i_big[:, n + 1] = nxt
        g_mat[:, i] = (i_big.astype(np.float64).T @ qf_dense).ravel()
        p_store.append(i_big.copy())

    g_mat[0, :] = 0.0
    dmx = np.max(g_mat, axis=0)
    nmx = np.argmax(g_mat, axis=0)
    mask = dmx > u_thr
    if not np.any(mask):
        return False, np.asarray(hif, dtype=np.int64)

    p_sel = [p_store[j] for j in range(ni_hid) if mask[j]]
    n_sel = nmx[mask]
    j0 = int(np.argmin(n_sel))
    p_use = p_sel[j0]
    n_use = int(n_sel[j0])
    col_idx = max(n_use - 1, 1) - 1
    p_vec = p_use[:, col_idx].astype(np.float64)
    ns_shape = [ns_by_f[f] for f in hif_list]
    r_body = p_vec.reshape(tuple(ns_shape), order="F").astype(np.float32)
    r_out = _spm_shiftdim_m32(32.0 * r_body)
    return r_out, np.asarray(hif, dtype=np.int64)

