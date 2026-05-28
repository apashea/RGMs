"""Entry 12C isolate tests for ``spm_MDP_VB_XXX.m`` tensor/policy shell (~395–743).

Scope of this subentry:
- tensor/prior shell allocation and normalization (``A/B/C/D/E/H`` with ``q*``/``p*``),
- novelty/ambiguity bookkeeping (``W/K/I`` and ``id.iK/iW/iH/iI``),
- policy preparation and update-order shell inputs (``GV/V/U`` + ``Np`` + ``spm_MDP_get_M`` call site prep).
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from tests.oracle.toolbox.DEM._entry12_handoff_assert import assert_deep_exact_equal
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry12_handoff_capture import (
    entry12_handoff_capture_driver_params,
    load_or_build_entry12_handoff_capture,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _default_options_vb,
    _vb_hyperparameters_mdp1,
    _vb_init_QXSP_outcomes_and_process,
    _vb_policy_depth_and_get_M,
    _vb_tensors_through_H,
)


def _mdp_for_12c() -> dict:
    # One model, one modality, two factors:
    # - factor 1 controllable (U=1, Nu=2)
    # - factor 2 uncontrollable (U=0, Nu=1)
    A0 = np.array([[0.8, 0.2], [0.1, 0.9]], dtype=np.float64)
    B1 = np.ones((2, 2, 2), dtype=np.float64) * 0.25
    B2 = np.ones((3, 3, 1), dtype=np.float64) / 3.0
    return {
        "T": 4,
        "A": [A0],
        "B": [B1, B2],
        "D": [np.array([[0.6], [0.4]], dtype=np.float64), np.array([[0.2], [0.3], [0.5]], dtype=np.float64)],
        "E": [np.array([[0.7], [0.3]], dtype=np.float64), np.array([[1.0]], dtype=np.float64)],
        "H": [np.array([[0.1], [0.9]], dtype=np.float64), np.array([[0.2], [0.8], [0.0]], dtype=np.float64)],
        "U": np.array([[1.0, 0.0]], dtype=np.float64),
        "id": {"A": [np.array([1], dtype=np.int64)]},
        "a": [np.array([[5.0, 1.0], [1.0, 5.0]], dtype=np.float64)],
        "b": [np.ones((2, 2, 2), dtype=np.float64) * 2.0, np.ones((3, 3, 1), dtype=np.float64) * 3.0],
    }


def test_entry12c_tensor_shell_shapes_and_normalization() -> None:
    """~395–588: allocates priors/tensors and normalizes ``A/B/C/D/E/H`` as specified."""
    md = _mdp_for_12c()
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))

    assert int(out["Nm"]) == 1
    assert int(out["T"]) == 4
    assert int(out["Ng"][0]) == 1
    assert int(out["Nf"][0]) == 2
    assert int(out["No"][0, 0]) == 2
    assert int(out["Ns"][0, 0]) == 2
    assert int(out["Ns"][0, 1]) == 3
    assert int(out["Nu"][0, 0]) == 2
    assert int(out["Nu"][0, 1]) == 1

    # A/B/D/E/H normalized columns
    A0 = np.asarray(out["A"][0][0], dtype=np.float64)
    B0 = np.asarray(out["B"][0][0], dtype=np.float64)
    D0 = np.asarray(out["D"][0][0], dtype=np.float64)
    E0 = np.asarray(out["E"][0][0], dtype=np.float64)
    H0 = np.asarray(out["H"][0][0], dtype=np.float64)
    np.testing.assert_allclose(A0.sum(axis=0), np.ones(A0.shape[1]), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(B0.sum(axis=0), np.ones(B0.shape[1:]), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(float(D0.sum()), 1.0, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(float(E0.sum()), 1.0, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(float(H0.sum()), 1.0, rtol=0.0, atol=1e-12)


def test_entry12c_w_k_i_and_domain_indices_are_built() -> None:
    """~465–613: controllable-parent novelty/ambiguity and domain index vectors are populated."""
    md = _mdp_for_12c()
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))

    id0 = out["id"][0]
    # modality 1 depends on factor 1, which is controllable -> K/W active
    assert len(np.asarray(id0["iK"]).ravel()) >= 1
    assert len(np.asarray(id0["iW"]).ravel()) >= 1
    # at least one factor has H and at least one has I from controllable b
    assert len(np.asarray(id0["iH"]).ravel()) >= 1
    assert len(np.asarray(id0["iI"]).ravel()) >= 1


def test_entry12c_iW_requires_mdp_a_field() -> None:
    """MATLAB ~470–472: ``W{m,g}`` only when ``isfield(MDP(m),'a')``; else ``id.iW`` empty."""
    md = _mdp_for_12c()
    out_with_a = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))
    assert len(np.asarray(out_with_a["id"][0]["iW"]).ravel()) >= 1

    md_no_a = copy.deepcopy(md)
    md_no_a.pop("a", None)
    out_no_a = _vb_tensors_through_H([md_no_a], nm=1, t_h=float(md["T"]))
    assert np.asarray(out_no_a["id"][0]["iW"]).ravel().size == 0
    assert len(np.asarray(out_no_a["id"][0]["iK"]).ravel()) >= 1


def test_entry12c_policy_shell_and_preallocation_inputs() -> None:
    """~619–743: ``GV/V/U/Np`` and ``N=min(N,T)`` + ``spm_MDP_get_M`` shell preallocation."""
    md = _mdp_for_12c()
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))

    # Policy shell from U/GU
    assert int(out["Np"][0]) >= 1
    assert out["V"][0].shape[1] == int(out["Nf"][0])
    assert out["GV"][0].shape[1] == int(out["NF"][0])
    assert 1 in np.asarray(out["id"][0]["fu"]).tolist()
    assert 1 in np.asarray(out["ID"][0]["fu"]).tolist()

    # spm_MDP_get_M prep shell
    hp = _vb_hyperparameters_mdp1(md)
    pol = _vb_policy_depth_and_get_M([md], out, hp)
    assert int(pol["N_policy_depth"]) == min(int(hp["N"]), int(out["T"]))
    assert pol["M_update"].shape[0] == int(out["T"])
    assert len(pol["BP"]) == int(out["Nm"])
    assert len(pol["IP"]) == int(out["Nm"])
    assert len(pol["R_policy"]) == int(out["Nm"])
    assert len(pol["w_policy"]) == int(out["Nm"])
    assert len(pol["v_policy"]) == int(out["Nm"])


def test_entry12c_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12C")
    if h is None:
        pytest.skip("MATLAB subentry 12C not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    models = copy.deepcopy(in_obj["models"])
    bundle = copy.deepcopy(in_obj["bundle_pre_12c"])
    hp = copy.deepcopy(in_obj["hp"])
    post = _vb_init_QXSP_outcomes_and_process(models, bundle, _default_options_vb(), float(hp["chi"]))
    bundle.update(post)
    bundle.update(_vb_policy_depth_and_get_M(models, bundle, hp))
    bundle["options_vb"] = _default_options_vb()
    assert_deep_exact_equal(in_obj, h["in"], "12C.in")
    assert_deep_exact_equal({"bundle": bundle}, h["out"], "12C.out")
