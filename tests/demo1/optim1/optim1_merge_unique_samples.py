"""Build ``_spm_merge_fast`` ``combined`` tensors and ``spm_unique`` refs for OPTIM1 B2 capture."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_merge_structure_learning import (
    _cell_entry,
    _cell_scalar,
    _matlab_size3,
    _numel_streams,
    _slice_cell_rows,
    _slice_o_rows,
    _stream_groups,
    _unwrap_cell_payload,
)
from python_src.toolbox.DEM.spm_information_distance import spm_information_distance
from python_src.toolbox.DEM.spm_unique import spm_unique


def build_merge_fast_combined(O: list, A: list, B: list) -> list:
    """Reproduce ``combined`` passed to ``spm_unique`` inside fidelity ``_spm_merge_fast``."""
    b_old = _unwrap_cell_payload(B[0]) if len(B) else np.zeros((0, 0), dtype=np.float64)
    b_old = np.asarray(b_old, dtype=np.float64)
    if b_old.ndim == 0:
        b_old = np.reshape(b_old, (1, 1, 1), order="F")
    if b_old.ndim == 1:
        b_old = b_old.reshape((0, 0, 1), order="F") if b_old.size == 0 else b_old.reshape((-1, 1, 1), order="F")
    if b_old.ndim == 2:
        b_old = b_old[:, :, None]

    ng = len(A)
    ns, _, _ = _matlab_size3(b_old)

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

    return [[a_old[g]] + list(O[g]) for g in range(ng)]


def collect_merge_unique_samples(
    O: list,
    MDP: list[dict[str, Any]],
    *,
    max_samples: int = 5,
) -> list[dict[str, Any]]:
    """
    Walk fidelity merge level ``n=1`` and collect ``combined`` + ``spm_unique`` refs.

    Samples are taken in deterministic call order (stream ``s``, group ``g``).
    """
    o_cur = [list(row) for row in O]
    mdp_h = MDP
    samples: list[dict[str, Any]] = []

    mdp_n = mdp_h[0]
    for s in range(1, _numel_streams(mdp_n) + 1):
        g_stream = _stream_groups(mdp_n, s)
        for g in range(1, len(g_stream) + 1):
            if len(samples) >= int(max_samples):
                return samples
            gg = np.asarray(g_stream[g - 1], dtype=np.int64).ravel(order="F")
            fg = _cell_scalar(mdp_n["id"]["A"], int(np.min(gg)))
            o_rows = _slice_o_rows(o_cur, gg)
            a_rows = _slice_cell_rows(mdp_n["a"], gg)
            b_cell = [_cell_entry(mdp_n["b"], fg)]
            combined = build_merge_fast_combined(o_rows, a_rows, b_cell)
            i_ref, j_ref = spm_unique(copy.deepcopy(combined))
            d_ref, _ = spm_information_distance(copy.deepcopy(combined))
            samples.append(
                {
                    "stream_s": int(s),
                    "group_g": int(g),
                    "factor_fg": int(fg),
                    "ng": len(combined),
                    "n_columns": len(combined[0]) if combined else 0,
                    "combined": combined,
                    "i_ref": np.asarray(i_ref, dtype=np.int64).ravel(order="F"),
                    "j_ref": np.asarray(j_ref, dtype=np.int64).ravel(order="F"),
                    "D_ref": np.asarray(d_ref, dtype=np.float64),
                }
            )
    return samples
