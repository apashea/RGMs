"""DEM_AtariIII Entry 3 — ``PDP = spm_MDP_generate(GDP)`` with ``tau=1``, ``T=10000`` ledger."""

from __future__ import annotations

import copy
from typing import Any

from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate

ATARI_TRAINING_T_LEDGER = 10000


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
    """Run ``spm_MDP_generate`` on prepared ``GDP``."""
    return spm_MDP_generate(gdp)
