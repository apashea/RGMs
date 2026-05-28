"""Oracle: ``_vb_hierarchical_q_O_prev_ncols`` width for inherited parent ``Q.O`` rows."""

from __future__ import annotations

import numpy as np

from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_hierarchical_q_O_prev_ncols


def test_vb_hierarchical_q_O_prev_ncols_prefers_parent_ng_width():
    """666 cells @ 111 modalities × 6 cols — not 2 modalities × 333 cols."""
    flat = [np.zeros((1, 1), dtype=np.float64)] * 666
    assert _vb_hierarchical_q_O_prev_ncols(flat, ng=2) == 6


def test_vb_hierarchical_q_O_prev_ncols_child_only_row():
    """Small inner-only ``Q.O`` row stays on child ``Ng``."""
    flat = [np.zeros((1, 1), dtype=np.float64)] * 4
    assert _vb_hierarchical_q_O_prev_ncols(flat, ng=2) == 2


def test_vb_hierarchical_q_O_prev_ncols_matrix_shape():
    arr = np.zeros((10, 7), dtype=np.float64)
    assert _vb_hierarchical_q_O_prev_ncols(arr, ng=2) == 7
