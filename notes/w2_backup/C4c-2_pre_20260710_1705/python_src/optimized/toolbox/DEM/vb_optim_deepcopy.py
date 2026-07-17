"""W2 — fast structural clone for MDP dict trees inside band **12F** hierarchical paths.

``copy.deepcopy`` on nested NumPy-heavy MDP structs dominates VB wall time (profile
on tier **3a** call2). This copier preserves fidelity semantics for common MDP leaves
and falls back to stdlib ``deepcopy`` for exotic objects.
"""
from __future__ import annotations

import copy
from typing import Any

import numpy as np

try:
    from scipy import sparse
except ImportError:  # pragma: no cover
    sparse = None  # type: ignore[assignment]


def vb_optim_deepcopy(obj: Any, memo: dict[int, Any] | None = None) -> Any:
    """MDP-tree deep copy without stdlib deepcopy overhead on NumPy leaves."""
    if memo is None:
        memo = {}
    oid = id(obj)
    if oid in memo:
        return memo[oid]

    if isinstance(obj, np.ndarray):
        return np.array(obj, dtype=obj.dtype, copy=True, order="K")

    if isinstance(obj, np.generic):
        return obj.item() if obj.ndim == 0 else np.array(obj, copy=True)

    if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
        return obj

    if sparse is not None and sparse.issparse(obj):
        return obj.copy()

    if isinstance(obj, dict):
        out: dict[Any, Any] = {}
        memo[oid] = out
        for key, val in obj.items():
            out[key] = vb_optim_deepcopy(val, memo)
        return out

    if isinstance(obj, list):
        out_list: list[Any] = []
        memo[oid] = out_list
        for item in obj:
            out_list.append(vb_optim_deepcopy(item, memo))
        return out_list

    if isinstance(obj, tuple):
        out_t = tuple(vb_optim_deepcopy(item, memo) for item in obj)
        memo[oid] = out_t
        return out_t

    return copy.deepcopy(obj, memo)
