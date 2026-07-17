"""FSL backward — Entry 7 only (hit/miss assimilations; not Entry 12).

Ledger: Entry **6** windows → ``assimilate_hit_miss_sequences`` (``spm_merge_structure_learning``).

Input: ``MDP_pre_entry7`` + ``PDP_O`` + ``PDP.o`` + ``GDP.id`` (``rng(2)`` dump).
Authority: ``MDP_pre_entry9`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_entry6 import find_events_and_windows
from python_src.toolbox.DEM.dem_atariiii_entry7 import assimilate_hit_miss_sequences
from python_src.toolbox.DEM.dem_atariiii_pdp_o import assert_pdp_o_columns_sufficient


def entry7_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build the FSL backward boundary dict from a ``run_dem_atariiii`` context."""
    return {
        "mdp": ctx["MDP"],
        "pdp_o": ctx["PDP"]["O"],
        "pdp_o_obs": ctx["PDP"]["o"],
        "gdp_id": ctx["GDP"]["id"],
        "Ne": ctx["Ne"],
    }


def run_entry7_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **7** ledger from a materialized pre-Entry-7 boundary dict.

    Required keys: ``mdp``, ``pdp_o``, ``pdp_o_obs``, ``gdp_id``, ``Ne``.
    """
    ne = int(boundary["Ne"])
    _r, _c, windows = find_events_and_windows(
        np.asarray(boundary["pdp_o_obs"], dtype=np.float64),
        boundary["gdp_id"],
        ne,
    )
    assert_pdp_o_columns_sufficient(
        boundary["pdp_o"],
        ne=ne,
        entry6_windows=windows,
    )
    mdp_out = assimilate_hit_miss_sequences(
        boundary["pdp_o"],
        copy.deepcopy(boundary["mdp"]),
        windows,
        ne,
    )
    return {
        "mdp": mdp_out,
        "entry6_windows": windows,
        "n_windows": len(windows),
    }
