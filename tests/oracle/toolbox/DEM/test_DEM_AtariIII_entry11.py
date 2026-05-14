"""Entry 11 — isolated driver smoke for DEM_AtariIII (`spm_set_costs` → `spm_mdp2rdp`, `RDP.T`)."""

from __future__ import annotations

import os
import time

import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import get_dem_atariiii_run_last_label, run_dem_atariiii


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


def test_DEM_AtariIII_entry11_run_deadline_message():
    """Expired ``RGMS_ATARI_RUN_DEADLINE_MONO`` aborts with the documented timeout string and last-operation label."""
    deadline_keys = ("RGMS_ATARI_RUN_DEADLINE_MONO", "RGMS_ATARI_RUN_DEADLINE_MINUTES")
    old = {k: os.environ.get(k) for k in deadline_keys}
    try:
        if "RGMS_ATARI_RUN_DEADLINE_MINUTES" in os.environ:
            del os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"]
        os.environ["RGMS_ATARI_RUN_DEADLINE_MONO"] = str(time.perf_counter() - 1.0)
        with pytest.raises(RuntimeError) as excinfo:
            run_dem_atariiii(entry_stop=1)
        msg = str(excinfo.value)
        assert "TIME LIMIT OF ? MINUTES EXCEEDED" in msg
        assert "Last call =" in msg
        assert get_dem_atariiii_run_last_label() in msg
    finally:
        for k in deadline_keys:
            if old[k] is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(old[k])
