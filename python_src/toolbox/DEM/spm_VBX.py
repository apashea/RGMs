"""
Variational Bayes / belief propagation for categorical MDP factors (MATLAB-compatible).

Translated from spm_VBX.m (Pass 1 faithful transliteration). Local helpers mirror
the MATLAB nested subfunctions (including local ``spm_log`` semantics).
"""

from __future__ import annotations

import numpy as np

from matlab_compat import full, matlab_scalar
from python_src.spm_combinations import spm_combinations
from python_src.spm_cross import spm_cross
from python_src.spm_dot import spm_dot
from python_src.spm_softmax import spm_softmax
from python_src.spm_sum import spm_sum
from python_src.toolbox.DEM.spm_edges import spm_edges
from python_src.toolbox.DEM.spm_parents import spm_parents


def _cell_multi_get(cur, indices_1based: list):
    """MATLAB id.fg{g}{ind{:}} / id.gg{g}{ind{:}} with 1-based indices."""
    if len(indices_1based) == 1:
        return cur[int(indices_1based[0]) - 1]
    if len(indices_1based) == 2:
        r = int(indices_1based[0]) - 1
        c = int(indices_1based[1]) - 1
        return cur[r][c]
    out = cur
    for idx in indices_1based:
        out = out[int(idx) - 1]
    return out


def _vbx_log(A):
    """Local spm_log from spm_VBX.m (not repo ``spm_log``)."""
    A = np.asarray(A)
    if A.dtype == bool or np.issubdtype(A.dtype, np.bool_):
        return -32.0 * (~np.asarray(A, dtype=bool))
    return np.fmax(np.log(np.asarray(A, dtype=float)), -32.0)


def _spm_margin(X):
    X = np.asarray(X, dtype=float, order="F")
    n = int(X.ndim)
    Y = []
    for i in range(n):
        j_dims = [d + 1 for d in range(n) if d != i]
        s = X
        for dim in j_dims:
            s = np.asarray(spm_sum(s, int(dim)), dtype=float)
        Y.append(np.reshape(s, (-1, 1), order="F"))
    return Y


def _spm_times(X, *args_cell):
    """MATLAB ``spm_times`` — matches ``X .* spm_cross(x{:})`` (see spm_VBX.m)."""
    X = np.asarray(full(X), dtype=float, order="F")
    if not args_cell:
        return X
    cr = spm_cross(*[full(t) for t in args_cell])
    return X * np.asarray(full(cr), dtype=float, order="F")


def _spm_VBX_sparse(P):
    Nf = len(P)
    R = [None] * Nf
    s = [None] * Nf
    for f in range(Nf):
        Pf = np.asarray(P[f], dtype=float).reshape(-1, order="F")
        s[f] = Pf > np.exp(-16.0)
        # Match MATLAB column shape P{f}(s{f}) — 1-D NumPy slices lose (N,1) and break
        # ``spm_cross`` / ``_spm_times`` broadcasting vs ``spm_times`` in spm_VBX.m.
        R[f] = Pf[np.ravel(s[f])].reshape(-1, 1)
    return R, s


def _a_colon_s_coerce_likelihood_(A):
    """MATLAB ``A{g}`` is ``(No, …)`` column-major; ``loadmat`` may yield ``(No,)`` or ``(1, No)``."""
    X = np.asarray(full(A), dtype=float, order="F")
    if X.ndim == 1 and X.size > 1:
        return X.reshape(-1, 1, order="F")
    if X.ndim == 2 and X.shape[0] == 1 and X.shape[1] > 1:
        return np.asarray(X.reshape(X.shape[1], 1, order="F"), dtype=float, order="F")
    return X


def _a_colon_s_logical(A, s_masks):
    """MATLAB ``A(:, s{:})`` with logical masks for trailing dimensions (``spm_VBX_update``)."""
    X = _a_colon_s_coerce_likelihood_(A)
    for k, mask in enumerate(s_masks):
        m = np.asarray(mask, dtype=bool).reshape(-1)
        axis = k + 1
        X = np.compress(m, X, axis=axis)
    while X.ndim > 1 and X.shape[-1] == 1:
        X = X[..., 0]
    return X


def _a_colon_s_index_dim2(A, idx_1based):
    """MATLAB ``A(:, s{f})`` in ``spm_VBX_update_L`` — numeric indices along dim 2 (``f(1)`` only)."""
    idx = np.asarray(idx_1based, dtype=np.int64).ravel() - 1
    X = np.asarray(full(A), dtype=float, order="F")
    tup = (slice(None), idx) + (slice(None),) * max(0, X.ndim - 2)
    return X[tup]


def _p_sub(P, j_arr):
    jj = np.asarray(j_arr, dtype=int).ravel()
    return [P[int(jx) - 1] for jx in jj]


