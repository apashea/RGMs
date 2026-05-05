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
from python_src.toolbox.DEM.spm_induction import spm_induction as _spm_induction
from python_src.toolbox.DEM.spm_parents import spm_parents


def _spm_sample(p: Any) -> int:
    if isinstance(p, np.ndarray) and p.dtype == bool:
        flat = np.flatnonzero(p.ravel(order="F"))
        k = int(flat.size)
        if k == 0:
            raise ValueError("spm_sample: empty logical mask")
        # MATLAB spm_MDP_generate local spm_sample: logical P uses randperm(numel(i),1).
        # For MATLAB's twister default, randperm(k,1) selects index floor(k*r1)+1 using the
        # first rand() output r1 after reset; when 2<=k<=4 it also consumes a second rand()
        # so the stream stays aligned with replayed MATLAB rand() buffers.
        if k == 1:
            return int(flat[0] + 1)
        r1 = float(np.random.rand())
        if k <= 4:
            float(np.random.rand())
        pos = int(np.floor(r1 * k))
        if pos >= k:
            pos = k - 1
        return int(flat[pos] + 1)
    pv = np.asarray(p, dtype=np.float64).ravel(order="F")
    total = float(np.sum(pv))
    if (not np.isfinite(total)) or total <= 0.0 or (not np.all(np.isfinite(pv))):
        n = int(pv.size)
        if n <= 0:
            raise ValueError("spm_sample: empty numeric probability vector")
        pv = np.ones((n,), dtype=np.float64) / float(n)
    cs = np.cumsum(pv)
    r = float(np.random.rand())
    hit = np.flatnonzero(r < cs)
    if hit.size == 0:
        idx = int(pv.size) - 1
    else:
        idx = int(hit[0])
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
                ag = mdp["A"][g]
                for o in i_arr.tolist():
                    ind = [int(mdp["s"][jj - 1, t_idx - 1]) for jj in j_arr.tolist()]
                    sl = (slice(None),) + tuple(ii - 1 for ii in ind)
                    sub = ag[sl]
                    if sp.issparse(sub):
                        sub = sub.toarray()
                    col = np.asarray(sub)
                    col = np.reshape(col, (-1, 1), order="F")
                    o_cell[m][int(o) - 1][t_idx - 1] = col.astype(np.float64, copy=False)
                    sample_col = (
                        col if col.dtype == np.bool else col.astype(np.float64, copy=False)
                    )
                    mdp["o"][int(o) - 1, t_idx - 1] = _spm_sample(sample_col)

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
