"""Entry 12G / 12H handoff-capture boundary parity (post-loop accumulation through assembly).

Isolate checks align with ``spm_MDP_VB_XXX`` windows ~1454+ (post-loop through ~1691 assembly).
"""

from __future__ import annotations

import copy

import pytest

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vbxxx
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_hyperparameters_mdp1

from tests.oracle.toolbox.DEM._entry12_handoff_assert import assert_deep_exact_equal
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry12_handoff_capture import (
    entry12_handoff_capture_driver_params,
    load_or_build_entry12_handoff_capture,
)


@pytest.mark.slow
def test_entry12g_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12G")
    if h is None:
        pytest.skip("MATLAB subentry 12G not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    models = copy.deepcopy(in_obj["models"])
    bundle = copy.deepcopy(in_obj["bundle"])
    hp = _vb_hyperparameters_mdp1(models[0])
    vbxxx._vb_optional_backwards_replay(models, bundle, bundle["options_vb"])
    vbxxx._vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
    vbxxx._vb_posterior_predictive_Y(models, bundle, bundle["options_vb"])
    vbxxx._vb_reorganize_X_S_from_QP(bundle)
    vbxxx._vb_options_N_neural_simulated_responses(models, bundle, bundle["options_vb"])
    assert_deep_exact_equal(in_obj, h["in"], "12G.in")
    assert_deep_exact_equal({"models": models, "bundle": bundle}, h["out"], "12G.out")


@pytest.mark.slow
def test_entry12h_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12H")
    if h is None:
        pytest.skip("MATLAB subentry 12H not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    models = copy.deepcopy(in_obj["models"])
    bundle = copy.deepcopy(in_obj["bundle"])
    vbxxx._vb_assemble_mdp_results_1691(models, bundle)
    out_assembled = copy.deepcopy(models[0] if len(models) == 1 else models)
    assert_deep_exact_equal(in_obj, h["in"], "12H.in")
    assert_deep_exact_equal(
        {"assembled": out_assembled, "bundle": bundle}, h["out"], "12H.out"
    )
