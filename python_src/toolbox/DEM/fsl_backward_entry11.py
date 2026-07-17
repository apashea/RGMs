"""FSL backward — Entry 11 assembly only (not Entry 12, not full ``run_dem_atariiii``)."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals


def entry11_rdp_for_entry12_vb(
    rdp_assembly: dict[str, Any],
    *,
    tag: str = "rgms_canonical",
) -> dict[str, Any]:
    """VB input: shared ``rdp_for_vb_from_python_assembly`` (MATLAB ``.mat`` template)."""
    from python_src.toolbox.DEM.entry12_matlab_capture import rdp_for_vb_from_python_assembly

    return rdp_for_vb_from_python_assembly(rdp_assembly, tag=tag)


def run_entry11_assembly_from_mdp(
    mdp: list[dict[str, Any]],
    *,
    c_val: float = 32.0,
) -> dict[str, Any]:
    """
    Ledger Entry 11 only: ``spm_set_goals`` → ``spm_set_costs`` → ``spm_mdp2rdp`` → ``T=64``.

    Input ``mdp`` is the MATLAB authority state **after Entry 10** (post-sort, post-goals, before costs).
    Output ``RDP`` is compared to ``DEMAtariIII_XXX_12_rdp.mat`` (Entry 12 Call 1 input spec).
    """
    mdp_e11 = copy.deepcopy(mdp)
    goals = np.array([2, 3], dtype=np.int64)
    costs = np.array([c_val, -c_val], dtype=np.float64)
    mdp_e11 = spm_set_goals(mdp_e11, goals, costs)
    mdp_e11 = spm_set_costs(
        mdp_e11,
        np.array([2.0, 3.0], dtype=np.float64),
        costs,
    )
    rdp = spm_mdp2rdp(mdp_e11)
    rdp["T"] = 64.0
    return rdp


def run_entry11_rdp_for_entry12_vb_from_mdp(
    mdp: list[dict[str, Any]],
    *,
    c_val: float = 32.0,
    tag: str = "rgms_canonical",
) -> dict[str, Any]:
    """Assembly plus VB-input prep (script **3** lane)."""
    return entry11_rdp_for_entry12_vb(run_entry11_assembly_from_mdp(mdp, c_val=c_val), tag=tag)
