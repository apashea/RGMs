"""Entry 12A isolate tests for ``spm_MDP_VB_XXX.m`` (~192–260): OPTIONS / ``spm_MDP_checkX`` / multi-trial.

Full-run MATLAB-vs-Python ``spm_MDP_checkX`` parity on Atari ``saved_rdp`` + ``_12A.mat`` lives in
``test_entry12_canonical_mats_oracle.py`` (``.mat`` capture lane — no handoff pickles).
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _vb_models_after_checkx,
    spm_MDP_VB_XXX,
)
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX


def _minimal_mdp_for_checkx() -> dict:
    return {
        "T": 2,
        "A": [np.eye(2, dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.25],
        "D": [np.ones((2, 1), dtype=np.float64) * 0.5],
        "E": [np.ones((1, 1), dtype=np.float64)],
        "U": np.array([[1.0]], dtype=np.float64),
        "s": np.array([[1.0, 1.0]], dtype=np.float64),
        "u": np.array([[1.0, 1.0]], dtype=np.float64),
    }


def test_entry12a_models_after_checkx_single_dict_and_column_grid() -> None:
    """Entry 12A: post-``spm_MDP_checkX`` model layout normalization."""
    d = {"x": 1}
    assert _vb_models_after_checkx(d) == [d]
    assert _vb_models_after_checkx([[d], [d]]) == [d, d]


def test_entry12a_full_mode_returns_assembled_output_after_checkx() -> None:
    """Entry 12A: single-epoch call returns assembled output in full mode."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {})
    assert isinstance(out, dict)
    assert "X" in out and "P" in out and "O" in out
    assert "_rgms_partial_v" not in out


def test_entry12a_multi_epoch_not_implemented_guard() -> None:
    """Entry 12A: ``size(MDP,2) > 1`` stays explicitly guarded."""
    m = _minimal_mdp_for_checkx()
    with pytest.raises(NotImplementedError, match="multiple epochs"):
        spm_MDP_VB_XXX([[m, copy.deepcopy(m)]], {})
