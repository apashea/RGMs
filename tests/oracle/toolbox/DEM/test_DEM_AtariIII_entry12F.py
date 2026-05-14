"""Entry 12F isolate tests for ``spm_MDP_VB_XXX.m`` in-loop forwards/learning window (~1170–1453).

Scope of this subentry:
- `spm_forwards` call-site behavior and immediate policy/posterior updates,
- in-loop active learning updates (`qa/qb` and derived tensors),
- in-loop attentional/neural bookkeeping (`id.ig`, `sn`).
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


def _minimal_bundle_for_12f() -> dict:
    T = 3
    Ns = 2
    Nu = 2
    Np = 2
    return {
        "Nm": 1,
        "T": T,
        "Nf": np.array([1], dtype=np.int64),
        "Nu": np.array([[Nu]], dtype=np.int64),
        "Np": np.array([Np], dtype=np.int64),
        "Um": [np.array([[1.0]], dtype=np.float64)],
        "V": [type("_DenseAsSparse", (), {"toarray": lambda self: np.array([[1.0], [2.0]], dtype=np.float64)})()],
        "Q": [[[np.array([[0.6], [0.4]], dtype=np.float64) for _ in range(T)]]],
        "P": [[[np.array([[0.5], [0.5]], dtype=np.float64) for _ in range(T)]]],
        "B": [[[np.ones((Ns, Ns, Nu), dtype=np.float64) * 0.5]]],
        "A": [[np.array([[0.8, 0.2], [0.2, 0.8]], dtype=np.float64)]],
        "qa": [[np.ones((2, 2), dtype=np.float64) * 2.0]],
        "qb": [[np.ones((2, 2, 2), dtype=np.float64) * 2.0]],
        "W": [[None]],
        "K": [[None]],
        "I": [[None]],
        "R_policy": [np.zeros((Np, T), dtype=np.float64)],
        "w_policy": [np.zeros(T, dtype=np.float64)],
        "v_policy": [np.zeros(T, dtype=np.float64)],
        "gp": [{"E": [np.array([[0.5], [0.5]], dtype=np.float64)]}],
        "Pu_carry": [None],
        "id": [{"A": [np.array([1], dtype=np.int64)]}],
        "options_vb": vbxxx_mod._default_options_vb(),
        "sn": [[np.zeros((Ns, T, T), dtype=np.float64)]],
    }


def test_entry12f_belief_after_forwards_updates_R_w_v_and_Pu() -> None:
    """~1276–1345: after forwards, policy priors/complexity shells update (`R`,`w`,`v`,`Pu`,`P`)."""
    bundle = _minimal_bundle_for_12f()
    G = np.array([[0.1], [0.2]], dtype=np.float64)
    G_out, Z = vbxxx_mod._vb_belief_after_forwards(
        mi=0, bundle=bundle, t_m=2, t_idx=1, G_m=G, alpha=512.0
    )
    assert np.asarray(G_out).shape == (2, 1)
    assert np.isfinite(float(Z))
    assert np.asarray(bundle["R_policy"][0])[:, 1].shape == (2,)
    assert np.isfinite(bundle["w_policy"][0][1])
    assert np.isfinite(bundle["v_policy"][0][1])
    assert bundle["Pu_carry"][0] is not None
    # controlled factor gets a populated path prior at current t
    assert np.asarray(bundle["P"][0][0][1], dtype=np.float64).shape == (2, 1)


def test_entry12f_active_learning_updates_qa_qb_and_tensors() -> None:
    """~1349–1409: active in-loop learning updates likelihood/transition concentration tensors."""
    bundle = _minimal_bundle_for_12f()
    models = [{"a": [bundle["qa"][0][0].copy()], "b": [bundle["qb"][0][0].copy()], "A": [bundle["A"][0][0].copy()], "B": [bundle["B"][0][0].copy()]}]
    # outcome observation for g=1 at t=2
    bundle["O"] = [[[np.array([[1.0], [0.0]], dtype=np.float64), np.array([[1.0], [0.0]], dtype=np.float64), np.array([[1.0], [0.0]], dtype=np.float64)]]]
    vbxxx_mod._vb_active_learning_in_loop(mi=0, models=models, bundle=bundle, t_idx=1, t_m=2)
    assert np.asarray(bundle["qa"][0][0], dtype=np.float64).sum() > 8.0
    assert np.asarray(bundle["qb"][0][0], dtype=np.float64).sum() > 16.0
    assert bundle["W"][0][0] is not None
    assert bundle["K"][0][0] is not None
    assert bundle["I"][0][0] is not None


def test_entry12f_in_loop_id_ig_and_sn_bookkeeping() -> None:
    """~1418–1431: `id.ig(t)=id.i` and `sn(:,i,t)=Q(:,i)` updates when `OPTIONS.N` is on."""
    bundle = _minimal_bundle_for_12f()
    bundle["options_vb"] = {**bundle["options_vb"], "N": 1}
    bundle["id"][0]["i"] = 2.0
    vbxxx_mod._vb_in_loop_id_ig_and_sn(mi=0, bundle=bundle, t_idx=1)
    ig = np.asarray(bundle["id"][0]["ig"], dtype=np.float64).ravel()
    assert ig.size == 3
    assert float(ig[1]) == 2.0
    sn = np.asarray(bundle["sn"][0][0], dtype=np.float64)
    Q = bundle["Q"][0][0]
    # at t_idx=1, sn(:,i,2nd-slice) mirrors each Q(:,i)
    np.testing.assert_allclose(sn[:, 0, 1], np.asarray(Q[0], dtype=np.float64).ravel(), rtol=1e-6, atol=1e-10)


def test_entry12f_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12F")
    if h is None:
        pytest.skip("MATLAB subentry 12F not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    models = copy.deepcopy(in_obj["models"])
    bundle = copy.deepcopy(in_obj["bundle"])
    vbxxx_mod._vb_belief_after_forwards(
        mi=int(in_obj["mi"]),
        bundle=bundle,
        t_m=int(in_obj["t_m"]),
        t_idx=int(in_obj["t_idx"]),
        G_m=np.asarray(in_obj["G_m"], dtype=np.float64),
        alpha=float(in_obj["alpha"]),
    )
    assert_deep_exact_equal(in_obj, h["in"], "12F.in")
    assert_deep_exact_equal({"models": models, "bundle": bundle}, h["out"], "12F.out")
