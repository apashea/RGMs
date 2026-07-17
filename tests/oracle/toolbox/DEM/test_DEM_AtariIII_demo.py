"""ENTRY DEMO1 — wiring smoke for ``DEM_AtariIII_demo.py`` (orchestration only; no full ledger)."""

from __future__ import annotations

import numpy as np

import python_src.toolbox.DEM.DEM_AtariIII_demo as demo_mod
from python_src.toolbox.DEM.DEM_AtariIII_demo import run_dem_atariiii_demo


def _fake_driver_ctx() -> dict:
    return {
        "RGB": np.zeros((3, 3), dtype=np.float64),
        "GDP": {"id": {"reward": 109, "contraint": 110}},
        "Nm": 2,
        "RDP": {"T": 64.0},
        "PDP": {"T": 64.0, "Q": {"o": [np.zeros((4, 64))]}},
    }


def test_DEM_AtariIII_demo_wiring_compute_only(monkeypatch) -> None:
    """DEMO1 calls ``run_dem_atariiii(entry_stop=12)`` and skips plot when ``plot=False``."""

    def _fake_driver(entry_stop: int = 5) -> dict:
        assert entry_stop == 12
        return _fake_driver_ctx()

    monkeypatch.setattr(demo_mod, "run_dem_atariiii", _fake_driver)

    def _fail_plot(*_a: object, **_k: object) -> None:
        raise AssertionError("run_entry12plot must not run when plot=False")

    monkeypatch.setattr(demo_mod, "run_entry12plot", _fail_plot)

    ctx = run_dem_atariiii_demo(plot=False)

    assert np.isclose(float(ctx["RDP"]["T"]), 64.0, rtol=0.0, atol=1e-12)
    assert "PDP" in ctx
    assert "entry12plot" not in ctx


def test_DEM_AtariIII_demo_wiring_plot_tail(monkeypatch) -> None:
    """DEMO1 calls ``run_entry12plot`` with PDP + plot context when ``plot=True``."""

    def _fake_driver(entry_stop: int = 5) -> dict:
        assert entry_stop == 12
        return _fake_driver_ctx()

    monkeypatch.setattr(demo_mod, "run_dem_atariiii", _fake_driver)

    captured: dict[str, object] = {}

    def _fake_plot(pdp: object, plot_ctx: dict, **kwargs: object) -> tuple:
        captured["pdp"] = pdp
        captured["plot_ctx"] = plot_ctx
        captured["kwargs"] = kwargs
        h = np.array([1, 2], dtype=np.int64)
        return np.zeros((1, 1), dtype=np.uint8), np.zeros((1, 1), dtype=np.uint8), h, None

    monkeypatch.setattr(demo_mod, "run_entry12plot", _fake_plot)

    ctx = run_dem_atariiii_demo(plot=True, save_png=False)

    assert captured["pdp"] is ctx["PDP"]
    plot_ctx = captured["plot_ctx"]
    assert isinstance(plot_ctx, dict)
    assert "RGB" in plot_ctx and "GDP" in plot_ctx and plot_ctx["Nm"] == 2
    assert "entry12plot" in ctx
    assert np.array_equal(ctx["entry12plot"]["h"], np.array([1, 2], dtype=np.int64))
