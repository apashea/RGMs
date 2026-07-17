"""ENDGAME-2 — nested child inference kernel (reuse ``ws`` + cold bundle across 128× calls).

Tranche 1: cached ``ws`` per ``parent_mi``.
Tranche 2: cached child cold bundle shell; per-call refresh of ``D``/``E``/``a``/``b`` + native init + 12C.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM.vb_cold_optim import (
    vb_cold_refresh_child_12bc,
    vb_cold_setup_child_12bc_native,
)
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


@dataclass
class ChildBundleSlot:
    sig: tuple[Any, ...]
    bundle: dict[str, Any]


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


def child_bundle_acquire(
    slots: dict[int, ChildBundleSlot],
    parent_mi: int,
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """
    Return child cold bundle — full 12B–12C once per ``parent_mi`` signature, then refresh path.
    """
    sig = child_kernel_signature(models, nm, t_h)
    key = int(parent_mi)
    slot = slots.get(key)
    if slot is not None and slot.sig == sig:
        return vb_cold_refresh_child_12bc(models, slot.bundle, opts, hp)
    bundle = vb_cold_setup_child_12bc_native(models, nm, t_h, opts, hp)
    slots[key] = ChildBundleSlot(sig=sig, bundle=copy.deepcopy(bundle))
    return bundle
