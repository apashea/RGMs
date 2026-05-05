"""Entry 12 — ``run_dem_atariiii(entry_stop=12)`` wires full ``spm_MDP_VB_XXX(RDP)``."""

from __future__ import annotations

import os

import numpy as np

import python_src.toolbox.DEM.DEM_AtariIII as dem_atari_mod
from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii


def test_DEM_AtariIII_entry12_driver_wires_vb_full_mode(monkeypatch) -> None:
    """
    Ledger Entry 12: driver assigns ``ctx['PDP'] = spm_MDP_VB_XXX(RDP)`` (no staged partial flag).

    The real nested Atari ``RDP`` still triggers staged VB edge cases; we validate **wiring** by
    substituting a trivial PDP so the driver lane stays fast and deterministic.
    """
    captured: dict[str, object] = {}

    def _fake_vb(rdp: dict, options: object | None = None) -> dict:
        captured["rdp"] = rdp
        captured["options"] = options
        opts = options if isinstance(options, dict) else {}
        assert "_rgms_partial_ok" not in opts
        return {"T": float(rdp["T"])}

    monkeypatch.setattr(dem_atari_mod, "spm_MDP_VB_XXX", _fake_vb)

    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=12)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    assert ctx.get("_entry12_use_partial_vb") is False
    assert "RDP" in ctx and isinstance(ctx["RDP"], dict)
    assert captured["rdp"] is ctx["RDP"]
    assert np.isclose(float(ctx["RDP"]["T"]), 64.0, rtol=0.0, atol=1e-12)
    pdp = ctx["PDP"]
    assert isinstance(pdp, dict)
    assert float(pdp.get("T", 0.0)) == 64.0