def _fg_at(id_dict, g, ind_vals):
    """Parents ``f`` from ``id.fg`` / ``id.A{g}`` (``spm_VBX_update_L``)."""
    ind_list = [float(v) for v in np.asarray(ind_vals, dtype=float).ravel().tolist()]
    if "fg" in id_dict:
        fg = id_dict["fg"]
        if isinstance(fg, np.ndarray):
            if fg.ndim == 2:
                cols = np.array(ind_list, dtype=np.int64)
                return np.asarray(fg[g - 1, cols - 1])
            sub = (g - 1,) + tuple(int(ind_list[k]) - 1 for k in range(len(ind_list)))
            return np.asarray(fg[sub])
        return _cell_multi_get(fg[g - 1], ind_list)
    return id_dict["A"][g - 1]


def _gg_at(id_dict, g, ind_vals):
    """Children ``j`` from ``id.gg`` / scalar ``g`` (``spm_VBX_update_L``)."""
    ind_list = [float(v) for v in np.asarray(ind_vals, dtype=float).ravel().tolist()]
    if "gg" in id_dict:
        gg = id_dict["gg"]
        if isinstance(gg, np.ndarray):
            if gg.ndim == 2:
                cols = np.array(ind_list, dtype=np.int64)
                return np.asarray(gg[g - 1, cols - 1])
            sub = (g - 1,) + tuple(int(ind_list[k]) - 1 for k in range(len(ind_list)))
            return np.asarray(gg[sub])
        return _cell_multi_get(gg[g - 1], ind_list)
    return float(g)


def _spm_VBX_update_L(A, O, P, R, s, g, ff, id_dict):
    ff = np.asarray(ff, dtype=np.int64).ravel()
    nff = int(ff.size)
    Ns = np.ones(nff, dtype=int)
    for f in range(nff):
        fac = int(ff[f])
        Ns[f] = int(np.size(np.asarray(s[fac - 1])))
    L = np.zeros(tuple(int(x) for x in Ns), dtype=float, order="F")
    c = spm_combinations(Ns)
    for ii in range(int(c.shape[0])):
        ind = []
        for j in range(nff):
            fac = int(ff[j])
            sj = np.asarray(s[fac - 1], dtype=np.int64).ravel()
            ind.append(float(sj[int(c[ii, j]) - 1]))
        f_par = _fg_at(id_dict, g, ind)
        j_ch = _gg_at(id_dict, g, ind)
        f0 = int(np.asarray(f_par, dtype=int).ravel(order="F")[0])
        s_f = s[f0 - 1]
        if callable(A[g - 1]) and not isinstance(A[g - 1], np.ndarray):
            P_list = _p_sub(P, np.asarray(f_par, dtype=int).ravel())
            qo = A[g - 1](P_list)
        else:
            Ag = A[g - 1]
            s_idx = np.asarray(s_f, dtype=np.int64).ravel()
            A_slice = _a_colon_s_index_dim2(Ag, s_idx)
            f_list = np.asarray(f_par, dtype=int).ravel(order="F")
            dot_args = [O[g - 1]] + [R[int(fx) - 1] for fx in f_list]
            qo = spm_dot(A_slice, dot_args, 1)
        j_arr = np.atleast_1d(np.asarray(j_ch, dtype=float)).ravel()
        sub = tuple(int(c[ii, k]) - 1 for k in range(nff))
        for o in j_arr:
            oi = int(o)
            L[sub] = L[sub] + _vbx_log(spm_dot(qo, O[oi - 1]))
    return L


def _callable_multi_out(Afun) -> bool:
    return int(getattr(Afun, "_rgms_vbx_nout", 1)) > 1


