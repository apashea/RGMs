"""OPTIM1 Entry 3 — ``PDP = spm_MDP_generate_optim(GDP)`` with ``tau=1``, ``T=10000``."""

from __future__ import annotations

import copy
from typing import Any

from python_src.optimized.toolbox.DEM.spm_MDP_generate_optim import spm_MDP_generate_optim
from python_src.toolbox.DEM.dem_atariiii_entry3 import ATARI_TRAINING_T_LEDGER

__all__ = [
    "ATARI_TRAINING_T_LEDGER",
    "prepare_gdp_for_generate",
    "generate_mdp_rollout",
]


def prepare_gdp_for_generate(
    gdp: dict[str, Any],
    *,
    tau: float = 1.0,
    training_t: int = ATARI_TRAINING_T_LEDGER,
) -> dict[str, Any]:
    """MATLAB: ``GDP.tau = 1; GDP.T = 10000;`` before ``spm_MDP_generate``."""
    gdp_out = copy.deepcopy(gdp)
    gdp_out["tau"] = float(tau)
    gdp_out["T"] = float(training_t)
    return gdp_out


def generate_mdp_rollout(gdp: dict[str, Any]) -> dict[str, Any]:
    """Run ``spm_MDP_generate_optim`` on prepared ``GDP``."""
    return spm_MDP_generate_optim(gdp)
