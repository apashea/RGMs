"""Entry 12B isolate tests for ``spm_MDP_VB_XXX.m`` setup window (~261–394).

Scope of this subentry:
- model/process setup into ``GP`` and ``ID`` domains,
- dimension derivations (``Ng/Nf/Ns/Nu`` and ``NG/NF/NS/NU``),
- process priors ``GD``/``GE`` fallback behavior.
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
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_tensors_through_H


def _base_model_nonprocess() -> dict:
    A = [np.eye(2, dtype=np.float64)]
    B = [np.ones((2, 2, 1), dtype=np.float64) * 0.5]
    return {
        "T": 2,
        "A": A,
        "B": B,
        "D": [np.array([[0.5], [0.5]], dtype=np.float64)],
        "E": [np.array([[1.0]], dtype=np.float64)],
        "U": np.array([[0.0]], dtype=np.float64),
        "id": {"A": [np.array([1], dtype=np.int64)]},
    }


def _base_model_process(include_id: bool = True) -> dict:
    A = [np.eye(2, dtype=np.float64)]
    B = [np.ones((2, 2, 2), dtype=np.float64) * 0.25]
    md = {
        "T": 2,
        # model tensors are still used for Ng/Nf/No/Ns/Nu sizing
        "A": A,
        "B": B,
        "D": [np.array([[0.5], [0.5]], dtype=np.float64)],
        "E": [np.array([[0.5], [0.5]], dtype=np.float64)],
        "U": np.array([[1.0]], dtype=np.float64),
        # process tensors trigger process(m) == 1
        "GA": A,
        "GB": B,
        "GU": np.array([[1.0]], dtype=np.float64),
        "id": {"A": [np.array([1], dtype=np.int64)]},
    }
    if include_id:
        md["ID"] = {"g": [np.array([1], dtype=np.int64)], "A": [np.array([1], dtype=np.int64)]}
    return md


def test_entry12b_nonprocess_gp_and_id_mapping() -> None:
    """~333–347: non-process path uses model tensors and copies ``id`` to ``ID``."""
    md = _base_model_nonprocess()
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))
    assert int(out["process"][0]) == 0
    np.testing.assert_array_equal(np.asarray(out["gp"][0]["A"][0]), md["A"][0])
    np.testing.assert_array_equal(np.asarray(out["gp"][0]["B"][0]), md["B"][0])
    np.testing.assert_array_equal(np.asarray(out["gp"][0]["D"][0]), md["D"][0])
    np.testing.assert_array_equal(np.asarray(out["gp"][0]["E"][0]), md["E"][0])
    assert out["id"][0]["A"][0][0] == 1
    assert out["ID"][0]["A"][0][0] == 1


def test_entry12b_process_missing_ID_builds_default_domains() -> None:
    """~319–331: process path builds default ``ID.g`` and leading-factor ``ID.A`` when absent."""
    md = _base_model_process(include_id=False)
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))
    assert int(out["process"][0]) == 1
    assert "g" in out["ID"][0]
    assert "A" in out["ID"][0]
    assert len(out["ID"][0]["A"]) == 1
    np.testing.assert_array_equal(np.asarray(out["ID"][0]["A"][0]), np.array([1], dtype=np.int64))


def test_entry12b_process_priors_use_GD_GE_when_present() -> None:
    """~375–384: process priors ``GP.D`` / ``GP.E`` use provided ``GD`` / ``GE``."""
    md = _base_model_process(include_id=True)
    md["GD"] = [np.array([[0.9], [0.1]], dtype=np.float64)]
    md["GE"] = [np.array([[0.2], [0.8]], dtype=np.float64)]
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))
    np.testing.assert_allclose(np.asarray(out["gp"][0]["D"][0]), md["GD"][0], rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(np.asarray(out["gp"][0]["E"][0]), md["GE"][0], rtol=0.0, atol=1e-12)


def test_entry12b_process_priors_fallback_to_normalized_ones() -> None:
    """~377–387: absent ``GD``/``GE`` fallback to ``spm_norm(ones(...))`` by ``NS``/``NU``."""
    md = _base_model_process(include_id=True)
    out = _vb_tensors_through_H([md], nm=1, t_h=float(md["T"]))
    d0 = np.asarray(out["gp"][0]["D"][0], dtype=np.float64).ravel()
    e0 = np.asarray(out["gp"][0]["E"][0], dtype=np.float64).ravel()
    # GB has Ns=2 and Nu=2, so fallback is uniform over both.
    np.testing.assert_allclose(d0, np.array([0.5, 0.5]), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(e0, np.array([0.5, 0.5]), rtol=0.0, atol=1e-12)


def test_entry12b_handoff_capture_boundary_parity(dem_eng_entry12) -> None:
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    h = artifact["matlab_subentries"].get("12B")
    if h is None:
        pytest.skip("MATLAB subentry 12B not in capture yet — extend handoff builder.")
    in_obj = h["in"]
    out = _vb_tensors_through_H(copy.deepcopy(in_obj["models"]), nm=int(in_obj["nm"]), t_h=float(in_obj["t_h"]))
    assert_deep_exact_equal(in_obj, h["in"], "12B.in")
    assert_deep_exact_equal({"bundle": out}, h["out"], "12B.out")
