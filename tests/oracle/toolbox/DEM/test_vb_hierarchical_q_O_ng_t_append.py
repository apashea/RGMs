"""Oracle: ``Q.O{L}`` append uses Ng×T ragged rows (MATLAB ``cell(Ng,T)``), not one stacked matrix."""

from __future__ import annotations

import numpy as np

from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _vb_hierarchical_q_append_level,
    _vb_hierarchical_q_O_is_ng_t_rows,
)


def test_q_O_ng_t_append_hstacks_time_on_each_modality_row() -> None:
    qv: list = [None]
    child1 = {
        "A": [np.ones((2, 1)), np.ones((3, 1))],
        "O": [
            [np.array([[1.0], [0.0]], dtype=np.float64), np.array([[0.0], [1.0], [0.0]], dtype=np.float64)],
            [np.array([[0.0], [1.0]], dtype=np.float64), np.array([[1.0], [0.0], [0.0]], dtype=np.float64)],
        ],
        "T": 2,
    }
    _vb_hierarchical_q_append_level(qv, 0, child1, "O", 2)
    child2 = {
        "A": child1["A"],
        "O": [
            [np.array([[0.0], [1.0]], dtype=np.float64), np.array([[1.0], [0.0], [0.0]], dtype=np.float64)],
            [np.array([[1.0], [0.0]], dtype=np.float64), np.array([[0.0], [1.0], [0.0]], dtype=np.float64)],
        ],
        "T": 2,
    }
    _vb_hierarchical_q_append_level(qv, 0, child2, "O", 2)
    level = qv[0]
    assert _vb_hierarchical_q_O_is_ng_t_rows(level)
    assert len(level) == 2
    assert len(level[0]) == 4
    assert len(level[1]) == 4
    assert float(level[0][0][0]) == 1.0
    assert float(level[0][2][0]) == 0.0
