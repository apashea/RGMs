"""DEMO1 Product A — wiring smoke for ``DEM_AtariIII_demo1_python.py``."""

from __future__ import annotations

import numpy as np

import python_src.toolbox.DEM.DEM_AtariIII_demo1_python as demo1_mod
from python_src.toolbox.DEM.DEM_AtariIII_demo1_python import run_dem_atariiii_demo1_python


def _fake_driver_ctx() -> dict:
    return {
        "RGB": np.zeros((3, 3), dtype=np.float64),
        "GDP": {"id": {"reward": 109, "contraint": 110}},
        "Nm": 2,
        "RDP": {"T": 64.0},
        "PDP": {"T": 64.0, "Q": {"o": [np.zeros((4, 64))]}},
    }


def test_demo1_python_wiring_compute_only(monkeypatch) -> None:
    def _fake_driver(entry_stop: int = 5) -> dict:
        assert entry_stop == 12
        return _fake_driver_ctx()

    monkeypatch.setattr(demo1_mod, "run_dem_atariiii", _fake_driver)
    monkeypatch.setattr(demo1_mod, "run_entry12plot", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no plot")))

    ctx = run_dem_atariiii_demo1_python(plot=False)
    assert "PDP" in ctx
    assert "entry12plot" not in ctx


def test_demo1_python_wiring_plot_tail(monkeypatch) -> None:
    monkeypatch.setattr(demo1_mod, "run_dem_atariiii", lambda entry_stop=5: _fake_driver_ctx())

    def _fake_plot(pdp, plot_ctx, **kwargs):
        return np.zeros((1, 1), dtype=np.uint8), np.zeros((1, 1), dtype=np.uint8), np.array([1]), None

    monkeypatch.setattr(demo1_mod, "run_entry12plot", _fake_plot)
    ctx = run_dem_atariiii_demo1_python(plot=True, save_png=False)
    assert "entry12plot" in ctx
