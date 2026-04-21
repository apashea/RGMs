"""Pass 1 transliteration of spm_faster_structure_learning.m (locals + main).

Local MATLAB subfunctions ``spm_structure_fast`` and ``spm_group`` are
``_spm_structure_fast`` and ``_spm_group``. ``SPINBLOCK`` is fixed ``False`` to
match the staged ``.m`` default used by the §5 snippet; the ``true`` spatial-block
branch is deferred (see ``notes/andrew Python Matlab Translation Issues.md``).

Optional keyword-only hooks ``rgm_eig_pair``, ``rgm_mi_override_fn``, and
``link_dir_mi_fn`` exist only for **provisional**, **reversible** translation
validation (e.g. MATLAB Engine oracles). Production callers should omit them so
behaviour matches the committed pure-Python transliteration.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import numpy as np
from scipy import sparse

from python_src.spm_cat import spm_cat
from python_src.spm_cross import spm_cross
from python_src.spm_dir_MI import spm_dir_MI
from python_src.spm_dir_norm import spm_dir_norm
from python_src.spm_unvec import spm_unvec
from python_src.spm_vec import spm_vec
from python_src.toolbox.DEM.spm_rgm_group import spm_rgm_group
from python_src.toolbox.DEM.spm_unique import spm_unique


def spm_faster_structure_learning(
    O,
    S,
    dx=None,
    dt=None,
    *,
    rgm_eig_pair: Optional[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
    rgm_mi_override_fn: Optional[Callable[[List[Any], int], np.ndarray]] = None,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
):
    """RG structure learning — Pass 1 mirror of ``spm_faster_structure_learning.m``.

    Parameters
    ----------
    rgm_eig_pair :
        Forwarded as ``eig_pair`` to every ``spm_rgm_group`` call (oracle / MATLAB
        ``eig(...,'nobalance')`` bridge). Default ``None`` keeps production SciPy
        eigenpairs.
    rgm_mi_override_fn :
        Optional ``(o_sub, m) -> MI`` for provisional translation validation only;
        forwarded as ``mi_override`` into each ``spm_rgm_group`` call. Default
        ``None`` builds ``MI`` inside ``spm_rgm_group`` from ``O`` in Python.
    link_dir_mi_fn :
        Optional ``a_mat -> float`` replacing ``spm_dir_MI`` when storing stream-link
        matrices ``ss.ID`` / ``ss.IE``. Oracle-only (e.g. MATLAB Engine); default
        ``None`` uses native Python.
    """
    spinblock = False
    S = np.asarray(S, dtype=np.float64)
    if S.ndim == 1:
        S = S.reshape(1, -1)
    if S.shape[1] < 4:
        S = np.hstack([S, np.ones((S.shape[0], 4 - S.shape[1]), dtype=np.float64)])
    if S.shape[0] == 1:
        n_o = len(O)
        prod_s = float(np.prod(S[0, :3]))
        S[0, 3] = n_o / prod_s

    if dx is None:
        dx = 2.0
    if dt is None:
        dt = 2.0
    dx = np.concatenate(
        [np.asarray([float(dx)], dtype=np.float64), np.repeat(float(dx), 16)]
    )
    dt = np.concatenate(
        [np.asarray([float(dt)], dtype=np.float64), np.repeat(float(dt), 16)]
    )

    mdp_h: list[dict] = []
    n_stream = int(S.shape[0])
    o_cur = O

    for n in range(1, 9):
        sg: list[np.ndarray | None] = [None] * n_stream
        n_cells: dict[tuple[int, int], np.ndarray] = {}
        ng = np.zeros(n_stream, dtype=np.int64)

        mdp_n = _new_mdp_level(n_stream, float(dt[n - 1]))

        for s in range(1, n_stream + 1):
            no = len(mdp_n["a"])
            ns = len(mdp_n["b"])
            nt = len(o_cur[0]) if len(o_cur) else 0
            t_idx = np.arange(1, nt, int(dt[n - 1]), dtype=np.int64)
            if t_idx.size == 0:
                t_idx = np.array([1], dtype=np.int64)

            if spinblock:
                g = _spm_group(S[s - 1, :].tolist(), int(dx[n - 1]))
            else:
                o_stack = np.concatenate([[0.0], np.prod(S, axis=1).astype(np.float64)])
                offset = float(o_stack[s - 1])
                n_o_s = int(np.prod(S[s - 1, :]))
                idx = (offset + np.arange(1, n_o_s + 1, dtype=np.float64)).astype(np.int64)
                o_sub = [o_cur[int(i) - 1] for i in idx]
                m_stream = int(S[s - 1, 3])
                mi_override = None
                if rgm_mi_override_fn is not None:
                    mi_override = np.asarray(
                        rgm_mi_override_fn(o_sub, m_stream), dtype=np.float64
                    )
                g = spm_rgm_group(
                    o_sub,
                    int(dx[n - 1]),
                    m_stream,
                    eig_pair=rgm_eig_pair,
                    mi_override=mi_override,
                )

            g_off = spm_unvec(spm_vec(g) + float(no), g)
            g_use = []
            for item in g_off:
                arr = np.asarray(item, dtype=np.int64).ravel()
                g_use.append(arr.reshape((-1, 1), order="F"))
            mdp_n["G"][s] = g_use

            ng[s - 1] = len(g_use)
            j_len = nt
            sg[s - 1] = np.zeros((int(ng[s - 1]), j_len), dtype=np.float64)

            for g_i in range(1, int(ng[s - 1]) + 1):
                fg = ns + g_i
                gg = mdp_n["G"][s][g_i - 1].ravel(order="F").astype(np.int64)
                o_gg = [o_cur[int(ix) - 1] for ix in gg]
                mdp_loc, j_loc = _spm_structure_fast(o_gg)
                jv = np.asarray(j_loc, dtype=np.float64).ravel()
                n_j = min(jv.size, sg[s - 1].shape[1])
                sg[s - 1][g_i - 1, :n_j] = jv[:n_j]

                _assign_a_by_gg_rows(mdp_n["a"], gg, mdp_loc["a"])
                _assign_b_fg(mdp_n["b"], fg, mdp_loc["b"])

                i_d = 2 * ns + 2 * g_i - 1
                i_e = 2 * ns + 2 * g_i
                for r in np.asarray(gg, dtype=np.int64).ravel():
                    _set_indexed_scalar_cell(mdp_n["id"]["A"], int(r), fg)
                    _set_indexed_scalar_cell(mdp_n["sA"], int(r), s)
                    _set_indexed_scalar_cell(mdp_n["sC"], int(r), s)
                _set_id_list_at(mdp_n["id"]["D"], fg, [i_d])
                _set_id_list_at(mdp_n["id"]["E"], fg, [i_e])
                _set_indexed_scalar_cell(mdp_n["sB"], fg, s)

                for col_k, tk in enumerate(t_idx, start=1):
                    n_cells[(i_d, col_k)] = np.asarray(
                        mdp_loc["X"][int(tk) - 1], dtype=bool
                    ).ravel()
                    p_t = mdp_loc["P"][int(tk) - 1]
                    if isinstance(p_t, np.ndarray) and p_t.size > 1:
                        n_cells[(i_e, col_k)] = np.asarray(p_t, dtype=bool).ravel()
                    else:
                        n_cells[(i_e, col_k)] = np.array([bool(np.asarray(p_t).ravel()[0])], dtype=bool)

        if n > 1:
            _link_streams(mdp_n, mdp_h[n - 2], ng, sg, link_dir_mi_fn=link_dir_mi_fn)

        if int(np.max(ng)) < 2 and n > 1:
            mdp_h.append(mdp_n)
            break

        if not spinblock:
            o_cur, S = _compress_unitary_and_slice_o(mdp_n, n_cells, t_idx, S, n_stream, n)
        else:
            for s in range(1, n_stream + 1):
                g_shape = mdp_n["G"][s]
                s_dims = [max(1, len(g_shape)), 1, 1] if isinstance(g_shape, list) else [1, 1, 1]
                S[s - 1, :4] = np.array(s_dims + [2], dtype=np.float64)[:4]

        mdp_h.append(mdp_n)

    return mdp_h


def _new_mdp_level(n_stream: int, t_scale: float) -> dict:
    return {
        "a": [],
        "b": [],
        "id": {"A": [], "D": [], "E": []},
        "G": {},
        "T": t_scale,
        "sA": [],
        "sB": [],
        "sC": [],
        "ss": {
            "D": [[None for _ in range(n_stream)] for __ in range(n_stream)],
            "E": [[None for _ in range(n_stream)] for __ in range(n_stream)],
            "ID": [[None for _ in range(n_stream)] for __ in range(n_stream)],
            "IE": [[None for _ in range(n_stream)] for __ in range(n_stream)],
        },
    }


def _assign_a_by_gg_rows(a_rows: list, gg: np.ndarray, mdp_a: list) -> None:
    gg_flat = np.asarray(gg, dtype=np.int64).ravel()
    for k in range(len(gg_flat)):
        r = int(gg_flat[k])
        while len(a_rows) < r:
            a_rows.append([None])
        a_rows[r - 1] = [mdp_a[k]]


def _assign_b_fg(b_rows: list, fg: int, mdp_b: list) -> None:
    while len(b_rows) < fg:
        b_rows.append([None])
    b_rows[fg - 1] = list(mdp_b)


def _set_id_list_at(id_list: list, fg: int, values: list) -> None:
    while len(id_list) < fg:
        id_list.append([])
    id_list[fg - 1] = list(values)


def _set_indexed_scalar_cell(lst: list, idx: int, value) -> None:
    while len(lst) < idx:
        lst.append(None)
    lst[idx - 1] = value


def _find_ismember_indices(sb_list: list, target: int) -> list[int]:
    return [i + 1 for i, v in enumerate(sb_list) if v is not None and int(v) == int(target)]


def _link_streams(
    mdp_n: dict,
    mdp_prev: dict,
    ng: np.ndarray,
    sg: list[np.ndarray | None],
    *,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
) -> None:
    def _stream_link_mi(a_mat: np.ndarray) -> float:
        if link_dir_mi_fn is not None:
            return float(link_dir_mi_fn(np.asarray(a_mat, dtype=np.float64)))
        return float(np.real(spm_dir_MI(a_mat)))

    si = 1
    st = np.flatnonzero(ng) + 1
    for sj in st[1:].tolist():
        fsi = _find_ismember_indices(mdp_n["sB"], si)
        fsj = _find_ismember_indices(mdp_prev["sB"], sj)
        t_cols = int(sg[0].shape[1]) if sg[0] is not None else 0
        for i_idx in range(len(fsi)):
            for j_idx in range(len(fsj)):
                fi = fsi[i_idx]
                fj = fsj[j_idx]
                bi = mdp_n["b"][fi - 1][0]
                bj_prev = mdp_prev["b"][fj - 1][0]
                ni = int(np.asarray(bi).shape[0])
                nj = int(np.asarray(bj_prev).shape[1])
                nu = int(np.asarray(bj_prev).shape[2]) if np.asarray(bj_prev).ndim > 2 else 1

                gi = len(mdp_n["a"]) + 1
                gj = int(np.asarray(mdp_prev["id"]["D"][fj - 1]).ravel()[0])
                a_norm = spm_dir_norm(mdp_n["a"][gj - 1][0])
                if sparse.issparse(a_norm):
                    a_norm = a_norm.toarray()
                a_norm = np.asarray(a_norm, dtype=np.float64)
                a_mat = np.zeros((nj, ni), dtype=np.float64)
                for f in range(t_cols):
                    ii_sg = int(sg[si - 1][i_idx, f])
                    ij_sg = int(sg[int(sj) - 1][j_idx, f])
                    a_mat[:, ii_sg - 1] = a_mat[:, ii_sg - 1] + a_norm[:, ij_sg - 1]

                _append_linked_likelihood(mdp_n, a_mat, fi, si, sj)
                mdp_prev["id"]["D"][fj - 1] = list(mdp_prev["id"]["D"][fj - 1]) + [gi]
                _ss_store(mdp_prev["ss"]["D"], sj, sj, fj, fj, gj)
                _ss_store(mdp_prev["ss"]["D"], si, sj, fi, fj, gi)
                _ss_store_mi(mdp_prev["ss"]["ID"], si, sj, fi, fj, _stream_link_mi(a_mat))

                gi = len(mdp_n["a"]) + 1
                gj = int(np.asarray(mdp_prev["id"]["E"][fj - 1]).ravel()[0])
                a_norm = spm_dir_norm(mdp_n["a"][gj - 1][0])
                if sparse.issparse(a_norm):
                    a_norm = a_norm.toarray()
                a_norm = np.asarray(a_norm, dtype=np.float64)
                a_mat = np.zeros((nu, ni), dtype=np.float64)
                for f in range(t_cols):
                    ii_sg = int(sg[si - 1][i_idx, f])
                    ij_sg = int(sg[int(sj) - 1][j_idx, f])
                    a_mat[:, ii_sg - 1] = a_mat[:, ii_sg - 1] + a_norm[:, ij_sg - 1]

                _append_linked_likelihood(mdp_n, a_mat, fi, si, sj)
                mdp_prev["id"]["E"][fj - 1] = list(mdp_prev["id"]["E"][fj - 1]) + [gi]
                _ss_store(mdp_prev["ss"]["E"], sj, sj, fj, fj, gj)
                _ss_store(mdp_prev["ss"]["E"], si, sj, fi, fj, gi)
                _ss_store_mi(mdp_prev["ss"]["IE"], si, sj, fi, fj, _stream_link_mi(a_mat))


def _append_linked_likelihood(mdp_n: dict, a_mat: np.ndarray, fi: int, si: int, sj: int) -> None:
    mdp_n["a"].append([a_mat])
    mdp_n["id"]["A"].append([fi])
    mdp_n["sA"].append(si)
    mdp_n["sC"].append(sj)


def _ss_store(ss_mat: list, si: int, sj: int, fi: int, fj: int, val: int) -> None:
    m = ss_mat[int(si) - 1][int(sj) - 1]
    if m is None:
        m = {}
        ss_mat[int(si) - 1][int(sj) - 1] = m
    m[(int(fi), int(fj))] = int(val)


def _ss_store_mi(ss_mat: list, si: int, sj: int, fi: int, fj: int, val: float) -> None:
    m = ss_mat[int(si) - 1][int(sj) - 1]
    if m is None:
        m = {}
        ss_mat[int(si) - 1][int(sj) - 1] = m
    m[(int(fi), int(fj))] = val


def _compress_unitary_and_slice_o(
    mdp_n: dict,
    n_cells: dict,
    t_idx: np.ndarray,
    S: np.ndarray,
    n_stream: int,
    n: int,
):
    ns_b = len(mdp_n["b"])
    d_mask = np.ones(ns_b, dtype=bool)
    for f in range(1, ns_b + 1):
        sb = mdp_n["sB"][f - 1]
        if sb is not None and int(sb) == 1:
            b = np.sum(np.asarray(mdp_n["b"][f - 1][0], dtype=np.float64), axis=2)
            if float(np.max(np.sum(b, axis=1))) < 1.0 and n < 2:
                d_mask[f - 1] = False
            denom = max(int(np.asarray(b).shape[0]), 1)
            if float(np.min(np.sum(b > 0, axis=0) / denom)) > 0.5 and b.size > 4:
                d_mask[f - 1] = False
            if np.asarray(mdp_n["b"][f - 1][0]).size == 1:
                d_mask[f - 1] = False

    for f in np.flatnonzero(~d_mask) + 1:
        mdp_n["b"][f - 1][0] = np.sum(np.asarray(mdp_n["b"][f - 1][0], dtype=np.float64))
        for g in _id_a_children(mdp_n["id"]["A"], f):
            ag = mdp_n["a"][g - 1][0]
            if sparse.issparse(ag):
                ag = ag.toarray()
            mdp_n["a"][g - 1][0] = np.sum(np.asarray(ag, dtype=np.float64), axis=1, keepdims=True)

    s_b_kept = [mdp_n["sB"][i] for i, keep in enumerate(d_mask) if keep]
    for s in range(n_stream):
        cnt = sum(1 for x in s_b_kept if x is not None and int(x) == s + 1)
        S[s, :4] = np.array([cnt, 1, 1, 2], dtype=np.float64)

    d_exp = np.repeat(d_mask, 2)
    i_vec = (np.flatnonzero(d_exp) + 1).astype(np.int64)
    old_set_d = [[int(x) for x in row] for row in mdp_n["id"]["D"]]
    old_set_e = [[int(x) for x in row] for row in mdp_n["id"]["E"]]
    for j in range(len(mdp_n["id"]["D"])):
        old = old_set_d[j]
        mdp_n["id"]["D"][j] = [k + 1 for k in range(len(i_vec)) if int(i_vec[k]) in set(old)]
    for j in range(len(mdp_n["id"]["E"])):
        old = old_set_e[j]
        mdp_n["id"]["E"][j] = [k + 1 for k in range(len(i_vec)) if int(i_vec[k]) in set(old)]

    O_new = _n_rows_to_o(n_cells, i_vec.tolist(), int(t_idx.size))
    return O_new, S


def _id_a_children(id_a: list, f: int) -> list[int]:
    out = []
    for gi, cell in enumerate(id_a, start=1):
        if cell is None:
            continue
        v = int(np.asarray(cell).ravel()[0])
        if v == f:
            out.append(gi)
    return out


def _n_rows_to_o(
    n_cells: dict,
    i_rows: list[int],
    ncols: int,
) -> list:
    O_out = []
    for _g in range(len(i_rows)):
        O_out.append([])
    for gi, row in enumerate(i_rows):
        for c in range(1, ncols + 1):
            key = (int(row), c)
            if key not in n_cells:
                raise KeyError(f"missing N cell {key}")
            col = n_cells[key].astype(np.float64).reshape((-1, 1), order="F")
            O_out[gi].append(col)
    return O_out


def _spm_group_sparse_col(rows_1based: np.ndarray, nrows: int) -> sparse.csr_matrix:
    """MATLAB ``sparse(rows,1,1,nrows,1)`` with 1-based row indices."""
    rows0 = np.asarray(rows_1based, dtype=np.int64).ravel() - 1
    cols0 = np.zeros(rows0.shape[0], dtype=np.int64)
    data = np.ones(rows0.shape[0], dtype=np.float64)
    return sparse.csr_matrix((data, (rows0, cols0)), shape=(int(nrows), 1))


def _spm_group(N, d=None):
    """Local ``spm_group`` from ``spm_faster_structure_learning.m``."""
    N = [int(x) for x in np.asarray(N, dtype=np.int64).ravel().tolist()]
    while len(N) < 4:
        N.append(1)
    N = N[:4]

    if d is None:
        d = [3 if (N[0] % 3 == 0) else 2, 3 if (N[1] % 3 == 0) else 2, 3 if (N[2] % 3 == 0) else 2]
    else:
        d = np.asarray(d, dtype=np.int64).ravel()
        if d.size == 1:
            dv = int(d.flat[0])
            d = [dv, dv, dv]
        else:
            d = [int(d.flat[0]), int(d.flat[1]), int(d.flat[2])]

    r = []
    s = []
    for i in range(3):
        di = min(d[i], N[i])
        d[i] = di
        if N[i] == 0:
            ri = []
        else:
            ri = list(range(0, N[i], di))
        r.append(ri)
        s.append(len(ri))

    L = [r[i][-1] + d[i] for i in range(3)]

    g = []
    n4 = N[3]
    for ii in range(s[0]):
        row_i = []
        for jj in range(s[1]):
            row_j = []
            for kk in range(s[2]):
                rows1 = np.arange(1, d[0] * n4 + 1, dtype=np.int64) + r[0][ii] * n4
                n1 = _spm_group_sparse_col(rows1, int(L[0] * n4))
                rows2 = np.arange(1, d[1] + 1, dtype=np.int64) + r[1][jj]
                n2 = _spm_group_sparse_col(rows2, int(L[1]))
                rows3 = np.arange(1, d[2] + 1, dtype=np.int64) + r[2][kk]
                n3 = _spm_group_sparse_col(rows3, int(L[2]))

                v = np.asarray(spm_cross(n1, n2, n3))
                d1 = N[0] * n4
                d2 = N[1]
                d3 = N[2]
                if v.ndim == 2:
                    v = v[:d1, :d2]
                else:
                    v = v[:d1, :d2, :d3]
                flat = np.ravel(v, order="F")
                row_j.append(np.flatnonzero(flat) + 1)
            row_i.append(row_j)
        g.append(row_i)
    return g


def _spm_structure_fast(O):
    """Local ``spm_structure_fast`` from ``spm_faster_structure_learning.m``."""
    i, j = spm_unique(O)
    i = np.atleast_1d(np.asarray(i, dtype=np.float64))
    j = np.atleast_1d(np.asarray(j, dtype=np.float64))
    if i.ndim == 1:
        i = i.reshape((-1, 1), order="F")
    if j.ndim == 1:
        j = j.reshape((-1, 1), order="F")

    ni = int(np.prod(i.shape, dtype=np.int64))
    nj = int(np.prod(j.shape, dtype=np.int64))
    jj = np.asarray(j, dtype=np.int64).ravel(order="F")
    rows_r = np.arange(nj, dtype=np.int64)
    R = sparse.csr_matrix(
        (np.ones(nj, dtype=np.float64), (rows_r, jj - 1)),
        shape=(nj, ni),
    )

    ng = len(O)
    a = []
    for g in range(ng):
        row_cell = [[O[g][t] for t in range(len(O[g]))]]
        ag = spm_cat(row_cell) @ R
        a.append(ag)

    ns = ni
    nt = nj - 1
    b = np.zeros((ns, ns, 1), dtype=np.float64)
    jf = np.asarray(j, dtype=np.int64).ravel(order="F")

    for t in range(nt):
        jt = int(jf[t]) - 1
        jtp1 = int(jf[t + 1]) - 1
        seg = b[jtp1, jt, :].ravel()
        nz = np.flatnonzero(seg)
        if nz.size:
            u = int(nz[0])
            b[jtp1, jt, u] += 1.0
        else:
            plane = b[:, jt, :]
            empty = np.flatnonzero(~plane.any(axis=0))
            if empty.size:
                u = int(empty[0])
                b[jtp1, jt, u] = 1.0
            else:
                b = np.concatenate([b, np.zeros((ns, ns, 1), dtype=np.float64)], axis=2)
                b[jtp1, jt, b.shape[2] - 1] = 1.0

    nu = b.shape[2]
    x0 = np.zeros(ns, dtype=bool)
    mdp_x = []
    for t in range(nt + 1):
        s = x0.copy()
        jidx = int(jf[t]) - 1
        s[jidx] = True
        mdp_x.append(s)
    mdp_x = mdp_x[:nt]

    mdp_p = []
    for t in range(nt):
        jt = int(jf[t]) - 1
        jtp1 = int(jf[t + 1]) - 1
        if nu > 1:
            mdp_p.append(np.asarray(b[jtp1, jt, :].ravel(), dtype=bool))
        else:
            mdp_p.append(np.array(True, dtype=bool))

    mdp = {
        "a": a,
        "b": [b],
        "X": mdp_x,
        "P": mdp_p,
    }
    return mdp, j
