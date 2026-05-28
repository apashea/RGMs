"""Oracle: call-2 generative-process dtypes after ``loadmat`` restoration."""

from __future__ import annotations

import numpy as np

from python_src.toolbox.DEM.entry12_atari_calls import load_entry12_rdp_for_tag
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
    entry12_call2_gp_matlab_class_fixture_path,
    load_entry12_rdp_mat_nested_for_tag,
    restore_entry12_call2_gp_dtypes,
)
from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call_rdp_mat_path


def test_call2_gp_matlab_class_fixture_exists() -> None:
    p = entry12_call2_gp_matlab_class_fixture_path()
    assert p.is_file(), f"missing MATLAB GP class export: {p}"


def test_call2_ga_dtype_restore_matches_matlab_inventory() -> None:
    mat_p = entry12_atari_call_rdp_mat_path("rgms_atari_call2")
    nested = load_entry12_rdp_mat_nested_for_tag("rgms_atari_call2", mat_p)
    ga = nested["MDP"]["GA"]
    assert len(ga) == 111
    assert ga[0].dtype == bool
    assert ga[109].dtype == bool
    assert ga[110].dtype == np.float64
    assert np.all(np.diag(ga[110]) == 1.0)
    assert ga[110].dtype != bool


def test_load_entry12_rdp_for_tag_call2_preserves_gp_dtypes_through_checkx() -> None:
    rdp = load_entry12_rdp_for_tag("rgms_atari_call2")
    ga = rdp["MDP"]["GA"]
    assert ga[0].dtype == bool
    assert ga[110].dtype == np.float64


def test_vb_gp_a_outcome_column_accepts_1d_gp_column() -> None:
    """``GP.A{g}(:,ind)`` when ``loadmat`` yields a flat ``Nx1`` column (call 1 child GA)."""
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_gp_A_outcome_column

    ag = np.array([0.0, 0.0, 0.0, 0.0, 1.0])
    col = _vb_gp_A_outcome_column(ag, [0])
    assert col.shape == (5, 1)
    assert np.allclose(col.ravel(), ag)


def test_restore_is_idempotent_for_call2_fixture() -> None:
    mat_p = entry12_atari_call_rdp_mat_path("rgms_atari_call2")
    nested = load_entry12_rdp_mat_nested_for_tag("rgms_atari_call2", mat_p)
    before = [a.dtype for a in nested["MDP"]["GA"]]
    restore_entry12_call2_gp_dtypes(nested)
    after = [a.dtype for a in nested["MDP"]["GA"]]
    assert before == after
