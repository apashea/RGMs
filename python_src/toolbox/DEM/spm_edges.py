"""
Parents and children of MDP likelihood mapping — domain combinations (MATLAB-compatible).

Translated from spm_edges.m (Pass 1 faithful transliteration).
"""

from __future__ import annotations

import numpy as np

from python_src.spm_cross import spm_cross
from python_src.toolbox.DEM.spm_index import spm_index


def _cell_multi_get(cur, indices_1based: list):
    """MATLAB id.fg{g}{s{:}} / id.gg{g}{s{:}} with 1-based indices in s."""
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


def spm_edges(id_dict: dict, g: int, Q):
    """
    FORMAT j, i, q = spm_edges(id, g, Q)

    Returns parents ``j`` and children ``i`` of likelihood mapping ``A{g}`` for
    each retained domain combination. ``q`` is the posterior over that grid
    (state-dependent branch) or ``1`` (state-independent).
    """
    g = int(g)
    if "ff" in id_dict:
        ff_list = np.asarray(id_dict["ff"], dtype=np.int64).ravel()
        nff = int(ff_list.size)
        r: list[np.ndarray] = []
        nr = np.zeros(nff, dtype=np.int64)
        for f in range(nff):
            ff = int(ff_list[f])
            qf = np.asarray(Q[ff - 1], dtype=float).ravel()
            mx = float(np.max(qf))
            idx_1b = np.where(qf > mx / 16.0)[0] + 1
            r.append(idx_1b.astype(np.float64))
            nr[f] = idx_1b.size

        r_cells = []
        for f in range(nff):
            ff = int(ff_list[f])
            qf = np.asarray(Q[ff - 1], dtype=float).ravel()
            ri = r[f].astype(np.int64)
            r_cells.append(qf[ri - 1])

        q_flat = np.asarray(spm_cross(*r_cells), dtype=float).reshape(-1, order="F")
        q_flat = q_flat / np.sum(q_flat)
        iq = np.where(q_flat > np.max(q_flat) / 16.0)[0] + 1
        q_sub = q_flat[iq - 1]

        j_out: list = []
        i_out: list = []
        for k in range(int(np.size(q_sub))):
            ind_arr = spm_index(nr, float(iq[k]))
            ind = np.asarray(ind_arr, dtype=float).ravel()
            s = [None] * nff
            for ff_i in range(nff):
                ri_f = r[ff_i].astype(np.int64)
                s[ff_i] = float(ri_f[int(ind[ff_i]) - 1])

            if "fg" in id_dict:
                fg = id_dict["fg"]
                if isinstance(fg, np.ndarray):
                    # MATLAB: id.fg(g, [s{:}]) — multiple indices along dim 2; higher
                    # dims default to first slice (see spm_edges.m).
                    cols = np.asarray(s, dtype=np.int64) - 1
                    tail = (0,) * max(0, fg.ndim - 2)
                    j_row = np.asarray(fg[(g - 1, cols) + tail])
                    j_out.append(np.atleast_1d(j_row))
                else:
                    j_out.append(_cell_multi_get(fg[g - 1], s))
            else:
                j_out.append(np.asarray(id_dict["A"][g - 1], dtype=float).copy())

            if "gg" in id_dict:
                gg = id_dict["gg"]
                if isinstance(gg, np.ndarray):
                    cols = np.asarray(s, dtype=np.int64) - 1
                    tail = (0,) * max(0, gg.ndim - 2)
                    i_row = np.asarray(gg[(g - 1, cols) + tail])
                    i_out.append(np.atleast_1d(i_row))
                else:
                    i_out.append(_cell_multi_get(gg[g - 1], s))
            else:
                i_out.append(float(g))

        return j_out, i_out, np.reshape(q_sub, (-1, 1))

    A = np.asarray(id_dict["A"], dtype=float, order="F")
    j = float(np.ravel(A, order="F")[g - 1])
    i = g
    q = 1.0
    return j, i, q
