"""
Parents and children of MDP likelihood mappings (MATLAB-compatible).

Translated from spm_parents.m (Pass 1 faithful transliteration).
"""

from __future__ import annotations

import numpy as np


def _is_cell_q(Q) -> bool:
    """MATLAB iscell(Q)."""
    return isinstance(Q, (list, tuple))


def _s_from_q_cell(id_ff, Q) -> list:
    """MATLAB: for f=1:Ns, [~,m]=max(Q{id.ff(f)}); s{f}=m; (1-based m)."""
    ff = np.asarray(id_ff, dtype=np.int64).ravel()
    s: list = []
    for f in range(ff.size):
        qf = np.asarray(Q[ff[f] - 1], dtype=float).ravel()
        m = int(np.argmax(qf) + 1)
        s.append(m)
    return s


def _s_from_q_numeric(id_ff, Q) -> list:
    """MATLAB: s = num2cell(Q(id.ff)); — values become 1-based scalars in s."""
    qv = np.asarray(Q, dtype=float).ravel()
    ff = np.asarray(id_ff, dtype=np.int64).ravel()
    sub = qv[ff - 1]
    return [int(x) for x in sub.ravel().tolist()]


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


def spm_parents(id: dict, g: int, Q):
    """
    FORMAT [j,i] = spm_parents(id,g,Q)

    id — dict mimicking a MATLAB struct. Keys use MATLAB names ('A','ff','fg','gg').
    g — MATLAB 1-based index into id.A / id.fg / id.gg rows (same as MATLAB).
    """
    if "ff" in id:
        if _is_cell_q(Q):
            s = _s_from_q_cell(id["ff"], Q)
        else:
            s = _s_from_q_numeric(id["ff"], Q)

        if "fg" in id:
            fg = id["fg"]
            if isinstance(fg, np.ndarray):
                cols = np.array(s, dtype=np.int64)
                j = np.asarray(fg[g - 1, cols - 1])
            else:
                j = _cell_multi_get(fg[g - 1], s)
        else:
            j = id["A"][g - 1]

        if "gg" in id:
            gg = id["gg"]
            if isinstance(gg, np.ndarray):
                cols = np.array(s, dtype=np.int64)
                i = np.asarray(gg[g - 1, cols - 1])
            else:
                i = _cell_multi_get(gg[g - 1], s)
        else:
            i = g

        return j, i

    j = id["A"][g - 1]
    i = g
    return j, i
