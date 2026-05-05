"""
``spm_backwards`` — local function from ``spm_MDP_VB_XXX.m`` (staged as free function).

Backwards / smoothing pass for variational posteriors. Pass 1 transliteration;
MATLAB: ``matlab_src/toolbox/DEM/spm_backwards.m`` (extracted) / ``spm_MDP_VB_XXX.m`` ~2081–2332.
"""

from __future__ import annotations

import copy
import warnings
from typing import Any

import numpy as np
from scipy import sparse

from matlab_compat import full as mfull, matlab_size
from python_src.spm_cross import spm_cross
from python_src.spm_dot import spm_dot
from python_src.spm_log import spm_log
from python_src.spm_psi import spm_psi
from python_src.spm_softmax import spm_softmax
from python_src.spm_vec import spm_vec
from python_src.toolbox.DEM.spm_forwards import spm_children
from python_src.toolbox.DEM.spm_parents import spm_parents


def _pagetranspose(a: Any) -> np.ndarray:
    a = np.asarray(mfull(a), dtype=np.float64)
    if a.ndim <= 2:
        return np.ascontiguousarray(a.T)
    # MATLAB pagetranspose swaps the first two dims on each page.
    return np.swapaxes(a, 0, 1)


def _spm_norm(a: Any) -> Any:
    if sparse.issparse(a):
        a = np.asarray(mfull(a), dtype=np.float64)
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return a
    s = np.sum(a, axis=0, keepdims=True)
    out = np.divide(a, s, out=np.zeros_like(a, dtype=np.float64), where=s != 0)
    out = np.where(np.isnan(out), 1.0 / a.shape[0], out)
    return out


def _unique_stable(j: np.ndarray) -> np.ndarray:
    jv = np.asarray(j, dtype=np.int64).ravel()
    seen: set[int] = set()
    out: list[int] = []
    for v in jv.tolist():
        if int(v) not in seen:
            seen.add(int(v))
            out.append(int(v))
    return np.array(out, dtype=np.int64).reshape(1, -1)


def _numel_qb_row(qb: list, mi: int) -> int:
    row = qb[mi]
    if isinstance(row, list):
        return len(row)
    return int(np.asarray(row, dtype=object).size)


def _Q_row_m_t(Q: list, mi: int, t_m: int) -> list:
    ti = t_m - 1
    return [Q[mi][f][ti] for f in range(len(Q[mi]))]


def _sdot_mtimes_q(s_dot_p: Any, q_next: np.ndarray) -> np.ndarray:
    """MATLAB ``spm_dot(spm_psi(tr(qb)),P(m,f,t))*Q{m,f,t+1}`` as matrix multiply → column."""
    a = np.asarray(mfull(s_dot_p), dtype=np.float64)
    b = np.asarray(q_next, dtype=np.float64).reshape(-1, 1, order="F")
    if a.ndim == 2 and a.shape[1] == b.shape[0]:
        return np.asarray((a @ b).reshape(-1, 1), dtype=np.float64, order="F")
    if a.size == b.size:
        return (a.reshape(-1, 1) * b.reshape(-1, 1)).astype(np.float64)
    return (np.asarray(a).reshape(-1, 1) * b.reshape(-1, 1)).astype(np.float64)


