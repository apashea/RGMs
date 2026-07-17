"""W2 Phase 5-S-1 — explicit VB RNG context (optim-owned replay)."""
from __future__ import annotations

from typing import Any

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM.vb_rng_replay_optim import (
    VbMatlabRandReplay,
    vb_load_matlab_rand_buf,
)


class VbRandContext:
    """Top-level ``vb_rand_buf`` replay — no fidelity ``spm_MDP_VB_XXX`` import."""

    __slots__ = ("_reuse", "_replay")

    def __init__(self, *, reuse_matlab_draws: bool) -> None:
        self._reuse = bool(reuse_matlab_draws)
        self._replay: Any = None

    def __enter__(self) -> VbRandContext:
        if self._reuse and _inst._VB_TIMING_DEPTH == 1:
            self._replay = VbMatlabRandReplay(vb_load_matlab_rand_buf())
            self._replay.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._replay is not None and _inst._VB_TIMING_DEPTH == 1:
            self._replay.__exit__(exc_type, exc, tb)
            self._replay = None
