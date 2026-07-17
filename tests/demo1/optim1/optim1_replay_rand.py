"""OPTIM1 RNG replay — extends FSL backward patch targets for ``*_optim`` modules."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import numpy as np

from tests.oracle.toolbox.DEM.fsl_backward_rand import _RAND_PATCH_TARGETS


def _optim_rand_patch_targets() -> tuple[str, ...]:
    return _RAND_PATCH_TARGETS + (
        "python_src.optimized.toolbox.DEM.spm_MDP_generate_optim.np.random.rand",
    )


@contextmanager
def optim1_entry3_driver_env(*, deadline_minutes: str = "60") -> Iterator[None]:
    """Entry **3** scale env: ``training_t=10000`` + wall limit."""
    old: dict[str, str | None] = {}
    keys = (
        "RGMS_ATARI_TRAINING_T",
        "RGMS_ATARI_RUN_DEADLINE_MINUTES",
        "RGMS_ATARI_RUN_DEADLINE_MONO",
    )
    for k in keys:
        old[k] = os.environ.get(k)
    os.environ["RGMS_ATARI_TRAINING_T"] = "10000"
    os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = deadline_minutes
    os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MONO", None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextmanager
def optim1_replay_matlab_draws(k_use: int, buf: np.ndarray) -> Iterator[list[int]]:
    """Replay ``buf[:k_use]`` through scalar ``np.random.rand`` (FSL + optim targets)."""
    from unittest.mock import patch

    seq = np.asarray(buf, dtype=np.float64).ravel()
    if k_use > seq.size:
        raise ValueError(f"replay needs K={k_use} draws but buffer has {seq.size}")
    ctr = [0]

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("OPTIM1 replay: only scalar np.random.rand() supported")
        if ctr[0] >= k_use:
            raise RuntimeError(
                f"OPTIM1 replay: exhausted {k_use} draws at index {ctr[0]}"
            )
        v = float(seq[ctr[0]])
        ctr[0] += 1
        return v

    patches = [patch(t, side_effect=shim) for t in _optim_rand_patch_targets()]
    try:
        for p in patches:
            p.start()
        yield ctr
    finally:
        for p in reversed(patches):
            p.stop()
