"""Entry 12E isolate tests for ``spm_MDP_VB_XXX.m`` outcomes/hierarchy window (~852–1170).

Scope of this subentry:
- `OPTIONS.O` outcome generation path,
- hierarchy pre-forward handling (child `S -> O` transcription and parent `O` updates).
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vbxxx_mod
from tests.oracle.toolbox.DEM._entry12_handoff_assert import assert_deep_exact_equal
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry12_handoff_capture import (
    entry12_handoff_capture_driver_params,
    load_or_build_entry12_handoff_capture,
)


def _bundle_for_outcome_generation() -> tuple[list[dict], dict]:
    T = 1
    ns = 2
    # one model / one modality / one factor
    models = [
        {
            "s": np.array([[1.0]], dtype=np.float64),
            "o": np.array([[0.0]], dtype=np.float64),
            "n": np.array([[1.0]], dtype=np.float64),
        }
    ]
    A = np.array([[0.8, 0.2], [0.1, 0.9]], dtype=np.float64)
    bundle = {
        "options_vb": {"O": 1},
        "ID": [{"A": [np.array([1], dtype=np.int64)]}],
        "gp": [{"A": [A]}],
        "O": [[[None]]],
        "Ng": np.array([1], dtype=np.int64),
        "No": np.array([[2]], dtype=np.int64),
        "T": T,
        "Q": [[[np.array([[0.7], [0.3]], dtype=np.float64)]]],
        "A": [[A]],
        "Nm": 1,
    }
    return models, bundle


def test_entry12e_options_o_generates_outcome_when_n_eq_m(monkeypatch) -> None:
    """~892–903: with `n(o,t)>0` and `n==m`, outcome is generated from ELBO softmax path."""
    models, bundle = _bundle_for_outcome_generation()

    # deterministic sample so test is stable
    monkeypatch.setattr(vbxxx_mod, "_spm_sample", lambda p: 1)
    vbxxx_mod._vb_generate_outcomes_if_options_o(
        models, bundle, t_idx=0, M_row=np.array([1], dtype=np.int64)
    )
    assert bundle["O"][0][0][0] is not None
    assert float(models[0]["o"][0, 0]) == 1.0


def test_entry12e_options_o_disabled_leaves_outcomes_unchanged() -> None:
    """~873 guard: if `OPTIONS.O==0`, outcome-generation block is skipped."""
    models, bundle = _bundle_for_outcome_generation()
    bundle["options_vb"] = {"O": 0}
    vbxxx_mod._vb_generate_outcomes_if_options_o(
        models, bundle, t_idx=0, M_row=np.array([1], dtype=np.int64)
    )
    assert bundle["O"][0][0][0] is None
    assert float(models[0]["o"][0, 0]) == 0.0


def test_entry12e_hierarchy_S_to_O_transcription_and_parent_mapping(monkeypatch) -> None:
    """~1138–1152 and ~1164–1175: child `S -> O`, then child posteriors map back to parent `O`."""
    child = {
        "T": 1,
        "L": 1,
        "S": np.array([[0.2, 0.8], [0.9, 0.1]], dtype=np.float64),
        "A": [np.ones((2, 2), dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.5],
        "D": [np.array([[0.5], [0.5]], dtype=np.float64)],
        "E": [np.array([[1.0]], dtype=np.float64)],
        "U": np.array([[0.0]], dtype=np.float64),
        "id": {"D": [np.array([1], dtype=np.int64)], "E": [np.array([], dtype=np.int64)]},
    }
    parent = {"MDP": [copy.deepcopy(child)], "Q": {"seed": 1}}
    models = [parent]
    bundle = {
        "Nm": 1,
        "T": 1,
        "Ng": np.array([1], dtype=np.int64),
        "O": [[[None]]],
        # Required by ~1060–1071 empirical-prior updates in hierarchy branch.
        "id": [{"A": [np.array([1], dtype=np.int64)]}],
        "A": [[np.array([[0.9, 0.1], [0.2, 0.8]], dtype=np.float64)]],
        "Q": [[[np.array([[0.5], [0.5]], dtype=np.float64)]]],
    }

    def _fake_child_solver(mdp_in, _options=None):
        # Ensure transcription happened before recurse
        assert "O" in mdp_in and np.asarray(mdp_in["O"]).shape[1] == 1
        return {
            "id": {"D": [np.array([1], dtype=np.int64)], "E": [np.array([], dtype=np.int64)]},
            "X": [np.array([[0.6], [0.4]], dtype=np.float64)],
            "P": [np.array([[1.0]], dtype=np.float64)],
            "Q": {"child": 1},
        }

    monkeypatch.setattr(vbxxx_mod, "spm_MDP_VB_XXX", _fake_child_solver)
    vbxxx_mod._vb_hierarchical_subordinate_outcomes(
        models, bundle, t_idx=0, M_row=np.array([1], dtype=np.int64), recurse_partial=False
    )
    np.testing.assert_allclose(np.asarray(bundle["O"][0][0][0], dtype=np.float64), np.array([[0.6], [0.4]]))


def test_entry12e_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12E")
    if h is None:
        pytest.skip("MATLAB subentry 12E not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    models = copy.deepcopy(in_obj["models"])
    bundle = copy.deepcopy(in_obj["bundle"])
    vbxxx_mod._vb_generate_outcomes_if_options_o(
        models,
        bundle,
        t_idx=int(in_obj["t_idx"]),
        M_row=np.asarray(in_obj["M_row"], dtype=np.int64),
    )
    assert_deep_exact_equal(in_obj, h["in"], "12E.in")
    assert_deep_exact_equal({"models": models, "bundle": bundle}, h["out"], "12E.out")
