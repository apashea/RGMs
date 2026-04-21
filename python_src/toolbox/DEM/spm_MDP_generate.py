"""
Active inference / generative roll-out for discrete MDPs (MATLAB-compatible).

Pass 1 transliteration of spm_MDP_generate.m including local helpers
`spm_sample`, `spm_norm`, and `spm_induction`.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import scipy.sparse as sp

from python_src.spm_combinations import spm_combinations
from python_src.spm_kron import spm_kron
from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_parents import spm_parents


def _spm_sample(p: Any) -> int:
    if isinstance(p, np.ndarray) and p.dtype == bool:
        flat = np.flatnonzero(p.ravel(order="F"))
        if flat.size == 0:
            raise ValueError("spm_sample: empty logical mask")
        # MATLAB `spm_sample`: i = find(P); i = i(randperm(numel(i),1));
        # `randperm(k,1)` consumes one uniform from the same RNG stream as `rand`.
        # Verified: equivalent to picking position `floor(k*rand)+1` among sorted `find(P)`.
        k = int(flat.size)
        pos = int(np.floor(float(np.random.rand()) * k))
        if pos >= k:
            pos = k - 1
        return int(flat[pos] + 1)
    pv = np.asarray(p, dtype=np.float64).ravel(order="F")
    cs = np.cumsum(pv)
    r = float(np.random.rand())
    idx = int(np.flatnonzero(r < cs)[0])
    return idx + 1


def _spm_norm(a: Any) -> np.ndarray:
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return a
    s = np.sum(a, axis=0, keepdims=True)
    out = np.divide(a, s, out=np.zeros_like(a, dtype=np.float64), where=s != 0)
    out = np.where(np.isnan(out), 1.0 / a.shape[0], out)
    return out


def _b_matrix_for_u(bf: np.ndarray, u_idx: int) -> np.ndarray:
    """MATLAB ``B(:,:,u)`` with trailing ``Nu=1`` folded to ``Ns×Ns`` in Python."""
    arr = np.asarray(bf, dtype=np.float64)
    if arr.ndim == 2:
        return arr
    return np.asarray(arr[:, :, int(u_idx) - 1], dtype=np.float64)


def _as_models(mdp_in: Union[dict, List[dict]]) -> List[dict]:
    if isinstance(mdp_in, dict):
        return [spm_MDP_checkX(copy.deepcopy(mdp_in))]
    if isinstance(mdp_in, list) and mdp_in and isinstance(mdp_in[0], dict):
        return [spm_MDP_checkX(copy.deepcopy(x)) for x in mdp_in]
    raise TypeError("spm_MDP_generate: MDP must be a dict or list of dicts")


def _spm_shiftdim_m32(r_tensor: np.ndarray) -> np.ndarray:
    """
    MATLAB `shiftdim(single(32*R), -1)` after `reshape(full(P), [Ns 1])`.

    Observed behavior (MATLAB R2024b): a 2-D state grid becomes `1 x Ns1 x Ns2`
    single; a trailing singleton `… x 1` is folded into the same layout.
    """
    x = np.asarray(r_tensor, dtype=np.float32)
    if x.ndim == 2:
        return np.reshape(x, (1, x.shape[0], x.shape[1]), order="C")
    if x.ndim == 3 and x.shape[-1] == 1:
        y = np.asarray(x[:, :, 0], dtype=np.float32)
        return np.reshape(y, (1, y.shape[0], y.shape[1]), order="C")
    if x.ndim == 1:
        return np.reshape(x, (1, x.size, 1), order="C")
    return x


def _spm_induction(
    B: List[List[np.ndarray]],
    Q: List[sp.csr_matrix],
    n_steps: int,
    idd: dict,
) -> Tuple[Any, np.ndarray]:
    """
    Local `spm_induction` from spm_MDP_generate.m (Pass 1).

    B mirrors MATLAB `BP(1,f,k)`: ``B[f][k]`` is the belief propagator for
    factor index ``f`` (0-based) and policy ``k``.

    Q[f] is a csr column (Ns_f, 1) posterior at the current time slice.
    """
    if "hid" in idd and idd["hid"] is not None:
        hid = np.asarray(idd["hid"], dtype=np.float64)
    else:
        hid = np.zeros((0, 0))

    if hid.size == 0:
        hif = np.zeros((0,), dtype=np.int64)
    else:
        hif = np.flatnonzero(np.any(hid != 0, axis=1)) + 1

    if "cid" in idd and idd["cid"] is not None and np.asarray(idd["cid"]).size > 0:
        cid = np.asarray(idd["cid"], dtype=np.float64)
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
                    qv = float(qv * Q[f - 1][cidx - 1, 0])
            if qv > (1.0 - 1.0 / 8.0):
                inds = [int(cid[int(f) - 1, i]) for f in hif.tolist()]
                lin = int(
                    np.ravel_multi_index(
                        tuple(x - 1 for x in inds), tuple(ns_list[:-1]), order="F"
                    )
                )
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

    ncut = int(min(int(n_steps), 16))
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


def spm_MDP_generate(mdp_in: Union[dict, List[dict]]) -> Union[dict, List[dict]]:
    models = _as_models(mdp_in)
    nm = len(models)
    t = int(models[0]["T"])
    ng = [len(models[m]["A"]) for m in range(nm)]
    nf = [len(models[m]["B"]) for m in range(nm)]
    no: List[List[int]] = []
    nu: List[List[int]] = []
    ns: List[List[int]] = []
    for m in range(nm):
        no.append([int(np.asarray(models[m]["A"][g]).shape[0]) for g in range(ng[m])])
        ns.append([int(np.asarray(models[m]["B"][f]).shape[0]) for f in range(nf[m])])
        nu.append(
            [
                int(
                    np.asarray(models[m]["B"][f]).shape[2]
                    if np.asarray(models[m]["B"][f]).ndim >= 3
                    else 1
                )
                for f in range(nf[m])
            ]
        )

    max_ng = max(ng) if ng else 0
    o_cell = [[[None for _ in range(t)] for _ in range(max_ng)] for _ in range(nm)]

    a: List[List[np.ndarray]] = [[None] * ng[m] for m in range(nm)]
    b: List[List[np.ndarray]] = [[None] * nf[m] for m in range(nm)]
    d: List[List[np.ndarray]] = [[None] * nf[m] for m in range(nm)]
    e: List[List[np.ndarray]] = [[None] * nf[m] for m in range(nm)]
    u_pol: List[np.ndarray] = []
    v_pol: List[np.ndarray] = []
    np_pol: List[int] = []
    id_list: List[dict] = []

    for m in range(nm):
        mdp = models[m]
        for g in range(ng[m]):
            a[m][g] = _spm_norm(np.asarray(mdp["A"][g], dtype=np.float64))
        for f in range(nf[m]):
            b[m][f] = _spm_norm(np.asarray(mdp["B"][f], dtype=np.float64))
            d[m][f] = _spm_norm(np.asarray(mdp["D"][f], dtype=np.float64))
            e[m][f] = _spm_norm(np.asarray(mdp["E"][f], dtype=np.float64))
        u_row = np.any(np.asarray(mdp["U"], dtype=np.float64), axis=0)
        k_list = np.flatnonzero(u_row) + 1
        nu_mk = [nu[m][int(i) - 1] for i in k_list.tolist()]
        u_mat = spm_combinations(np.asarray(nu_mk, dtype=np.float64))
        v = np.zeros((u_mat.shape[0], nf[m]), dtype=np.float64)
        for j, col in enumerate(k_list.tolist()):
            v[:, int(col) - 1] = u_mat[:, j]
        u_pol.append(u_row.astype(bool))
        v_pol.append(v)
        np_pol.append(int(v.shape[0]))
        s_new = np.zeros((nf[m], t), dtype=np.float64)
        try:
            s0 = np.asarray(mdp["s"], dtype=np.float64)
            if s0.shape == (nf[m], t):
                s_new[:, :] = s0
            else:
                s_flat = s0.ravel(order="F")
                for ii in np.flatnonzero(s_flat):
                    unr = np.unravel_index(int(ii), (nf[m], t), order="F")
                    s_new[unr] = s_flat[ii]
        except Exception:
            pass
        mdp["s"] = s_new
        u_new = np.zeros((nf[m], t), dtype=np.float64)
        try:
            u0 = np.asarray(mdp["u"], dtype=np.float64)
            if u0.shape == (nf[m], t):
                u_new[:, :] = u0
            else:
                u_flat = u0.ravel(order="F")
                for ii in np.flatnonzero(u_flat):
                    unr = np.unravel_index(int(ii), (nf[m], t), order="F")
                    u_new[unr] = u_flat[ii]
        except Exception:
            pass
        mdp["u"] = u_new
        mdp["o"] = np.zeros((ng[m], t), dtype=np.float64)
        id_list.append(copy.deepcopy(mdp["id"]))

    try:
        tau = max(float(models[-1].get("tau", 1.0)), 1.0)
    except Exception:
        tau = 1.0

    k_pol = [1 for _ in range(nm)]
    pk_list: List[np.ndarray] = []
    for m in range(nm):
        npm = np_pol[m]
        pk = (1.0 - 1.0 / tau) * np.eye(npm) + (1.0 / tau) / npm
        pk_list.append(_spm_norm(pk))

    g_prev = [np.zeros((np_pol[m], 1), dtype=np.float64) for m in range(nm)]

    for t_idx in range(1, t + 1):
        for m in range(nm):
            mdp = models[m]
            for f in range(nf[m]):
                if mdp["u"][f, t_idx - 1] == 0:
                    if t_idx > 1:
                        mdp["u"][f, t_idx - 1] = mdp["u"][f, t_idx - 2]
                    else:
                        pu = _spm_norm(e[m][f])
                        mdp["u"][f, t_idx - 1] = _spm_sample(pu)
            if t_idx > 1:
                if "hid" in id_list[m]:
                    k_pol[m] = _spm_sample(spm_softmax(g_prev[m]))
                else:
                    k_pol[m] = _spm_sample(pk_list[m][:, k_pol[m] - 1])
                for f in range(nf[m]):
                    if u_pol[m][f]:
                        mdp["u"][f, t_idx - 2] = v_pol[m][k_pol[m] - 1, f]
            for f in range(nf[m]):
                if mdp["s"][f, t_idx - 1] == 0:
                    if t_idx > 1:
                        bmat = _b_matrix_for_u(
                            b[m][f], int(mdp["u"][f, t_idx - 2])
                        )
                        ps = bmat[:, int(mdp["s"][f, t_idx - 2]) - 1]
                        ps = np.asarray(ps, dtype=np.float64).reshape(-1, 1, order="F")
                    else:
                        ps = d[m][f]
                    mdp["s"][f, t_idx - 1] = _spm_sample(ps)

        for m in range(nm):
            mdp = models[m]
            for g in range(ng[m]):
                j, i = spm_parents(id_list[m], g + 1, mdp["s"][:, t_idx - 1])
                i_arr = np.atleast_1d(np.asarray(i, dtype=np.float64)).astype(int).ravel()
                j_arr = np.atleast_1d(np.asarray(j, dtype=np.float64)).astype(int).ravel()
                ag = np.asarray(mdp["A"][g], dtype=np.float64)
                for o in i_arr.tolist():
                    ind = [int(mdp["s"][jj - 1, t_idx - 1]) for jj in j_arr.tolist()]
                    sl = (slice(None),) + tuple(ii - 1 for ii in ind)
                    col = np.asarray(ag[sl], dtype=np.float64).reshape(-1, order="F")
                    col = col.reshape(-1, 1, order="F")
                    o_cell[m][int(o) - 1][t_idx - 1] = col
                    mdp["o"][int(o) - 1, t_idx - 1] = _spm_sample(col)

        for m in range(nm):
            mdp = models[m]
            if "hid" in id_list[m]:
                g_line = np.zeros((np_pol[m], 1), dtype=np.float64)
                bp = [[None for _ in range(np_pol[m])] for _ in range(nf[m])]
                q_row: List[sp.csr_matrix] = []
                for f in range(nf[m]):
                    sf = int(mdp["s"][f, t_idx - 1])
                    q_row.append(
                        sp.csr_matrix(
                            ([1.0], ([sf - 1], [0])),
                            shape=(ns[m][f], 1),
                            dtype=np.float64,
                        )
                    )
                    for k in range(np_pol[m]):
                        if v_pol[m][k, f] != 0:
                            bp[f][k] = _b_matrix_for_u(
                                b[m][f], int(v_pol[m][k, f])
                            )
                        else:
                            bp[f][k] = _b_matrix_for_u(
                                b[m][f], int(mdp["u"][f, t_idx - 1])
                            )
                r_mat, r_fac = _spm_induction(bp, q_row, t - t_idx + 1, id_list[m])
                if r_mat is not False and np.any(
                    np.asarray(r_mat, dtype=np.float64).ravel()
                ):
                    p_map: Dict[Tuple[int, int], np.ndarray] = {}
                    fac_order = [
                        int(f) for f in np.asarray(r_fac, dtype=np.int64).ravel(order="F")
                    ]
                    for k in range(1, np_pol[m] + 1):
                        for ff in fac_order:
                            col = bp[ff - 1][k - 1][:, int(mdp["s"][ff - 1, t_idx - 1]) - 1]
                            p_map[(ff, k)] = np.asarray(col, dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                        cols_k = [p_map[(ff, k)] for ff in fac_order]
                        blk_k = np.asarray(cols_k[0], dtype=np.float64).reshape(
                            -1, 1, order="F"
                        )
                        for j in range(1, len(cols_k)):
                            pj = np.asarray(cols_k[j], dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                            blk_k = np.kron(blk_k, pj)
                        rv = (
                            np.asarray(r_mat, dtype=np.float64)
                            .ravel(order="F")
                            .reshape(1, -1)
                        )
                        g_line[k - 1, 0] = float(np.asarray(rv @ blk_k).squeeze())
                g_prev[m] = g_line.copy()

        for m in range(nm):
            mdp = models[m]
            mdp["T"] = t
            mdp["O"] = [[o_cell[m][g][tt] for tt in range(t)] for g in range(ng[m])]

    if isinstance(mdp_in, dict):
        return models[0]
    return models
