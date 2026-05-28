"""Oracle: hierarchical ``mdp.Q`` stores Ng×T nested grids / matrices, not flat ``(:)`` rows."""

from __future__ import annotations

import numpy as np

from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _vb_hierarchical_q_O_level_to_matrix,
    _vb_hierarchical_q_append_level,
    _vb_hierarchical_update_parent_Q_from_child,
)


def test_q_Y_level_stored_as_nested_grid_not_flat_row() -> None:
    parent: dict = {"Q": {"Y": []}}
    child = {
        "L": 1,
        "T": 2,
        "Y": [
            [np.array([[1.0]], dtype=np.float64), np.array([[2.0]], dtype=np.float64)],
            [np.array([[3.0]], dtype=np.float64), np.array([[4.0]], dtype=np.float64)],
        ],
    }
    _vb_hierarchical_update_parent_Q_from_child(parent, child)
    y0 = parent["Q"]["Y"][0]
    assert isinstance(y0, list) and len(y0) == 2
    assert isinstance(y0[0], list) and len(y0[0]) == 2
    assert float(np.asarray(y0[0][0]).ravel()[0]) == 1.0


def test_q_O_level_stored_as_ng_t_ragged_rows() -> None:
    qv: list = []
    child = {
        "L": 1,
        "T": 2,
        "A": [np.ones((3, 1), dtype=np.float64), np.ones((2, 1), dtype=np.float64)],
        "O": [
            [np.array([[1.0], [0.0], [0.0]], dtype=np.float64), np.array([[0.0], [1.0], [0.0]], dtype=np.float64)],
            [np.array([[0.0], [1.0]], dtype=np.float64), np.array([[1.0], [0.0]], dtype=np.float64)],
        ],
    }
    _vb_hierarchical_q_append_level(qv, 0, child, "O", 2)
    assert len(qv) == 1
    level = qv[0]
    assert isinstance(level, list) and len(level) == 2
    assert all(isinstance(row, list) for row in level)
    assert len(level[0]) == 2
    mat = _vb_hierarchical_q_O_level_to_matrix(level, t_child=2, ng=2, no=[3, 2])
    assert int(mat.shape[1]) == 2
