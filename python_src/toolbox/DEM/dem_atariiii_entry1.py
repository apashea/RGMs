"""DEM_AtariIII Entry 1 — snippet constants (``Nr``, ``Nc``, ``Sc``, ``Nd``, ``C``)."""

from __future__ import annotations

from typing import Any

# MATLAB ``DEM_AtariIII`` snippet (``rng(2)`` ledger scale; constants before pong).
ATARI_NR = 12
ATARI_NC = 9
ATARI_SC = 9
ATARI_ND = 4
ATARI_C = 32


def entry1_constants_dict() -> dict[str, int | float]:
    """Ledger constants written into ``run_dem_atariiii`` context at Entry **1**."""
    return {
        "Nr": ATARI_NR,
        "Nc": ATARI_NC,
        "Sc": ATARI_SC,
        "Nd": ATARI_ND,
        "C": ATARI_C,
    }


def apply_entry1_constants(ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply Entry **1** constants; returns context dict (mutates ``ctx`` when provided)."""
    out = ctx if ctx is not None else {}
    out.update(entry1_constants_dict())
    return out
