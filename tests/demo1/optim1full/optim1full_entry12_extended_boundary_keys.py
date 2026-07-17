"""OPTIM1FULL call4 — canonical Entry **12** lean boundary keys."""

from __future__ import annotations

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CALL4_LEAN_BOUNDARY_KEYS,
    ENTRY12_LEAN_BOUNDARY_KEYS,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
)

# Shared framework (call2/call3/canonical).
ENTRY12_BASE_BOUNDARY_KEYS: tuple[str, ...] = ENTRY12_LEAN_BOUNDARY_KEYS

# Call4 canonical set (includes ``out_t10``, ``out_t20``, ``out_t30``).
OPTIM1FULL_CALL4_BOUNDARY_KEYS: tuple[str, ...] = ENTRY12_CALL4_LEAN_BOUNDARY_KEYS

# Back-compat aliases (mistake-era names).
OPTIM1FULL_CALL4_EXTRA_BOUNDARY_KEYS: tuple[str, ...] = ("out_t10", "out_t20", "out_t30")
OPTIM1FULL_CALL4_EXTENDED_BOUNDARY_KEYS: tuple[str, ...] = OPTIM1FULL_CALL4_BOUNDARY_KEYS
OPTIM1FULL_CALL4_EXTRA_BOUNDARY_T: tuple[int, ...] = (10, 20, 30)
OPTIM1FULL_CALL4_EXTENDED_TAG = ENTRY12_OPTIM1FULL_CALL4_TAG
