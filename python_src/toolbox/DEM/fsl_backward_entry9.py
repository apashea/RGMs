"""FSL backward — Entry 9 only (basin loop; not Entry 12, not full ``run_dem_atariiii``).

Ledger: Entry **8+9** outer loop — ``spm_merge_structure_learning`` then ``spm_RDP_basin`` until
``all(d)`` or ``n_outer`` exhausted.

Input boundary is MATLAB-fed ``MDP_pre_entry9`` + ``PDP.O`` from
``dump_MDP_pre_entry10.m``. Output ``mdp`` is compared to ``MDP_pre_entry10`` authority.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

import copy
from typing import Any

from python_src.toolbox.DEM.dem_atariiii_entry9 import basin_training_loop
from python_src.toolbox.DEM.dem_atariiii_pdp_o import assert_pdp_o_columns_sufficient
from python_src.toolbox.DEM.fsl_backward_entry8 import entry8_boundary_from_driver_ctx

entry9_boundary_from_driver_ctx = entry8_boundary_from_driver_ctx


def run_entry9_from_boundary(
    boundary: dict[str, Any],
) -> dict[str, Any]:
    """
    Run Entry **9** ledger from a materialized pre-Entry-9 boundary dict.

    Required keys: ``mdp``, ``pdp_o``, ``Ne``, ``C``. Optional: ``NT`` (default 100),
    ``n_outer`` (default 128).
    """
    mdp = copy.deepcopy(boundary["mdp"])
    pdp_o = boundary["pdp_o"]
    ne = int(boundary["Ne"])
    c_val = float(boundary["C"])
    nt = int(boundary.get("NT", 100))
    n_outer = int(boundary.get("n_outer", 128))
    assert_pdp_o_columns_sufficient(
        pdp_o,
        ne=ne,
        nt=nt,
        n_outer=n_outer,
    )
    out = basin_training_loop(
        pdp_o,
        mdp,
        ne,
        c_val,
        nt=nt,
        n_outer=n_outer,
    )
    return {
        "mdp": out["MDP"],
        "NS": out["NS"],
        "NU": out["NU"],
        "NA": out["NA"],
        "NO": out["NO"],
        "NH": out["NH"],
        "entry8_loop_s": float(out["entry8_loop_s"]),
        "entry9_loop_s": float(out["entry9_loop_s"]),
        "NT": nt,
        "n_outer": n_outer,
    }