def _spm_VBX_update(P, A, O, i_children, j_parents):
    j = j_parents
    if isinstance(j, (list, tuple)):
        j_list = [int(np.asarray(x).reshape(-1)[0]) for x in j]
    else:
        j_list = [int(x) for x in np.atleast_1d(np.asarray(j, dtype=int)).ravel().tolist()]
    Nf = len(j_list)
    Pj = [P[jj - 1] for jj in j_list]
    R, s = _spm_VBX_sparse(Pj)
    M: list = [None] * Nf
    L_acc = None
    U_last = None
    r = np.arange(1, Nf + 1, dtype=int)
    i_list = np.atleast_1d(np.asarray(i_children, dtype=float)).ravel().tolist()
    for o in i_list:
        oi = int(o)
        if callable(A) and not isinstance(A, np.ndarray):
            if _callable_multi_out(A):
                U, r = A(O[oi - 1], s, Pj)
                r = np.asarray(r, dtype=int).ravel()
            else:
                U = A(O[oi - 1], s)
                r = np.arange(1, Nf + 1, dtype=int)
            if isinstance(U, (list, tuple)) and len(U) > 0 and isinstance(U[0], np.ndarray):
                for f in range(len(U)):
                    t = _vbx_log(U[f])
                    M[f] = t if M[f] is None else (M[f] + t)
            else:
                t = _vbx_log(U)
                L_acc = t if L_acc is None else (L_acc + t)
            U_last = U
        else:
            A_sub = _a_colon_s_logical(A, s)
            Oo = np.asarray(full(O[oi - 1]), dtype=float, order="F")
            if Oo.ndim == 1 and Oo.size > 1:
                Oo = Oo.reshape(-1, 1, order="F")
            U_last = spm_dot(A_sub, Oo)
            t = _vbx_log(U_last)
            L_acc = t if L_acc is None else (L_acc + t)
    U = U_last
    if U is None:
        return P, -32.0
    if isinstance(U, (list, tuple)) and len(U) > 0 and isinstance(U[0], np.ndarray):
        F = 0.0
        Q = [None] * len(U)
        r_arr = np.asarray(r, dtype=int).ravel()
        for f in range(len(U)):
            rf = int(r_arr[f])
            Uf = np.exp(M[f]) * np.asarray(R[rf - 1], dtype=float)
            Z = float(np.sum(Uf))
            if Z:
                F = F + float(_vbx_log(Z))
                Q[f] = Uf / Z
            else:
                F = float(F + (-32.0))
                Q[f] = Uf + 1.0 / float(np.size(Uf))
        j_ord = [j_list[int(r_arr[f]) - 1] for f in range(len(r_arr))]
        for f in range(len(j_ord)):
            jf = int(j_ord[f])
            rf = int(r_arr[f])
            mask = np.asarray(s[rf - 1], dtype=bool).reshape(-1)
            qf = np.asarray(Q[f], dtype=float).reshape(-1, order="F")
            arr = np.asarray(P[jf - 1], dtype=float).reshape(-1, order="F").copy()
            arr[:] = 0.0
            arr[mask] = qf
            P[jf - 1] = arr.reshape(np.asarray(P[jf - 1]).shape, order="F")
        return P, float(F)
    L_tensor = L_acc
    if L_tensor is None:
        return P, -32.0
    if np.size(L_tensor) > 1:
        L_exp = np.exp(np.asarray(L_tensor, dtype=float, order="F"))
        U_t = _spm_times(L_exp, *R)
        Z = float(np.sum(U_t))
        if Z:
            F = float(_vbx_log(Z))
            Q = _spm_margin(U_t / Z)
        else:
            F = -32.0
            Q = _spm_margin(U_t + 1.0 / float(np.size(U_t)))
        n_up = min(len(j_list), len(Q))
        for f in range(n_up):
            jf = int(j_list[f])
            mask = np.asarray(s[f], dtype=bool).reshape(-1)
            qf = np.asarray(Q[f], dtype=float).reshape(-1, order="F")
            arr = np.asarray(P[jf - 1], dtype=float).reshape(-1, order="F").copy()
            arr[:] = 0.0
            arr[mask] = qf
            P[jf - 1] = arr.reshape(np.asarray(P[jf - 1]).shape, order="F")
        return P, float(F)
    if np.size(L_tensor) == 1:
        return P, float(np.asarray(L_tensor).reshape(-1)[0])
    return P, -32.0


def _get_ig(id_dict):
    if "i" in id_dict:
        gcell = id_dict["g"]
        ii = np.asarray(id_dict["i"], dtype=int).ravel()
        return [gcell[int(k) - 1] for k in ii.tolist()]
    return id_dict["g"]


def _ff_partition(id_dict, p):
    ff = id_dict["ff"]
    if isinstance(ff, list) and len(ff) > 0:
        first = ff[0]
        if isinstance(first, np.ndarray):
            return np.asarray(ff[int(p)], dtype=np.int64).ravel()
    return np.asarray(ff, dtype=np.int64).ravel()


def _nq_from_edges_j(j0):
    if isinstance(j0, (list, tuple)):
        return len(j0)
    return int(np.size(np.asarray(j0)))


def _j_in_ff(j, ff_arr):
    j_flat = np.asarray(j, dtype=float).ravel()
    ff_flat = np.asarray(ff_arr, dtype=int).ravel()
    return bool(np.any(np.isin(j_flat.astype(int), ff_flat)))


