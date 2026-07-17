"""DEM_AtariIII Entry 5 — clear ``a{g}`` / ``b{f}`` (parameter forgetting)."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

_EMPTY_AB = np.zeros((0, 0), dtype=np.float64)


def forget_parameters(
    mdp: list[dict[str, Any]],
) -> tuple[int, int, list[dict[str, Any]]]:
    """MATLAB: ``Nm``, ``Ne``, nested loops setting ``MDP{n}.a{g}`` and ``.b{f}`` to ``[]``."""
    mdp_out = copy.deepcopy(mdp)
    nm = len(mdp_out)
    ne = max(2 ** (nm - 1), 1)
    for n in range(nm):
        for g in range(len(mdp_out[n]["a"])):
            mdp_out[n]["a"][g] = _EMPTY_AB.copy()
        for f in range(len(mdp_out[n]["b"])):
            mdp_out[n]["b"][f] = _EMPTY_AB.copy()
    return nm, ne, mdp_out
