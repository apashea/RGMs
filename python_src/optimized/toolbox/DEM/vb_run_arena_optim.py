"""W2 Phase **5-C-arena** / **6-D-DELETION** — unified VB run arena.

``VbRunArena`` attaches to the top-level ``bundle`` for nested child bookkeeping.
**Q-record pool deleted (6-D-DELETION):** hierarchical child uses shared ``parent['Q']``
alias per ``spm_MDP_VB_XXX.m`` ~1163–1165 — not ``arena_child_q_from_parent``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_ARENA_KEY = "_vb_run_arena_optim"


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
    # C4n: fingerprint of child ``a``/``b``/``A``/``B`` at last checked hit (per parent_mi).
    child_ab_fp: dict[int, tuple[Any, ...]] = field(default_factory=dict)
    child_ws_slots: dict[int, Any] = field(default_factory=dict)
    child_bundle_slots: dict[int, Any] = field(default_factory=dict)


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
