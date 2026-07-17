"""FSL backward — Entry 5 only (parameter forgetting; no ``PDP`` mutation).

Ledger: ``forget_parameters`` on ``MDP`` cell array.

Input: ``MDP_pre_entry5`` (post–Entry 4 structure learning, pre-forget).
Authority: ``MDP_pre_entry7`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``
(same cell state as post–Entry 5 on the ``rng(2)`` ledger; name = pre–Entry 7 hit/miss).

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

import copy
from typing import Any

from python_src.toolbox.DEM.dem_atariiii_entry5 import forget_parameters


def entry5_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build boundary dict from ``run_dem_atariiii`` context (post–Entry 4, pre–Entry 6)."""
    return {"mdp": ctx["MDP"]}


def run_entry5_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **5** ledger from materialized boundary.

    Required keys: ``mdp`` (list of level dicts).
    """
    nm, ne, mdp_out = forget_parameters(copy.deepcopy(boundary["mdp"]))
    return {
        "mdp": mdp_out,
        "Nm": nm,
        "Ne": ne,
    }
