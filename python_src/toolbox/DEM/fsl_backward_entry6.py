"""FSL backward — Entry 6 only (events and assimilation windows; no ``MDP`` mutation).

Ledger: ``find_events_and_windows`` on ``PDP.o`` + ``GDP.id``.

Authority (``rng(2)`` ledger): ``entry6_r``, ``entry6_c``, ``entry6_t_windows`` in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_entry6 import find_events_and_windows


def entry6_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build boundary dict from ``run_dem_atariiii`` context (post–Entry 5, pre–Entry 7)."""
    return {
        "pdp_o_obs": ctx["PDP"]["o"],
        "gdp_id": ctx["GDP"]["id"],
        "Ne": ctx["Ne"],
    }


def run_entry6_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **6** ledger from materialized boundary.

    Required keys: ``pdp_o_obs``, ``gdp_id``, ``Ne``.
    """
    ne = int(boundary["Ne"])
    r, c, windows = find_events_and_windows(
        np.asarray(boundary["pdp_o_obs"], dtype=np.float64),
        boundary["gdp_id"],
        ne,
    )
    return {
        "r": r,
        "c": c,
        "entry6_windows": windows,
        "n_windows": len(windows),
    }
