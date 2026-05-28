"""Oracle: hierarchical ``Q.O`` Ng×T row append folds to same stacked matrix as legacy ``hstack``."""

from __future__ import annotations

import numpy as np

from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _vb_hierarchical_q_O_matrix_to_flat_cells,
    _vb_hierarchical_q_append_level,
    _vb_hierarchical_q_O_level_to_matrix,
)


def test_vb_hierarchical_q_O_matrix_append_matches_flat_concat_order():
    """Two child blocks (Ng=2, T=2) — matrix append equals direct flat row from combined matrix."""
    ng, no = 2, [3, 2]
    o1 = [
        [np.eye(3, 1), np.eye(2, 1)],
        [np.eye(3, 1) * 2.0, np.eye(2, 1) * 2.0],
    ]
    child1 = {"A": [np.zeros((3, 1)), np.zeros((2, 1))], "O": o1, "T": 2}
    qv: list = [None]
    _vb_hierarchical_q_append_level(qv, 0, child1, "O", 2)
    o2 = [
        [np.eye(3, 1) * 4.0, np.eye(2, 1) * 4.0],
        [np.eye(3, 1) * 5.0, np.eye(2, 1) * 5.0],
    ]
    child2 = {"A": child1["A"], "O": o2, "T": 2}
    _vb_hierarchical_q_append_level(qv, 0, child2, "O", 2)
    rows = qv[0]
    assert isinstance(rows, list) and len(rows) == ng and len(rows[0]) == 4
    mat = _vb_hierarchical_q_O_level_to_matrix(rows, t_child=4, ng=ng, no=no)
    assert isinstance(mat, np.ndarray) and int(mat.shape[1]) == 4
    m1 = _vb_hierarchical_q_O_level_to_matrix(o1, t_child=2, ng=ng, no=no)
    m2 = _vb_hierarchical_q_O_level_to_matrix(o2, t_child=2, ng=ng, no=no)
    expect_mat = np.asfortranarray(np.hstack([m1, m2]))
    assert np.allclose(mat, expect_mat), "Ng×T row append must fold to legacy matrix hstack"
