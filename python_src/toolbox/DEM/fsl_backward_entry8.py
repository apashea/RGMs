"""FSL backward — Entry 8 only (training-window merges; not Entry 12).

Ledger: ``training_window_assimilations`` — repeated ``spm_merge_structure_learning`` on
``PDP.O`` windows (no ``spm_RDP_basin``).

Input boundary: ``MDP_pre_entry9`` + ``PDP.O`` (same snapshot as Entry 9 input).
Authority: ``MDP_post_entry8`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

import copy
from typing import Any

from python_src.toolbox.DEM.dem_atariiii_entry8 import training_window_assimilations
from python_src.toolbox.DEM.dem_atariiii_pdp_o import assert_pdp_o_columns_sufficient


def entry8_boundary_from_driver_ctx(
    ctx: dict[str, Any],
    *,
    n_outer: int | None = None,
) -> dict[str, Any]:
    """Build the FSL backward boundary dict from a ``run_dem_atariiii`` context (Entry 8/9 input)."""
    outer = n_outer if n_outer is not None else int(ctx.get("entry8_outer", 128))
    return {
        "mdp": ctx["MDP"],
        "pdp_o": ctx["PDP"]["O"],
        "Ne": ctx["Ne"],
        "C": ctx["C"],
        "NT": ctx.get("entry8_NT", 100),
        "n_outer": outer,
    }


def run_entry8_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **8** ledger from a materialized pre-Entry-9 boundary dict.

    Required keys: ``mdp``, ``pdp_o``, ``Ne``. Optional: ``NT`` (100), ``n_outer`` (128).
    """
    ne = int(boundary["Ne"])
    nt = int(boundary.get("NT", 100))
    n_outer = int(boundary.get("n_outer", 128))
    assert_pdp_o_columns_sufficient(
        boundary["pdp_o"],
        ne=ne,
        nt=nt,
        n_outer=n_outer,
    )
    mdp_out, merge_s = training_window_assimilations(
        boundary["pdp_o"],
        copy.deepcopy(boundary["mdp"]),
        ne,
        nt=nt,
        n_outer=n_outer,
    )
    return {
        "mdp": mdp_out,
        "entry8_merge_loop_s": float(merge_s),
        "NT": nt,
        "n_outer": n_outer,
    }
