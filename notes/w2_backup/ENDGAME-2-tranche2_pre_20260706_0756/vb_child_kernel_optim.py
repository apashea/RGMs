"""ENDGAME-2 — nested child inference kernel (reuse ``ws`` across 128× calls).

Avoids per-call ``ws_from_bundle`` realloc when child structure is stable for one
``parent_mi``. Cold 12B–12C and hot t-loop remain; teardown via
``vb_cold_teardown_child_kernel_native``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM.vb_workspace_optim import (
    VbWorkspace,
    ws_from_bundle,
    ws_refill_from_bundle,
)


def child_kernel_signature(models: list[dict[str, Any]], nm: int, t_h: float) -> tuple[Any, ...]:
    """Structural key — child ``A``/``B`` layout stable across hierarchical steps at one ``m``."""
    m0 = models[0]
    a_lens = tuple(int(np.asarray(x).size) for x in m0.get("A", []))
    b_lens = tuple(int(np.asarray(x).size) for x in m0.get("B", []))
    return (int(nm), int(t_h), len(m0.get("A", [])), len(m0.get("B", [])), a_lens, b_lens)


@dataclass
class ChildWsSlot:
    sig: tuple[Any, ...]
    ws: VbWorkspace


def child_ws_acquire(
    slots: dict[int, ChildWsSlot],
    parent_mi: int,
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    bundle: dict[str, Any],
) -> VbWorkspace:
    """Return cached ``ws`` for ``parent_mi`` when signature matches; else alloc and store."""
    sig = child_kernel_signature(models, nm, t_h)
    slot = slots.get(int(parent_mi))
    if slot is not None and slot.sig == sig:
        ws_refill_from_bundle(slot.ws, bundle)
        return slot.ws
    ws = ws_from_bundle(bundle)
    slots[int(parent_mi)] = ChildWsSlot(sig=sig, ws=ws)
    return ws