def spm_backwards(
    O: list,
    P: list,
    Q: list,
    D: list,
    E: list,
    pa: list,
    pb: list,
    U: list,
    m: int,
    id_list: list,
) -> tuple[list, list, list, list, np.ndarray]:
    """
    FORMAT ``[Q,P,qa,qb,F] = spm_backwards(O,P,Q,D,E,pa,pb,U,m,id)``.

    ``m`` is **1-based** (MATLAB). Cells: ``O[m][g][t]``, ``Q[m][f][t]``, ``P[m][f][t]``,
    ``D[m][f]``, ``E[m][f]``, ``pa[m][g]``, ``pb[m][f]``, ``U[m]`` vector length ``Nf``.
    """
    mi = int(m) - 1
    idm = id_list[mi]
    tr = _pagetranspose

    Nf = len(Q[mi])
    T = len(Q[mi][0])

    Z = -np.inf
    F_out = np.zeros(T, dtype=np.float64)

    for _v in range(16):
        F = np.zeros(T, dtype=np.float64)
        qa = copy.deepcopy(pa)
        qb = copy.deepcopy(pb)

        # Accumulate posterior Dirichlet parameters (matches MATLAB ~2122–2141)
        for t_m in range(1, T + 1):
            ti = t_m - 1
            Qrow = _Q_row_m_t(Q, mi, t_m)

            for g in np.ravel(spm_children(idm)).tolist():
                g = int(g)
                j, i_ch = spm_parents(idm, g, Qrow)
                for o in np.atleast_1d(np.asarray(i_ch)).ravel():
                    o = int(o)
                    Omot = O[mi][o - 1][ti]
                    jv = np.atleast_1d(np.asarray(j)).ravel()
                    acc = spm_cross(Omot, _cell_get_Qjt(Q, mi, jv, ti))
                    qa[mi][g - 1] = np.asarray(qa[mi][g - 1], dtype=np.float64) + np.asarray(
                        acc, dtype=np.float64
                    )
                    pa_mg = np.asarray(pa[mi][g - 1], dtype=np.float64)
                    qa[mi][g - 1] = qa[mi][g - 1] * (pa_mg > 0)

            if t_m < T:
                nqb = _numel_qb_row(qb, mi)
                for f_1 in range(1, nqb + 1):
                    fi = f_1 - 1
                    acc = spm_cross(
                        spm_cross(Q[mi][fi][ti + 1], Q[mi][fi][ti]),
                        P[mi][fi][ti],
                    )
                    qb[mi][fi] = np.asarray(qb[mi][fi], dtype=np.float64) + np.asarray(
                        acc, dtype=np.float64
                    )
                    pb_mf = np.asarray(pb[mi][fi], dtype=np.float64)
                    qb[mi][fi] = qb[mi][fi] * (pb_mf > 0)

        # Inference over time (~2147–2258)
        for t_m in range(1, T + 1):
            ti = t_m - 1
            Qrow = _Q_row_m_t(Q, mi, t_m)

            if isinstance(idm, dict) and "independent" in idm:
                Lcell: list[Any] = [0.0] * Nf
                for g in np.ravel(spm_children(idm)).tolist():
                    g = int(g)
                    j, k = spm_parents(idm, g, Qrow)
                    j = _unique_stable(np.asarray(j, dtype=np.int64))
                    LL = None
                    for o in np.atleast_1d(np.asarray(k)).ravel():
                        o = int(o)
                        Omot = O[mi][o - 1][ti]
                        qa_mg = _spm_norm(qa[mi][g - 1])
                        dot_v = spm_dot(qa_mg, Omot)
                        logv = np.asarray(spm_log(dot_v), dtype=np.float64)
                        LL = logv if LL is None else (LL + logv)
                    for jj in np.atleast_1d(j).ravel():
                        idx = int(jj) - 1
                        if isinstance(Lcell[idx], float):
                            Lcell[idx] = np.asarray(LL, dtype=np.float64)
                        else:
                            Lcell[idx] = np.asarray(Lcell[idx], dtype=np.float64) + np.asarray(LL, dtype=np.float64)

                nqb = _numel_qb_row(qb, mi)
                f_last = nqb

                for _ii in range(1, Nf + 1):
                    Lf0 = np.asarray(Lcell[f_last - 1], dtype=np.float64)
                    Lf = Lf0.reshape(-1, 1, order="F")
                    dD = D[mi][f_last - 1]
                    n_s = int(np.asarray(dD, dtype=np.float64).shape[0])
                    LPv = np.zeros((n_s, 1), dtype=np.float64)
                    if t_m == 1:
                        LPv = LPv + np.asarray(spm_log(D[mi][f_last - 1]), dtype=np.float64).reshape(
                            -1, 1, order="F"
                        )
                    if t_m < T:
                        qbf = np.asarray(qb[mi][f_last - 1], dtype=np.float64)
                        Pmft = P[mi][f_last - 1][ti]
                        Qn = Q[mi][f_last - 1][ti + 1]
                        tdot = spm_dot(spm_psi(tr(qbf)), Pmft)
                        LPv = LPv + _sdot_mtimes_q(tdot, np.asarray(Qn, dtype=np.float64))
                    if t_m > 1:
                        qbf = np.asarray(qb[mi][f_last - 1], dtype=np.float64)
                        Pprev = P[mi][f_last - 1][ti - 1]
                        Qp = Q[mi][f_last - 1][ti - 1]
                        tdot = spm_dot(spm_psi(qbf), Pprev)
                        LPv = LPv + _sdot_mtimes_q(tdot, np.asarray(Qp, dtype=np.float64))

                    sm_in = Lf + LPv
                    Q[mi][f_last - 1][ti] = spm_softmax(np.asarray(sm_in, dtype=np.float64))
                    q_post = np.asarray(Q[mi][f_last - 1][ti], dtype=np.float64).reshape(-1, 1)
                    logq = spm_log(q_post)
                    F[ti] = F[ti] + float(np.sum(q_post * (sm_in - logq)))

            else:
                L = np.asarray(0.0, dtype=np.float64)
                for g in np.ravel(spm_children(idm)).tolist():
                    g = int(g)
                    j, k = spm_parents(idm, g, Qrow)
                    j = _unique_stable(np.asarray(j, dtype=np.int64))
                    LL = None
                    for o in np.atleast_1d(np.asarray(k)).ravel():
                        o = int(o)
                        Omot = O[mi][o - 1][ti]
                        qa_mg = _spm_norm(qa[mi][g - 1])
                        dot_v = spm_dot(qa_mg, Omot)
                        logv = np.asarray(spm_log(dot_v), dtype=np.float64)
                        LL = logv if LL is None else (LL + logv)
                    jv = np.asarray(j, dtype=np.int64).ravel()
                    if jv.size > 1:
                        order = np.argsort(jv, kind="mergesort")
                        jv = jv[order]
                        perm_axes = (order + 1).tolist()
                        LL = np.transpose(np.asarray(LL, dtype=np.float64), np.asarray(perm_axes) - 1)
                    sz_ll = matlab_size(LL)
                    kdims = np.ones(Nf + 1, dtype=np.int64)
                    for ix, fac in enumerate(jv.tolist()):
                        if ix < len(sz_ll):
                            kdims[int(fac) - 1] = int(sz_ll[ix])
                    LLt = np.asarray(LL, dtype=np.float64).reshape(
                        tuple(int(x) for x in kdims.tolist()), order="F"
                    )
                    if isinstance(L, (int, float)) and float(L) == 0.0:
                        L = LLt.astype(np.float64)
                    else:
                        L = np.asarray(L, dtype=np.float64) + LLt

                sz_L = np.array(L.shape, dtype=np.int64)
                r = np.flatnonzero(sz_L > 1).astype(np.int64)
                if r.size == 0:
                    F[ti] = float(np.asarray(L, dtype=np.float64).reshape(-1)[0])
                else:
                    new_shape = tuple(int(sz_L[int(i)]) for i in r.tolist()) + (1, 1)
                    L = np.asarray(L, dtype=np.float64).reshape(new_shape, order="F")

                    Q_rt = _Q_factors_subset(Q, mi, r, ti)
                    for dim_i in range(r.size):
                        loop_i = dim_i + 1
                        f_dim = int(r[dim_i]) + 1
                        LLln = spm_vec(spm_dot(L, Q_rt, loop_i))
                        ll_col = np.asarray(LLln, dtype=np.float64).reshape(-1, 1, order="F")
                        LPv = np.zeros_like(ll_col, dtype=np.float64)
                        if t_m == 1:
                            LPv = LPv + np.asarray(spm_log(D[mi][f_dim - 1]), dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                        if t_m < T:
                            qbf = np.asarray(qb[mi][f_dim - 1], dtype=np.float64)
                            Pmft = P[mi][f_dim - 1][ti]
                            Qn = Q[mi][f_dim - 1][ti + 1]
                            tdot = spm_dot(spm_psi(tr(qbf)), Pmft)
                            LPv = LPv + _sdot_mtimes_q(tdot, np.asarray(Qn, dtype=np.float64))
                        if t_m > 1:
                            qbf = np.asarray(qb[mi][f_dim - 1], dtype=np.float64)
                            Pprev = P[mi][f_dim - 1][ti - 1]
                            Qp = Q[mi][f_dim - 1][ti - 1]
                            tdot = spm_dot(spm_psi(qbf), Pprev)
                            LPv = LPv + _sdot_mtimes_q(tdot, np.asarray(Qp, dtype=np.float64))

                        sm_arg = ll_col + LPv
                        Q[mi][f_dim - 1][ti] = spm_softmax(sm_arg)
                        q_post = np.asarray(Q[mi][f_dim - 1][ti], dtype=np.float64).reshape(-1, 1)
                        logq = spm_log(q_post)
                        F[ti] = F[ti] + float(np.sum(q_post * (ll_col + LPv - logq)))

        # Path beliefs (~2262–2314)
        nqb_path = _numel_qb_row(qb, mi)
        for f_1 in range(1, nqb_path + 1):
            fi = f_1 - 1
            qbf_cell = np.asarray(qb[mi][fi], dtype=np.float64)
            Urow = np.asarray(U[mi], dtype=np.float64).ravel()
            if int(Urow[f_1 - 1]) != 0:
                for t_m in range(2, T + 1):
                    ti = t_m - 1
                    LLp = spm_vec(
                        spm_dot(
                            spm_dot(spm_psi(qbf_cell), Q[mi][fi][ti]),
                            Q[mi][fi][ti - 1],
                        )
                    )
                    LPp = spm_log(P[mi][fi][ti - 1])
                    ll_p = np.asarray(LLp, dtype=np.float64).reshape(-1, 1, order="F")
                    lp_p = np.asarray(LPp, dtype=np.float64).reshape(-1, 1, order="F")
                    P[mi][fi][ti - 1] = spm_softmax(ll_p + lp_p)
                    p_post = np.asarray(P[mi][fi][ti - 1], dtype=np.float64).reshape(-1, 1)
                    logp = spm_log(p_post)
                    F[ti] = F[ti] + float(np.sum(p_post * (ll_p + lp_p - logp)))
            else:
                LLacc = np.zeros((1, 1), dtype=np.float64)
                for t_m in range(2, T + 1):
                    ti = t_m - 1
                    term = spm_vec(
                        spm_dot(
                            spm_dot(spm_psi(qbf_cell), Q[mi][fi][ti]),
                            Q[mi][fi][ti - 1],
                        )
                    )
                    tcol = np.asarray(term, dtype=np.float64).reshape(-1, 1, order="F")
                    if LLacc.size == 1 and LLacc.reshape(-1)[0] == 0.0:
                        LLacc = tcol.copy()
                    else:
                        LLacc = LLacc + tcol
                LPp = spm_log(E[mi][fi])
                lp_e = np.asarray(LPp, dtype=np.float64).reshape(-1, 1, order="F")
                PP = spm_softmax(LLacc + lp_e)
                for t_m in range(1, T + 1):
                    ti = t_m - 1
                    P[mi][fi][ti] = PP
                p_post = np.asarray(PP, dtype=np.float64).reshape(-1, 1)
                logp = spm_log(p_post)
                for t_m in range(1, T + 1):
                    ti = t_m - 1
                    F[ti] = F[ti] + float(np.sum(p_post * (LLacc + lp_e - logp)))

        F_out = F.copy()
        dF = float(np.sum(F)) - float(Z)
        if float(np.sum(F)) > 0:
            warnings.warn("positive ELBO in spm_backwards", UserWarning, stacklevel=1)
        if dF < 1.0 / 128.0:
            break
        Z = float(np.sum(F))

    return Q, P, qa, qb, F_out


def _cell_get_Qjt(Q: list, mi: int, jv: np.ndarray, ti: int) -> Any:
    jv = np.asarray(jv, dtype=np.int64).ravel()
    if jv.size == 1:
        return Q[mi][int(jv[0]) - 1][ti]
    return [Q[mi][int(j) - 1][ti] for j in jv.tolist()]


def _Q_factors_subset(Q: list, mi: int, r: np.ndarray, ti: int) -> list:
    """Build MATLAB ``Q(m,r,t)`` — list of factor slices at indices ``r`` (0-based dims)."""
    out: list = []
    for idx in r.tolist():
        fi = int(idx)
        out.append(Q[mi][fi][ti])
    return out


__all__ = ["spm_backwards"]
