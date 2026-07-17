"""Smoke test: OPTIM1 driver fork imports and Entry 1 completes."""

from __future__ import annotations

from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim


def test_run_dem_atariiii_optim_entry1():
    ctx = run_dem_atariiii_optim(entry_stop=1)
    assert isinstance(ctx, dict)
