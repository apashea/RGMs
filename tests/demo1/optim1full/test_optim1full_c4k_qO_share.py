"""C4k contract: optim ``Q.O`` hstack retains historical cell refs (MATLAB L1238)."""
from __future__ import annotations

import numpy as np

from python_src.optimized.toolbox.DEM.vb_hierarchical_optim import (
    _vb_hierarchical_q_O_ng_t_hstack_optim,
    _vb_hierarchical_q_append_level_optim,
)


def test_q_O_hstack_retains_historical_cell_identity() -> None:
    a0 = np.array([1.0, 0.0], dtype=np.float64)
    a1 = np.array([0.0, 1.0], dtype=np.float64)
    old = [[a0, a1]]
    b0 = np.array([0.5, 0.5], dtype=np.float64)
    new = [[b0]]
    out = _vb_hierarchical_q_O_ng_t_hstack_optim(old, new)
    assert len(out) == 1
    assert len(out[0]) == 3
    assert out[0][0] is a0
    assert out[0][1] is a1
    # New columns keep the leaves passed in (already detached by field_to_rows in production).
    assert out[0][2] is b0
    np.testing.assert_array_equal(out[0][2], b0)
    # Mutating the historical leaf must surface in Q.O (MATLAB cell aliasing).
    a0[0] = 9.0
    assert float(out[0][0][0]) == 9.0


def test_q_O_append_level_grows_width_with_shared_history() -> None:
    qv: list = [None]
    child1 = {
        "A": [np.ones((2, 1))],
        "O": [
            [np.array([1.0, 0.0], dtype=np.float64), np.array([0.0, 1.0], dtype=np.float64)],
        ],
        "T": 2,
    }
    _vb_hierarchical_q_append_level_optim(qv, 0, child1, "O", 2)
    first0 = qv[0][0][0]
    child2 = {
        "A": child1["A"],
        "O": [
            [np.array([0.25, 0.75], dtype=np.float64), np.array([0.75, 0.25], dtype=np.float64)],
        ],
        "T": 2,
    }
    _vb_hierarchical_q_append_level_optim(qv, 0, child2, "O", 2)
    assert len(qv[0][0]) == 4
    assert qv[0][0][0] is first0
