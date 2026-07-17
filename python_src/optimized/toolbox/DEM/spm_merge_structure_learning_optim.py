"""OPTIM1 — ``spm_merge_structure_learning`` (Tier B1 structural + B2v0 ``spm_unique_optim``)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse

from python_src.spm_cat import spm_cat
from python_src.spm_dir_norm import spm_dir_norm
from python_src.optimized.toolbox.DEM.spm_unique_optim import spm_unique_optim


def spm_merge_structure_learning_optim(O, MDP):
    o_cur = _as_o_cells(O)
    mdp_h = MDP

    for n in range(1, len(mdp_h) + 1):
        mdp_n = mdp_h[n - 1]
        sg: dict[int, np.ndarray] = {}
        n_cells: dict[tuple[int, int], Any] = {}
        ng = np.zeros(_numel_streams(mdp_n), dtype=np.int64)
        t_step = int(np.asarray(mdp_n["T"]).reshape(-1)[0])
        t_idx = _time_index(o_cur, t_step)

        for s in range(1, _numel_streams(mdp_n) + 1):
            g_stream = _stream_groups(mdp_n, s)
            ng[s - 1] = len(g_stream)

            for g in range(1, len(g_stream) + 1):
                gg = np.asarray(g_stream[g - 1], dtype=np.int64).ravel(order="F")
                fg = _cell_scalar(mdp_n["id"]["A"], int(np.min(gg)))
                mdp_loc, j = _spm_merge_fast(
                    _slice_o_rows(o_cur, gg),
                    _slice_cell_rows(mdp_n["a"], gg),
                    [_cell_entry(mdp_n["b"], fg)],
                )
                sg[s] = _sg_assign_row(sg.get(s), g, np.asarray(j, dtype=np.int64).ravel(order="F"))

                for k in range(gg.size):
                    _cell_set(mdp_n["a"], int(gg[k]), [mdp_loc["a"][k]])
                _cell_set(mdp_n["b"], int(fg), [mdp_loc["b"][0]])

                i_d = _id_parent_scalar(mdp_n["id"]["D"], int(fg))
                i_e = _id_parent_scalar(mdp_n["id"]["E"], int(fg))
                if i_d is not None:
                    for col_k, tk in enumerate(t_idx, start=1):
                        tk_i = int(tk)
                        n_cells[(int(i_d), int(col_k))] = mdp_loc["X"][tk_i - 1]
                        n_cells[(int(i_e), int(col_k))] = mdp_loc["P"][tk_i - 1]

        if n > 1:
            _link_streams_merge(mdp_h[n - 1], mdp_h[n - 2], ng, sg)

        for f in range(1, len(mdp_n["b"]) + 1):
            if _id_is_empty(mdp_n["id"]["D"], f):
                b_f = _unwrap_cell_payload(_cell_entry(mdp_n["b"], f))
                _cell_set(mdp_n["b"], f, [np.asarray(np.sum(np.asarray(b_f, dtype=np.float64)), dtype=np.float64)])
                for g in _id_a_children(mdp_n["id"]["A"], f):
                    a_g = _unwrap_cell_payload(_cell_entry(mdp_n["a"], g))
                    a_g = np.asarray(a_g, dtype=np.float64)
                    if sparse.issparse(a_g):
                        a_g = a_g.toarray()
                    _cell_set(mdp_n["a"], g, [np.sum(a_g, axis=1, keepdims=True)])

        n_cols = max((c for (_, c) in n_cells.keys()), default=0)
        if n_cols < 1:
            break
        o_cur = _n_cells_to_o(n_cells, n_cols)

    return mdp_h


def _spm_merge_fast(O, A, B):
    b_old = _unwrap_cell_payload(B[0]) if len(B) else np.zeros((0, 0), dtype=np.float64)
    b_old = np.asarray(b_old, dtype=np.float64)
    if b_old.ndim == 0:
        b_old = np.reshape(b_old, (1, 1, 1), order="F")
    if b_old.ndim == 1:
        b_old = b_old.reshape((0, 0, 1), order="F") if b_old.size == 0 else b_old.reshape((-1, 1, 1), order="F")
    if b_old.ndim == 2:
        b_old = b_old[:, :, None]

    ng = len(A)
    ns, _, nu = _matlab_size3(b_old)

    a_old: list[np.ndarray] = []
    for g in range(ng):
        ag = _unwrap_cell_payload(A[g])
        ag = np.asarray(ag, dtype=np.float64)
        if ag.ndim == 1:
            ag = ag.reshape((-1, 1), order="F")
        if ag.ndim == 0:
            ag = np.reshape(ag, (1, 1), order="F")
        na = int(ag.shape[0]) if ag.size else 0
        o0 = np.asarray(O[g][0], dtype=np.float64)
        no = int(o0.shape[0]) if o0.ndim > 0 else 1
        a_mat = np.zeros((no, ns), dtype=np.float64)
        if na > 0 and ns > 0:
            a_mat[:na, :] = ag
        a_old.append(a_mat)

    combined = [[a_old[g]] + list(O[g]) for g in range(ng)]
    i, j = spm_unique_optim(combined)
    jv = np.asarray(j, dtype=np.int64).ravel(order="F")
    iv = np.asarray(i, dtype=np.int64).ravel(order="F")
    r = sparse.csr_matrix(
        (
            np.ones(jv.size, dtype=np.float64),
            (np.arange(jv.size, dtype=np.int64), jv - 1),
        ),
        shape=(jv.size, iv.size),
    )

    a = []
    for g in range(ng):
        row = [[a_old[g]] + list(O[g])]
        ag = spm_cat(row) @ r
        if sparse.issparse(ag):
            ag = ag.toarray()
        a.append(np.asarray(ag, dtype=np.float64))

    j_new = jv[ns:]
    nn = int(iv.size)
    nt = int(j_new.size - 1)
    b = np.zeros((nn, nn, nu), dtype=np.float64)
    if ns > 0:
        b[:ns, :ns, :] = b_old

    for t in range(nt):
        jt = int(j_new[t]) - 1
        jtp1 = int(j_new[t + 1]) - 1
        seg = np.asarray(b[jtp1, jt, :]).ravel(order="F")
        nz = np.flatnonzero(seg)
        if nz.size:
            u = int(nz[0])
            b[jtp1, jt, u] = b[jtp1, jt, u] + 1.0
        else:
            has_succ = np.any(b[:, jt, :], axis=0)
            empty = np.flatnonzero(~has_succ)
            if empty.size:
                u = int(empty[0])
                b[jtp1, jt, u] = 1.0
            else:
                b = np.concatenate([b, np.zeros((nn, nn, 1), dtype=np.float64)], axis=2)
                b[jtp1, jt, b.shape[2] - 1] = 1.0

    ns2 = int(b.shape[1])
    nu2 = int(b.shape[2])
    x0 = np.zeros((ns2, 1), dtype=bool)
    mdp_x = []
    for t in range(nt + 1):
        s = x0.copy()
        s[int(j_new[t]) - 1, 0] = True
        mdp_x.append(s)
    mdp_x = mdp_x[:nt]

    mdp_p = []
    for t in range(nt):
        if nu2 > 1:
            p = np.asarray(b[int(j_new[t + 1]) - 1, int(j_new[t]) - 1, :], dtype=bool).ravel(order="F")
            mdp_p.append(p)
        else:
            mdp_p.append(np.array(True, dtype=bool))

    mdp = {"a": a, "b": [b], "X": mdp_x, "P": mdp_p}
    return mdp, j_new


def _as_o_cells(O):
    """Reuse list-of-lists ``O`` when already cell-shaped (OPTIM1 low-risk)."""
    if isinstance(O, list):
        if not O:
            return []
        if isinstance(O[0], list):
            return O
    return [list(row) for row in O]


def _time_index(O, step: int) -> np.ndarray:
    n_cols = len(O[0]) if len(O) else 0
    if n_cols <= 1:
        return np.array([], dtype=np.int64)
    return np.arange(1, n_cols, max(int(step), 1), dtype=np.int64)


def _numel_streams(mdp_n: dict) -> int:
    g = mdp_n.get("G", {})
    if isinstance(g, dict):
        return len(g)
    return len(g)


def _stream_groups(mdp_n: dict, s: int):
    g = mdp_n.get("G", {})
    if isinstance(g, dict):
        return g[s]
    return g[s - 1]


def _slice_o_rows(O, rows_1based: np.ndarray):
    rows = np.asarray(rows_1based, dtype=np.int64).ravel(order="F")
    return [list(O[int(r) - 1]) for r in rows]


def _slice_cell_rows(cells: list, rows_1based: np.ndarray):
    rows = np.asarray(rows_1based, dtype=np.int64).ravel(order="F")
    return [_cell_entry(cells, int(r)) for r in rows]


def _cell_entry(cells: list, idx_1based: int):
    return cells[int(idx_1based) - 1]


def _cell_set(cells: list, idx_1based: int, value):
    while len(cells) < int(idx_1based):
        cells.append([])
    cells[int(idx_1based) - 1] = value


def _unwrap_cell_payload(x):
    if isinstance(x, list):
        if len(x) == 0:
            return np.zeros((0, 0), dtype=np.float64)
        if len(x) == 1:
            return x[0]
        return x
    return x


def _cell_scalar(cells: list, idx_1based: int) -> int:
    v = _cell_entry(cells, idx_1based)
    return int(np.asarray(v).ravel(order="F")[0])


def _id_parent_scalar(id_cells: list, idx_1based: int) -> int | None:
    v = _cell_entry(id_cells, idx_1based)
    a = np.asarray(v).ravel(order="F")
    if a.size < 1:
        return None
    return int(np.min(a))


def _id_is_empty(id_cells: list, idx_1based: int) -> bool:
    return np.asarray(_cell_entry(id_cells, idx_1based)).size == 0


def _id_a_children(id_a: list, f: int) -> list[int]:
    out = []
    for gi in range(1, len(id_a) + 1):
        v = np.asarray(_cell_entry(id_a, gi)).ravel(order="F")
        if v.size and int(v[0]) == int(f):
            out.append(gi)
    return out


def _sg_assign_row(sg_mat: np.ndarray | None, row_1based: int, j: np.ndarray) -> np.ndarray:
    row = int(row_1based) - 1
    jv = np.asarray(j, dtype=np.int64).ravel(order="F")
    if sg_mat is None:
        out = np.zeros((int(row_1based), jv.size), dtype=np.int64)
        out[row, : jv.size] = jv
        return out
    n_rows, n_cols = sg_mat.shape
    out = sg_mat
    if int(row_1based) > n_rows:
        out = np.pad(out, ((0, int(row_1based) - n_rows), (0, 0)), mode="constant")
    if jv.size != out.shape[1]:
        raise ValueError(
            f"sg row length mismatch: existing={out.shape[1]} new={jv.size} for row={row_1based}"
        )
    out[row, : jv.size] = jv
    return out


def _ss_get(ss_mat: list, si: int, sj: int, fi: int, fj: int) -> int:
    cell = ss_mat[int(si) - 1][int(sj) - 1]
    if isinstance(cell, dict):
        return int(cell[(int(fi), int(fj))])
    arr = np.asarray(cell)
    return int(arr[int(fi) - 1, int(fj) - 1])


def _link_streams_merge(mdp_n: dict, mdp_prev: dict, ng: np.ndarray, sg: dict[int, np.ndarray]) -> None:
    si = 1
    st = (np.flatnonzero(ng) + 1).tolist()
    for sj in st[1:]:
        fsi = [i + 1 for i, v in enumerate(mdp_n["sB"]) if v is not None and int(v) == int(si)]
        fsj = [i + 1 for i, v in enumerate(mdp_prev["sB"]) if v is not None and int(v) == int(sj)]
        fsi_col = {fi: idx for idx, fi in enumerate(fsi)}
        fsj_col = {fj: idx for idx, fj in enumerate(fsj)}
        t_cols = int(sg[si].shape[1])

        for fi in fsi:
            for fj in fsj:
                b_i = _unwrap_cell_payload(_cell_entry(mdp_n["b"], fi))
                b_j = _unwrap_cell_payload(_cell_entry(mdp_prev["b"], fj))
                b_i = np.asarray(b_i, dtype=np.float64)
                b_j = np.asarray(b_j, dtype=np.float64)
                if b_i.ndim == 0:
                    b_i = np.reshape(b_i, (1, 1, 1), order="F")
                if b_j.ndim == 0:
                    b_j = np.reshape(b_j, (1, 1, 1), order="F")
                if b_j.ndim == 2:
                    b_j = b_j[:, :, None]
                ni, _, _ = _matlab_size3(b_i)
                _, nj, nu = _matlab_size3(b_j)

                gi = _ss_get(mdp_prev["ss"]["D"], si, sj, fi, fj)
                gj = _ss_get(mdp_prev["ss"]["D"], sj, sj, fj, fj)
                a_norm = spm_dir_norm(_unwrap_cell_payload(_cell_entry(mdp_n["a"], gj)))
                if sparse.issparse(a_norm):
                    a_norm = a_norm.toarray()
                a_norm = np.asarray(a_norm, dtype=np.float64)
                a_old = _unwrap_cell_payload(_cell_entry(mdp_n["a"], gi))
                a_old = np.asarray(a_old, dtype=np.float64)
                a = np.zeros((nj, ni), dtype=np.float64)
                if a_old.size:
                    x, y = a_old.shape[:2]
                    a[:x, :y] = a_old
                fi_row = fsi_col[fi]
                fj_row = fsj_col[fj]
                for f in range(t_cols):
                    ii = int(sg[si][fi_row, f])
                    ij = int(sg[sj][fj_row, f])
                    a[:, ii - 1] = a[:, ii - 1] + a_norm[:, ij - 1]
                _cell_set(mdp_n["a"], gi, [a])

                gi = _ss_get(mdp_prev["ss"]["E"], si, sj, fi, fj)
                gj = _ss_get(mdp_prev["ss"]["E"], sj, sj, fj, fj)
                a_norm = spm_dir_norm(_unwrap_cell_payload(_cell_entry(mdp_n["a"], gj)))
                if sparse.issparse(a_norm):
                    a_norm = a_norm.toarray()
                a_norm = np.asarray(a_norm, dtype=np.float64)
                a_old = _unwrap_cell_payload(_cell_entry(mdp_n["a"], gi))
                a_old = np.asarray(a_old, dtype=np.float64)
                a = np.zeros((nu, ni), dtype=np.float64)
                if a_old.size:
                    x, y = a_old.shape[:2]
                    a[:x, :y] = a_old
                for f in range(t_cols):
                    ii = int(sg[si][fi_row, f])
                    ij = int(sg[sj][fj_row, f])
                    a[:, ii - 1] = a[:, ii - 1] + a_norm[:, ij - 1]
                _cell_set(mdp_n["a"], gi, [a])


def _n_cells_to_o(n_cells: dict[tuple[int, int], Any], n_cols: int):
    max_row = max((r for (r, _) in n_cells.keys()), default=0)
    out = [[] for _ in range(max_row)]
    for r in range(1, max_row + 1):
        for c in range(1, n_cols + 1):
            v = n_cells.get((r, c), np.zeros((0, 1), dtype=np.float64))
            a = np.asarray(v)
            if a.ndim == 1:
                a = a.reshape((-1, 1), order="F")
            if a.ndim == 0:
                a = np.reshape(a, (1, 1), order="F")
            out[r - 1].append(a)
    return out


def _matlab_size3(x: np.ndarray) -> tuple[int, int, int]:
    a = np.asarray(x)
    if a.ndim == 0:
        return 1, 1, 1
    if a.ndim == 1:
        if a.size == 0:
            return 0, 0, 1
        return 1, int(a.shape[0]), 1
    if a.ndim == 2:
        return int(a.shape[0]), int(a.shape[1]), 1
    return int(a.shape[0]), int(a.shape[1]), int(np.prod(a.shape[2:]))

