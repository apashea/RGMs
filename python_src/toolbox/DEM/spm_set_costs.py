"""Pass 1 transliteration of spm_set_costs.m."""

from __future__ import annotations

from typing import Any

import numpy as np

from python_src.spm_MDP_MI import spm_MDP_MI
from python_src.spm_dir_norm import spm_dir_norm
from python_src.spm_softmax import spm_softmax


def spm_set_costs(MDP: list[dict[str, Any]], S, chi):
    """MATLAB ``MDP = spm_set_costs(MDP,S,chi)``."""
    mdp = MDP
    nm = len(mdp)
    s_arr = np.asarray(S, dtype=np.float64).ravel(order="F")
    chi_arr = np.asarray(chi, dtype=np.float64).ravel(order="F")
    ns = int(s_arr.size)
    if ns > 1:
        for n in range(nm):
            if "C" in mdp[n]:
                del mdp[n]["C"]
        for s in range(ns):
            spm_set_costs(mdp, float(s_arr[s]), float(chi_arr[s]))
        return mdp

    s_stream = int(s_arr[0]) if ns else 1
    chi_s = float(chi_arr[0]) if chi_arr.size else 0.0

    C_blocks: list[np.ndarray | None] = [None] * (nm - 1)

    for m in range(1, nm):
        sb_m = _as_int_vector(mdp[m - 1]["sB"])
        fac_ix = np.flatnonzero(sb_m == s_stream)
        if fac_ix.size == 0:
            continue
        f_bi = int(fac_ix[0])
        b_sf = np.asarray(_unwrap_cell(mdp[m - 1]["b"][f_bi]), dtype=np.float64)
        n_rows = int(b_sf.shape[0])
        c = np.zeros((n_rows, 1), dtype=np.float64)

        for si in range(1, n_rows + 1):
            s_cell: dict[int, Any] = {}
            s_cell[m] = si

            if m >= 2:
                for n_ml in range(m, 1, -1):
                    s_cell[n_ml - 1] = []
                    sb_nm1 = _as_int_vector(mdp[n_ml - 2]["sB"])
                    sf_nm1 = np.flatnonzero(sb_nm1 == s_stream)[0]
                    sg = np.flatnonzero(_as_int_vector(mdp[n_ml - 1]["sA"]) == s_stream) + 1
                    sn = s_cell[n_ml]
                    sn_mat = np.asarray(sn, dtype=np.float64)
                    if sn_mat.ndim == 0:
                        ncols = 1
                    else:
                        ncols = int(sn_mat.shape[1]) if sn_mat.ndim > 1 else int(sn_mat.size)

                    for t in range(1, ncols + 1):
                        st_idx = int(sn_mat.flat[t - 1]) if sn_mat.size else int(sn)
                        ag1 = np.asarray(
                            _unwrap_cell(mdp[n_ml - 1]["a"][int(sg[0]) - 1]), dtype=np.float64
                        )
                        ag2 = np.asarray(
                            _unwrap_cell(mdp[n_ml - 1]["a"][int(sg[1]) - 1]), dtype=np.float64
                        )
                        xi = int(np.argmax(ag1[:, st_idx - 1]) + 1)
                        ui = int(np.argmax(ag2[:, st_idx - 1]) + 1)
                        t_horiz = int(mdp[n_ml - 1]["T"])
                        x_row = np.zeros(t_horiz, dtype=np.float64)
                        x_row[0] = float(xi)
                        b_prev = np.asarray(
                            _unwrap_cell(mdp[n_ml - 2]["b"][sf_nm1]), dtype=np.float64
                        )
                        for r in range(2, t_horiz + 1):
                            jj = int(
                                np.argmax(b_prev[:, int(x_row[r - 2]) - 1, ui - 1]) + 1
                            )
                            x_row[r - 1] = float(jj)
                        prev = s_cell[n_ml - 1]
                        if isinstance(prev, list) and len(prev) == 0:
                            s_cell[n_ml - 1] = np.reshape(x_row, (1, -1), order="F")
                        else:
                            prev_arr = np.asarray(prev, dtype=np.float64)
                            if prev_arr.size == 0:
                                s_cell[n_ml - 1] = np.reshape(x_row, (1, -1), order="F")
                            else:
                                if prev_arr.ndim == 1:
                                    prev_arr = prev_arr.reshape(1, -1, order="F")
                                xcol = np.reshape(x_row, (1, -1), order="F")
                                s_cell[n_ml - 1] = np.concatenate(
                                    (prev_arr, xcol), axis=1, dtype=np.float64
                                )

            sg1 = np.flatnonzero(_as_int_vector(mdp[0]["sA"]) == s_stream)
            a0 = np.asarray(_unwrap_cell(mdp[0]["a"][int(sg1[0])]), dtype=np.float64)
            s1 = s_cell[1]
            s1m = np.asarray(s1, dtype=np.float64)
            if s1m.ndim == 0:
                nct = 1
            else:
                nct = int(s1m.shape[1]) if s1m.ndim > 1 else int(s1m.size)
            o = np.zeros(max(nct, 1), dtype=np.float64)
            for t in range(1, nct + 1):
                v = int(s1m.flat[t - 1]) if s1m.size else int(s1m)
                o[t - 1] = float(np.argmax(a0[:, v - 1]) + 1)

            c[si - 1, 0] = float(np.any(o > 1))

        C_blocks[m - 1] = c

    for n in range(nm):
        ng = len(mdp[n]["a"])
        nf = len(mdp[n]["b"])
        if "U" not in mdp[n]:
            mdp[n]["U"] = np.zeros((1, nf), dtype=bool)
        if "C" not in mdp[n]:
            mdp[n]["C"] = []
            for g in range(ng):
                ag = np.asarray(_unwrap_cell(mdp[n]["a"][g]), dtype=np.float64)
                mdp[n]["C"].append(
                    spm_dir_norm(np.ones((ag.shape[0], 1), dtype=np.float64))
                )

    for n in range(2, nm + 1):
        sb_nm1 = _as_int_vector(mdp[n - 2]["sB"])
        d_row = mdp[n - 2]["id"]["D"]
        pf_list: list[int] = []
        for fi in range(len(d_row)):
            if sb_nm1[fi] == s_stream:
                arr = np.asarray(
                    _unwrap_cell(_cell_1based(d_row, fi + 1)), dtype=np.int64
                ).ravel(order="F")
                pf_list.extend([int(x) for x in arr.tolist()])
        pf = np.asarray(pf_list, dtype=np.int64)
        ps = np.flatnonzero(_as_int_vector(mdp[n - 1]["sA"]) == 1) + 1
        pg = np.intersect1d(ps, pf)
        u_prod: list[float] = [1.0]
        for g in pg.tolist():
            ag = np.asarray(_unwrap_cell(mdp[n - 1]["a"][int(g) - 1]), dtype=np.float64)
            if _spm_mdp_mi_scalar(ag) > 1.0 / 32.0:
                f_pol = _cell_scalar_int(mdp[n - 1]["id"]["A"][int(g) - 1])
                b_f = np.asarray(
                    _unwrap_cell(mdp[n - 1]["b"][int(f_pol) - 1]), dtype=np.float64
                )
                nu = int(b_f.shape[2])
                if float(np.prod(np.asarray(u_prod, dtype=np.float64))) * float(nu) < 8.0:
                    u_row = np.asarray(mdp[n - 1]["U"], dtype=bool)
                    if u_row.ndim == 2 and u_row.shape[0] == 1:
                        u_row = u_row.ravel()
                    if u_row.size < f_pol:
                        u_row = np.resize(u_row, max(f_pol, len(mdp[n - 1]["b"])))
                    u_new = np.asarray(u_row, dtype=bool).copy()
                    u_new[int(f_pol) - 1] = True
                    if u_new.ndim == 1:
                        mdp[n - 1]["U"] = u_new.reshape(1, -1)
                    else:
                        mdp[n - 1]["U"] = u_new
                    u_prod.append(float(nu))
            c_prev = C_blocks[n - 2]
            if c_prev is None:
                continue
            mdp[n - 1]["C"][int(g) - 1] = spm_softmax(c_prev, chi_s)

    return mdp


def _spm_mdp_mi_scalar(ag) -> float:
    """MATLAB ``spm_MDP_MI(a)`` scalar MI term only (Python returns tuple)."""
    out = spm_MDP_MI(np.asarray(ag, dtype=np.float64))
    v = out[0] if isinstance(out, tuple) else out
    return float(np.real(np.asarray(v, dtype=np.float64)).reshape(-1)[0])


def _cell_1based(cells: list[Any], idx_1based: int):
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
