"""Product A native RNG — MATLAB ``DEM_AtariIII.m`` ``rng(2)`` intent.

Library location for OPTIM1FULL native / COLAB1 (and other Product A drivers).
Does **not** apply to Product B Model B ledger replay.
"""

from __future__ import annotations

import os

# Staged ``DEM_AtariIII.m`` snippet: ``rng(2)`` before Entry 1 constants / pong.
NATIVE_DRIVER_RNG_SEED_DEFAULT = 2
# Back-compat alias used by older DEMO1/OPTIM1 call sites.
DEMO1_NATIVE_RNG_SEED_DEFAULT = NATIVE_DRIVER_RNG_SEED_DEFAULT


def seed_native_driver_rng() -> int | None:
    """
    Reset NumPy global RNG before a Product A full-driver run.

    Default **2** (MATLAB ``rng(2)`` intent). Override with ``RGMS_NATIVE_DRIVER_RNG_SEED``.
    Set ``RGMS_NATIVE_DRIVER_RNG_SEED=none`` to skip (diagnostic only — not Product A sign-off).
    """
    import numpy as np

    raw = str(os.getenv("RGMS_NATIVE_DRIVER_RNG_SEED", "")).strip()
    if raw.lower() in ("none", "skip"):
        return None
    if raw.lower() in ("", "default"):
        seed = NATIVE_DRIVER_RNG_SEED_DEFAULT
    else:
        seed = int(raw)
    np.random.seed(seed)
    return seed


__all__ = [
    "DEMO1_NATIVE_RNG_SEED_DEFAULT",
    "NATIVE_DRIVER_RNG_SEED_DEFAULT",
    "seed_native_driver_rng",
]
