"""Monkey-patch ``_entry12_assign_t_boundary`` for OPTIM1FULL extended probe times (no ``spm_MDP_VB_XXX.py`` edit)."""

from __future__ import annotations

from typing import Any

from tests.demo1.optim1full.optim1full_entry12_extended_boundary_keys import (
    OPTIM1FULL_CALL4_EXTRA_BOUNDARY_T,
)

_PATCHED = False
_ORIGINAL = None


def apply_optim1full_extended_boundary_patch() -> None:
    """Extend Python dump mirror with ``out_t10`` / ``out_t20`` / ``out_t30``."""
    global _PATCHED, _ORIGINAL
    if _PATCHED:
        return
    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb

    _ORIGINAL = vb._entry12_assign_t_boundary

    def _patched(ws: dict[str, Any], snap: dict[str, Any], t_1based: int, t_int: int) -> None:
        _ORIGINAL(ws, snap, t_1based, t_int)
        for et in OPTIM1FULL_CALL4_EXTRA_BOUNDARY_T:
            if t_1based == et:
                ws[f"out_t{et}"] = snap

    vb._entry12_assign_t_boundary = _patched
    _PATCHED = True


def restore_optim1full_extended_boundary_patch() -> None:
    global _PATCHED, _ORIGINAL
    if not _PATCHED or _ORIGINAL is None:
        return
    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb

    vb._entry12_assign_t_boundary = _ORIGINAL
    _PATCHED = False
    _ORIGINAL = None
