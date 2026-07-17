"""W2 Phase **5-C-arena** — unified VB run arena (child lite path + forwards driver host).

``VbRunArena`` attaches to the top-level ``bundle``; nested hierarchical ``run_child_vb``
calls use ``ChildVbArena`` views without full-tree ``deepcopy`` or public re-entry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM.vb_optim_deepcopy import vb_optim_deepcopy

_ARENA_KEY = "_vb_run_arena_optim"


def _qrec_fill_inplace(dst: Any, src: Any) -> Any:
    """
    Copy ``src`` into ``dst`` reusing ndarray buffers and container shells.

    Falls back to ``vb_optim_deepcopy`` when list lengths or types diverge.
    """
    if isinstance(src, np.ndarray):
        if isinstance(dst, np.ndarray) and dst.shape == src.shape and dst.dtype == src.dtype:
            np.copyto(dst, src)
            return dst
        return np.asarray(src, dtype=src.dtype, copy=True, order="K")

    if src is None or isinstance(src, (bool, int, float, str, bytes)):
        return src

    if isinstance(src, np.generic):
        return src.item() if src.ndim == 0 else np.array(src, copy=True)

    if isinstance(src, dict):
        if not isinstance(dst, dict):
            return vb_optim_deepcopy(src)
        for key in list(dst.keys()):
            if key not in src:
                del dst[key]
        for key, val in src.items():
            if key in dst:
                filled = _qrec_fill_inplace(dst[key], val)
                if filled is not dst[key]:
                    dst[key] = filled
            else:
                dst[key] = vb_optim_deepcopy(val)
        return dst

    if isinstance(src, list):
        if not isinstance(dst, list) or len(dst) != len(src):
            return vb_optim_deepcopy(src)
        for idx, s_item in enumerate(src):
            filled = _qrec_fill_inplace(dst[idx], s_item)
            if filled is not dst[idx]:
                dst[idx] = filled
        return dst

    if isinstance(src, tuple):
        return vb_optim_deepcopy(src)

    return vb_optim_deepcopy(src)


@dataclass
class _QrecPoolSlot:
    """Ping-pong ``qrec`` shells for one hierarchical ``parent_mi``."""

    shells: list[Any] = field(default_factory=lambda: [None, None])

    def checkout(self, parent_q: Any) -> Any:
        if not isinstance(parent_q, dict):
            return vb_optim_deepcopy(parent_q)

        shell_a, shell_b = self.shells
        if shell_a is None:
            shell_a = vb_optim_deepcopy(parent_q)
            shell_b = vb_optim_deepcopy(parent_q)
            self.shells = [shell_a, shell_b]
            return shell_a

        if id(parent_q) == id(shell_a):
            dst, src = shell_b, shell_a
        elif id(parent_q) == id(shell_b):
            dst, src = shell_a, shell_b
        else:
            dst, src = shell_a, parent_q

        filled = _qrec_fill_inplace(dst, src)
        if filled is not dst:
            if id(parent_q) == id(shell_a):
                self.shells[1] = filled
            elif id(parent_q) == id(shell_b):
                self.shells[0] = filled
            else:
                self.shells[0] = filled
            return filled
        return dst


@dataclass
class ChildVbArena:
    """Per nested child invocation — parent context only (no cloned ``Q``)."""

    parent_mi: int
    t_idx: int
    parent_bundle: dict[str, Any]


@dataclass
class VbRunArena:
    """Top-level optim VB arena — lives for one ``run_optim_vb`` call."""

    parent_bundle: dict[str, Any] | None = None
    child_checkx_done: dict[int, bool] = field(default_factory=dict)
    qrec_pools: dict[int, _QrecPoolSlot] = field(default_factory=dict)


def arena_child_q_from_parent(arena: VbRunArena, parent_mi: int, parent_q: Any) -> Any:
    """
    Child ``Q`` record for one hierarchical step — pooled semantic copy.

    Matches fidelity ``copy.deepcopy(parent['Q'])`` (~4239) without stdlib
    ``deepcopy`` on every step. Ping-pong shells reuse container/ndarray storage.
    """
    slot = arena.qrec_pools.setdefault(int(parent_mi), _QrecPoolSlot())
    return slot.checkout(parent_q)


def arena_attach(bundle: dict[str, Any], arena: VbRunArena) -> None:
    bundle[_ARENA_KEY] = arena
    arena.parent_bundle = bundle


def arena_get(bundle: dict[str, Any] | None) -> VbRunArena | None:
    if not isinstance(bundle, dict):
        return None
    arena = bundle.get(_ARENA_KEY)
    return arena if isinstance(arena, VbRunArena) else None


def child_arena(parent_bundle: dict[str, Any], parent_mi: int, t_idx: int) -> ChildVbArena:
    return ChildVbArena(
        parent_mi=int(parent_mi),
        t_idx=int(t_idx),
        parent_bundle=parent_bundle,
    )