def spm_VBX(O, P, A, id_dict):
    """
    FORMAT P, F = spm_VBX(O, P, A, id)

    ``O``, ``P``, ``A`` — list/tuple of NumPy arrays (MATLAB cell semantics).
    ``id_dict`` — struct-like dict with keys ``g``, optional ``i``, ``ff``, ``fg``, ``gg``, ``A``.
    """
    ig = _get_ig(id_dict)
    Nf = len(P)
    F = 0.0

    if "ff" in id_dict:
        ff_top = np.asarray(id_dict["ff"], dtype=int).ravel()
        for p in range(len(ig)):
            for g in np.atleast_1d(np.asarray(ig[p], dtype=int)).ravel().tolist():
                gi = int(g)
                j, i_ch = spm_parents(id_dict, gi, P)
                if _j_in_ff(j, ff_top):
                    P, f_add = _spm_VBX_update(P, A[gi - 1], O, i_ch, j)
                    F = F + f_add

    if "ff" in id_dict:
        R = [None] * Nf
        s_dom = [None] * Nf
        for f in range(Nf):
            Pf = np.asarray(P[f], dtype=float).reshape(-1, order="F")
            idx = np.where(Pf > np.exp(-8.0))[0] + 1
            s_dom[f] = idx.astype(np.float64)
            R[f] = Pf[idx - 1]
        for p in range(len(ig)):
            ff = _ff_partition(id_dict, p)
            nff = int(ff.size)
            Ns = np.ones(nff, dtype=int)
            for f in range(nff):
                fac = int(ff[f])
                Ns[f] = int(np.size(s_dom[fac - 1]))
            if int(np.prod(Ns)) > 1:
                Ldom = None
                for g in np.atleast_1d(np.asarray(ig[p], dtype=int)).ravel().tolist():
                    gi = int(g)
                    Li = _spm_VBX_update_L(A, O, P, R, s_dom, gi, ff, id_dict)
                    Ldom = Li if Ldom is None else (Ldom + Li)
                U = _spm_times(
                    np.exp(np.asarray(Ldom, dtype=float, order="F")),
                    *[R[int(ff[i]) - 1] for i in range(nff)],
                )
                Z = float(np.sum(U))
                if Z:
                    Qm = _spm_margin(U / Z)
                else:
                    Qm = _spm_margin(U + 1.0 / float(np.size(U)))
                for i in range(len(Qm)):
                    fac = int(ff[i])
                    R[fac - 1] = np.asarray(Qm[i], dtype=float).reshape(-1, order="F")
                for fac in np.asarray(ff, dtype=int).ravel().tolist():
                    arr = np.zeros_like(np.asarray(P[fac - 1], dtype=float).reshape(-1, order="F"))
                    msk = s_dom[fac - 1].astype(np.int64) - 1
                    arr[msk] = np.asarray(R[fac - 1], dtype=float).reshape(-1, order="F")
                    P[fac - 1] = arr.reshape(np.asarray(P[fac - 1]).shape, order="F")

    j0, _, _ = spm_edges(id_dict, 1, P)
    Nq = _nq_from_edges_j(j0)
    F_col = np.full((Nq, 1), float(np.asarray(F, dtype=float).reshape(-1)[0]), dtype=float)
    P_template = [np.asarray(P[f], dtype=float, order="F").copy() for f in range(Nf)]
    S = [[np.array(P_template[f], copy=True) for f in range(Nf)] for _ in range(Nq)]

    for p in range(len(ig)):
        for g in np.atleast_1d(np.asarray(ig[p], dtype=int)).ravel().tolist():
            gi = int(g)
            jq, iq, _ = spm_edges(id_dict, gi, P)
            if not isinstance(jq, (list, tuple)):
                jq = [jq]
                iq = [iq]
            for q in range(Nq):
                i_ch = iq[q]
                j = jq[q]
                Srow = [np.array(S[q][f], copy=True) for f in range(Nf)]
                Pupd, Fq = _spm_VBX_update(Srow, A[gi - 1], O, i_ch, j)
                j_idx = np.atleast_1d(np.asarray(j, dtype=float)).ravel().tolist()
                for jv in j_idx:
                    jf = int(jv)
                    S[q][jf - 1] = np.array(Pupd[jf - 1], copy=True)
                F_col[q, 0] = F_col[q, 0] + float(Fq)

    # Column (Nq,1) so ``spm_softmax`` does not treat the vector as a single-row matrix
    # and return ones (see ``spm_softmax`` shape[0] < 2 branch).
    p_w = np.asarray(spm_softmax(np.asarray(F_col, dtype=float, order="F")), dtype=float).reshape(-1)
    F_out = float(np.dot(F_col.reshape(-1), p_w.reshape(-1)))
    for f in range(Nf):
        acc = np.zeros_like(np.asarray(P[f], dtype=float), order="F")
        for q in range(Nq):
            acc = acc + np.asarray(S[q][f], dtype=float) * float(p_w[q])
        P[f] = acc
    return P, matlab_scalar(np.array(F_out))
