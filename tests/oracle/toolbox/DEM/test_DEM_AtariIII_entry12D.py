"""Entry 12D isolate tests for ``spm_MDP_VB_XXX.m`` generation core (~750–851).

Scope of this subentry:
- path/state sampling via local ``spm_sample`` flow,
- control branch behavior, including explicit ``spm_action`` route.
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


def _bundle_for_12d_nonprocess() -> tuple[list[dict], dict]:
    T = 2
    nf = 1
    ns = 2
    nu = 2
    models = [{"u": np.zeros((nf, T), dtype=np.float64), "s": np.zeros((nf, T), dtype=np.float64)}]
    gp = [
        {
            "E": [np.array([[0.2], [0.8]], dtype=np.float64)],
            "D": [np.array([[0.7], [0.3]], dtype=np.float64)],
            "B": [np.ones((ns, ns, nu), dtype=np.float64) * 0.5],
        }
    ]
    bundle = {
        "Nm": 1,
        "T": T,
        "process": np.array([0.0], dtype=np.float64),
        "NF": np.array([nf], dtype=np.int64),
        "Nf": np.array([nf], dtype=np.int64),
        "Nu": np.array([[nu]], dtype=np.int64),
        "Um": [np.array([[1.0]], dtype=np.float64)],
        "V": [np.asarray([[1.0], [2.0]], dtype=np.float64)],
        "Q": [[[np.array([[0.5], [0.5]], dtype=np.float64) for _ in range(T)]]],
        "P": [[[np.array([[0.5], [0.5]], dtype=np.float64) for _ in range(T)]]],
        "B": [[[np.ones((ns, ns, nu), dtype=np.float64) * 0.5]]],
        "gp": gp,
        "id": [{"fu": np.array([1], dtype=np.int64)}],
        "Pu_carry": [np.array([[0.5], [0.5]], dtype=np.float64)],
    }
    # ``_vb_prior_QP_paths_states_one_model`` expects sparse-like ``V`` with ``toarray()``.
    class _DenseAsSparse:
        def __init__(self, arr: np.ndarray):
            self._arr = arr

        def toarray(self) -> np.ndarray:
            return self._arr

    bundle["V"] = [_DenseAsSparse(np.array([[1.0], [2.0]], dtype=np.float64))]
    return models, bundle


def test_entry12d_t0_samples_u_and_s_when_zero(monkeypatch) -> None:
    """~758–771 and ~832–849 at ``t==1``: zero ``u/s`` are sampled from ``GP.E`` and ``GP.D``."""
    models, bundle = _bundle_for_12d_nonprocess()
    monkeypatch.setattr(vbxxx_mod, "_spm_sample", lambda p: 1)
    vbxxx_mod._vb_generation_paths_states_share(models, bundle, t_idx=0, M_row=np.array([1], dtype=np.int64))
    assert float(models[0]["u"][0, 0]) == 1.0
    assert float(models[0]["s"][0, 0]) == 1.0


def test_entry12d_tgt1_propagates_u_and_uses_control_branch(monkeypatch) -> None:
    """~760–764 + ~822–824 at ``t>1``: ``u(:,t)`` propagates then implicit control updates ``u(:,t-1)``."""
    models, bundle = _bundle_for_12d_nonprocess()
    models[0]["u"][0, 0] = 2.0
    models[0]["s"][0, 0] = 1.0

    # First call (for propagated u at t_idx=1): return 2; second call (implicit control): return 1; third (state): 1
    seq = iter([2, 1, 1])
    monkeypatch.setattr(vbxxx_mod, "_spm_sample", lambda p: int(next(seq)))
    vbxxx_mod._vb_generation_paths_states_share(models, bundle, t_idx=1, M_row=np.array([1], dtype=np.int64))

    # propagated path at current time
    assert float(models[0]["u"][0, 1]) == 2.0
    # control write to previous column
    assert float(models[0]["u"][0, 0]) == 1.0
    # state sampled at current time
    assert float(models[0]["s"][0, 1]) == 1.0


def test_entry12d_process_branch_calls_spm_action(monkeypatch) -> None:
    """~812–816: process branch routes through explicit ``spm_action``."""
    T = 2
    nf = 1
    ns = 2
    models = [
        {
            "u": np.ones((nf, T), dtype=np.float64),
            "s": np.ones((nf, T), dtype=np.float64),
            "GB": [np.ones((ns, ns, 2), dtype=np.float64)],
            "GV": np.array([[1.0], [2.0]], dtype=np.float64),
            "id": {"A": [np.array([1], dtype=np.int64)]},
            "chi": 512.0,
        }
    ]
    bundle = {
        "process": np.array([1.0], dtype=np.float64),
        "T": T,
        "Nf": np.array([nf], dtype=np.int64),
        "Q": [[[np.array([[0.5], [0.5]], dtype=np.float64) for _ in range(T)]]],
        "A": [[np.ones((2, ns), dtype=np.float64)]],
    }
    called = {"n": 0}

    def _fake_action(md, A_list, Q_slice, t_arg):
        called["n"] += 1
        assert int(t_arg) == 1
        assert len(Q_slice) == 1
        return md

    monkeypatch.setattr(vbxxx_mod, "_spm_action", _fake_action)
    vbxxx_mod._vb_gen_control_one_model(0, models, bundle, t_idx=1)
    assert called["n"] == 1


def test_entry12d_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12D")
    if h is None:
        pytest.skip("MATLAB subentry 12D not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    models = copy.deepcopy(in_obj["models"])
    bundle = copy.deepcopy(in_obj["bundle"])
    vbxxx_mod._vb_generation_paths_states_share(
        models,
        bundle,
        t_idx=int(in_obj["t_idx"]),
        M_row=np.asarray(in_obj["M_row"], dtype=np.int64),
    )
    assert_deep_exact_equal(in_obj, h["in"], "12D.in")
    assert_deep_exact_equal({"models": models, "bundle": bundle}, h["out"], "12D.out")
