"""Pass 1 transliteration of spm_set_goals.m."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from python_src.spm_softmax import spm_softmax


def spm_set_goals(MDP, S, chi):
    mdp = MDP
    nm = len(mdp)

    s_arr = np.asarray(S, dtype=np.int64).ravel(order="F")
    chi_arr = np.asarray(chi, dtype=np.float64).ravel(order="F")
    if s_arr.size > 1:
        for i in range(s_arr.size):
            chi_i = chi_arr[i] if i < chi_arr.size else chi_arr[-1]
            mdp = spm_set_goals(mdp, int(s_arr[i]), float(chi_i))
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
    pd = np.asarray([v for v in pd.tolist() if int(v) in set(ps.tolist())], dtype=np.int64)
    pe = np.asarray([v for v in pe.tolist() if int(v) in set(ps.tolist())], dtype=np.int64)

    ns_top = int(np.asarray(_unwrap_cell(mdp[m - 1]["b"][0])).shape[0])
    for si in range(1, ns_top + 1):
        if pd.size:
            a_pd = np.asarray(_unwrap_cell(_cell_1based(mdp[m - 1]["a"], int(pd[0]))), dtype=np.float64)
            a_pe = np.asarray(_unwrap_cell(_cell_1based(mdp[m - 1]["a"], int(pe[0]))), dtype=np.float64)
            x = [int(np.argmax(a_pd[:, si - 1]) + 1)]
            u = int(np.argmax(a_pe[:, si - 1]) + 1)
        else:
            x = [1]
            u = 1

        sf = np.flatnonzero(_as_int_vector(mdp[m - 2]["sB"]) == s_stream)
        b_parent = np.asarray(_unwrap_cell(mdp[m - 2]["b"][int(sf[0])]), dtype=np.float64)
        for _r in range(2, int(mdp[m - 1]["T"]) + 1):
            j = int(np.argmax(b_parent[:, x[-1] - 1, u - 1]) + 1)
            x.append(j)

        s_levels: dict[int, list[int]] = {m - 1: x}

        for n in range(m - 1, 1, -1):
            s_levels[n - 1] = []
            sf_n = np.flatnonzero(_as_int_vector(mdp[n - 2]["sB"]) == s_stream)
            sg_n = np.flatnonzero(_as_int_vector(mdp[n - 1]["sA"]) == s_stream)
            for t in range(len(s_levels[n])):
                a1 = np.asarray(_unwrap_cell(mdp[n - 1]["a"][int(sg_n[0])]), dtype=np.float64)
                a2 = np.asarray(_unwrap_cell(mdp[n - 1]["a"][int(sg_n[1])]), dtype=np.float64)
                st = int(s_levels[n][t])
                x_t = [int(np.argmax(a1[:, st - 1]) + 1)]
                u_t = int(np.argmax(a2[:, st - 1]) + 1)

                b_n = np.asarray(_unwrap_cell(mdp[n - 2]["b"][int(sf_n[0])]), dtype=np.float64)
                for _r in range(2, int(mdp[n - 1]["T"]) + 1):
                    j = int(np.argmax(b_n[:, x_t[-1] - 1, u_t - 1]) + 1)
                    x_t.append(j)
                s_levels[n - 1].extend(x_t)

        o = []
        for t in range(len(s_levels[1])):
            sg1 = np.flatnonzero(_as_int_vector(mdp[0]["sA"]) == s_stream)
            a1 = np.asarray(_unwrap_cell(mdp[0]["a"][int(sg1[0])]), dtype=np.float64)
            j = int(np.argmax(a1[:, int(s_levels[1][t]) - 1]) + 1)
            o.append(j)

        if np.any(np.asarray(o, dtype=np.int64) > 1):
            if chi_s > 0:
                mdp[m - 1]["id"].setdefault("hid", []).append(int(si))
            elif chi_s < 0:
                mdp[m - 1]["id"].setdefault("cid", []).append(int(si))

    hid = mdp[m - 1]["id"].get("hid", [])
    if chi_s > 0 and len(hid):
        h = sparse.csr_matrix(
            (
                np.full(len(hid), float(chi_s), dtype=np.float64),
                (np.asarray(hid, dtype=np.int64) - 1, np.zeros(len(hid), dtype=np.int64)),
            ),
            shape=(ns_top, 1),
        ).toarray()
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
    out = []
    for v in values:
        if v is None:
            out.append(0)
        else:
            out.append(int(np.asarray(v, dtype=np.int64).ravel(order="F")[0]))
    return np.asarray(out, dtype=np.int64)


def _concat_cells(seq) -> np.ndarray:
    vals = []
    for item in seq:
        arr = np.asarray(item, dtype=np.int64).ravel(order="F")
        vals.extend([int(v) for v in arr.tolist()])
    return np.asarray(vals, dtype=np.int64)
