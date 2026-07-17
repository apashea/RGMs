"""OPTIM1FULL Product B — canonical sign-off environment (§ ``OPTIM1.md`` **11.0.1**)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

# ``DEM_AtariIII.m`` lines 250–252 — not tunable on Product B sign-off.
OPTIM1FULL_CANONICAL_NR = 32
OPTIM1FULL_CANONICAL_NT = 256
OPTIM1FULL_CANONICAL_NS = 256


def assert_optim1full_signoff_env() -> None:
    """Fail fast if canonical Atari parameters are not active."""
    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
        atari_nr_replications,
        atari_ns_concentration,
        atari_nt_game_length,
    )

    if atari_nr_replications() != OPTIM1FULL_CANONICAL_NR:
        raise RuntimeError(
            f"RGMS_ATARI_NR effective={atari_nr_replications()} — Product B sign-off "
            f"requires NR={OPTIM1FULL_CANONICAL_NR}; use optim1full_signoff_env()"
        )
    if atari_nt_game_length() != OPTIM1FULL_CANONICAL_NT:
        raise RuntimeError(
            f"RGMS_ATARI_NT effective={atari_nt_game_length()} — "
            f"requires NT={OPTIM1FULL_CANONICAL_NT}"
        )
    if float(atari_ns_concentration()) != float(OPTIM1FULL_CANONICAL_NS):
        raise RuntimeError(
            f"RGMS_ATARI_NS effective={atari_ns_concentration()} — "
            f"requires NS={OPTIM1FULL_CANONICAL_NS}"
        )


@contextmanager
def optim1full_signoff_env(*, deadline_minutes: str = "120") -> Iterator[None]:
    """
    Pin ``DEM_AtariIII.m`` canonical parameters for OPTIM1FULL Product B gates.

    Overrides stray values such as ``RGMS_ATARI_NR=1`` in the shell/conda env.
    """
    from tests.oracle.toolbox.DEM.fsl_backward_rand import fsl_entry11_driver_env

    old: dict[str, str | None] = {}
    pinned = {
        "RGMS_ATARI_NR": str(OPTIM1FULL_CANONICAL_NR),
        "RGMS_ATARI_NT": str(OPTIM1FULL_CANONICAL_NT),
        "RGMS_ATARI_NS": str(OPTIM1FULL_CANONICAL_NS),
        "RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG": "1",
        "RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI": "1",
        "RGMS_OPTIM1FULL_ENTRY4_LINK_DIR_MI": "1",
        "RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG": "1",
        "RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB": "1",
        "RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_EIG": "1",
        "RGMS_OPTIM1FULL_DIR_ORBITS_MATLAB_SVD": "1",
    }
    for key, value in pinned.items():
        old[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        with fsl_entry11_driver_env(deadline_minutes=deadline_minutes):
            assert_optim1full_signoff_env()
            yield
    finally:
        for key, prior in old.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior
