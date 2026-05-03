"""Entry 11 — isolated driver smoke for DEM_AtariIII (`spm_set_costs` → `spm_mdp2rdp`, `RDP.T`)."""

from __future__ import annotations

import os

import numpy as np

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii


def test_DEM_AtariIII_entry11_driver_smoke():
    """Fast training horizon / outer count; verify nested `RDP` and ledger horizon."""
    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=11)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    assert "MDP" in ctx and isinstance(ctx["MDP"], list)
    assert "RDP" in ctx and isinstance(ctx["RDP"], dict)
    assert np.isclose(float(ctx["RDP"]["T"]), 64.0, rtol=0.0, atol=1e-12)
    assert "L" in ctx["RDP"]
    assert "MDP" in ctx["RDP"]


def test_DEM_AtariIII_entries_1_to_11_python_smoke():
    """Same env pattern as Entry 9 cumulative smoke; stops at nested RDP."""
    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=11)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    assert "RDP" in ctx
    assert "P" in ctx
    assert np.asarray(ctx["P"], dtype=np.float64).shape[0] == 32
