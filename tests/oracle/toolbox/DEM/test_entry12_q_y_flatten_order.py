"""Oracle: ``_vb_hierarchical_q_ot_grid_to_cell_row`` uses MATLAB ``(:)`` order ``o + t*Ng``."""

from __future__ import annotations

import numpy as np

from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_hierarchical_q_ot_grid_to_cell_row


def test_q_ot_grid_flatten_column_major_o_plus_t_ng() -> None:
    ng, t_count = 3, 2
    grid = [
        [np.asarray([[float(o + t * 10)]], dtype=np.float64) for t in range(t_count)]
        for o in range(ng)
    ]
    cells = _vb_hierarchical_q_ot_grid_to_cell_row(grid, t_child=t_count)
    assert len(cells) == ng * t_count
    for t in range(t_count):
        for o in range(ng):
            idx = o + t * ng
            assert float(np.asarray(cells[idx]).ravel()[0]) == float(o + t * 10)
