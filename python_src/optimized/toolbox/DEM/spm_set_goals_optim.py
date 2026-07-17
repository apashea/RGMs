"""OPTIM1 — ``spm_set_goals`` (Tier Cbv0 fork + Cb/Cd index/hoist opts)."""

from __future__ import annotations

import numpy as np

from python_src.spm_softmax import spm_softmax


def spm_set_goals_optim(MDP, S, chi):
    mdp = MDP
    nm = len(mdp)

    s_arr = np.asarray(S, dtype=np.int64).ravel(order="F")
    chi_arr = np.asarray(chi, dtype=np.float64).ravel(order="F")
    if s_arr.size > 1:
        for i in range(s_arr.size):
            chi_i = chi_arr[i] if i < chi_arr.size else chi_arr[-1]
            mdp = spm_set_goals_optim(mdp, int(s_arr[i]), float(chi_i))
        return mdp

    s_stream = int(s_arr[0]) if s_arr.size else 1
    chi_s = float(chi_arr[0]) if chi_arr.size else 0.0
    m = nm

    if chi_s >= 0:
        mdp[m - 1]["id"]["hid"] = []
        if "H" in mdp[m - 1]:
            del mdp[m - 1]["H"]
    if chi_s <= 0:
        mdp[m - 1]["id"]["cid"] = []

    sb_prev = _as_int_vector(mdp[m - 2]["sB"])
    sf_idx = np.flatnonzero(sb_prev == s_stream) + 1
    pd = _concat_cells([_cell_1based(mdp[m - 2]["id"]["D"], int(i)) for i in sf_idx.tolist()])
    pe = _concat_cells([_cell_1based(mdp[m - 2]["id"]["E"], int(i)) for i in sf_idx.tolist()])

    sb_m = _as_int_vector(mdp[m - 1]["sB"])
    i_first = int(np.flatnonzero(sb_m == 1)[0] + 1)
    id_a = [_cell_scalar_int(v) for v in mdp[m - 1]["id"]["A"]]
    ps = np.asarray([i + 1 for i, v in enumerate(id_a) if int(v) == i_first], dtype=np.int64)
    if ps.size:
        pd = pd[np.isin(pd, ps)]
        pe = pe[np.isin(pe, ps)]
    else:
        pd = np.asarray([], dtype=np.int64)
        pe = np.asarray([], dtype=np.int64)

    ns_top = int(np.asarray(_unwrap_cell(mdp[m - 1]["b"][0])).shape[0])
    sf_parent = np.flatnonzero(sb_prev == s_stream)
    b_parent = np.asarray(_unwrap_cell(mdp[m - 2]["b"][int(sf_parent[0])]), dtype=np.float64)
    t_top = int(mdp[m - 1]["T"])

    level_data: list[tuple[int, np.ndarray, np.ndarray, np.ndarray, int]] = []
    for n in range(m - 1, 0, -1):
        sb_n = _as_int_vector(mdp[n - 1]["sB"]) if n > 1 else None
        sa_n = _as_int_vector(mdp[n - 1]["sA"])
        sf_n = np.flatnonzero(sb_n == s_stream) if sb_n is not None else None
        sg_n = np.flatnonzero(sa_n == s_stream)
        if n == m - 1:
            continue
        a1_n = np.asarray(_unwrap_cell(mdp[n - 1]["a"][int(sg_n[0])]), dtype=np.float64)
        a2_n = np.asarray(_unwrap_cell(mdp[n - 1]["a"][int(sg_n[1])]), dtype=np.float64)
        b_n = np.asarray(_unwrap_cell(mdp[n - 2]["b"][int(sf_n[0])]), dtype=np.float64)
        level_data.append((n, a1_n, a2_n, b_n, int(mdp[n - 1]["T"])))

    sg1 = np.flatnonzero(_as_int_vector(mdp[0]["sA"]) == s_stream)
    a1_level0 = np.asarray(_unwrap_cell(mdp[0]["a"][int(sg1[0])]), dtype=np.float64)

    if pd.size:
        a_pd_top = np.asarray(_unwrap_cell(_cell_1based(mdp[m - 1]["a"], int(pd[0]))), dtype=np.float64)
        a_pe_top = np.asarray(_unwrap_cell(_cell_1based(mdp[m - 1]["a"], int(pe[0]))), dtype=np.float64)
    else:
        a_pd_top = a_pe_top = None

    for si in range(1, ns_top + 1):
        if a_pd_top is not None:
            x = [int(np.argmax(a_pd_top[:, si - 1]) + 1)]
            u = int(np.argmax(a_pe_top[:, si - 1]) + 1)
        else:
            x = [1]
            u = 1

        for _r in range(2, t_top + 1):
            j = int(np.argmax(b_parent[:, x[-1] - 1, u - 1]) + 1)
            x.append(j)

        s_levels: dict[int, list[int]] = {m - 1: x}

        for n, a1_n, a2_n, b_n, t_n in level_data:
            s_levels[n - 1] = []
            for t in range(len(s_levels[n])):
                st = int(s_levels[n][t])
                x_t = [int(np.argmax(a1_n[:, st - 1]) + 1)]
                u_t = int(np.argmax(a2_n[:, st - 1]) + 1)
                for _r in range(2, t_n + 1):
                    j = int(np.argmax(b_n[:, x_t[-1] - 1, u_t - 1]) + 1)
                    x_t.append(j)
                s_levels[n - 1].extend(x_t)

        o = []
        for t in range(len(s_levels[1])):
            j = int(np.argmax(a1_level0[:, int(s_levels[1][t]) - 1]) + 1)
            o.append(j)

        if np.any(np.asarray(o, dtype=np.int64) > 1):
            if chi_s > 0:
                mdp[m - 1]["id"].setdefault("hid", []).append(int(si))
            elif chi_s < 0:
                mdp[m - 1]["id"].setdefault("cid", []).append(int(si))

    hid = mdp[m - 1]["id"].get("hid", [])
    if chi_s > 0 and len(hid):
        h = np.zeros((ns_top, 1), dtype=np.float64)
        h[np.asarray(hid, dtype=np.int64) - 1, 0] = float(chi_s)
        mdp[m - 1]["H"] = [spm_softmax(h)]

    if chi_s > 0 and len(hid):
        mdp[m - 1]["U"] = 1
    if chi_s < 0 and len(mdp[m - 1]["id"].get("cid", [])):
        mdp[m - 1]["U"] = 1

    return mdp


def _cell_1based(cells, idx_1based: int):
    return cells[int(idx_1based) - 1]


def _cell_scalar_int(x) -> int:
    return int(np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")[0])


def _unwrap_cell(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _as_int_vector(values) -> np.ndarray:
    if isinstance(values, np.ndarray):
        return np.asarray(values, dtype=np.int64).ravel(order="F")
    if isinstance(values, (int, np.integer)):
        return np.asarray([int(values)], dtype=np.int64)
    if not isinstance(values, (list, tuple)):
        return np.asarray([int(np.asarray(values, dtype=np.int64).ravel(order="F")[0])], dtype=np.int64)
    out = np.empty(len(values), dtype=np.int64)
    for i, v in enumerate(values):
        if v is None:
            out[i] = 0
        elif isinstance(v, (int, np.integer)):
            out[i] = int(v)
        else:
            out[i] = int(np.asarray(v, dtype=np.int64).ravel(order="F")[0])
    return out


def _concat_cells(seq) -> np.ndarray:
    vals = []
    for item in seq:
        arr = np.asarray(item, dtype=np.int64).ravel(order="F")
        vals.extend([int(v) for v in arr.tolist()])
    return np.asarray(vals, dtype=np.int64)
