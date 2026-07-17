"""DEM_AtariIII Entry 7 — hit/miss ``spm_merge_structure_learning`` assimilations."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning


def assimilate_hit_miss_sequences(
    pdp_o_cells: list[list[Any]],
    mdp: list[dict[str, Any]],
    entry6_windows: list[dict[str, Any]],
    ne: int,
) -> list[dict[str, Any]]:
    """MATLAB inner loop: ``MDP = spm_merge_structure_learning(PDP.O(:,t+s),MDP)``."""
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    for rec in entry6_windows:
        t = np.asarray(rec["t"], dtype=np.int64).ravel(order="F")
        for s in range(1, int(ne) + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
    return mdp_out
