"""OPTIM1FULL copy of OPTIM1 §2 scalar ``rand`` patch targets (lane-isolated)."""

from __future__ import annotations

from tests.oracle.toolbox.DEM.fsl_backward_rand import _RAND_PATCH_TARGETS


def optim1full_rand_patch_targets() -> tuple[str, ...]:
    """Same targets as OPTIM1 Product B ``_optim_rand_patch_targets``."""
    return _RAND_PATCH_TARGETS + (
        "python_src.optimized.toolbox.DEM.spm_MDP_generate_optim.np.random.rand",
    )
