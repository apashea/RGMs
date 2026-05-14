"""Convert MATLAB ``loadmat`` values (v7, ``simplify_cells``) to nested Python for DEM MDP/RDP.

Used by Entry 12 ``.mat`` oracles. Keeps nested translation quirks localized to tests,
not ``python_src`` runtime paths.

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def mat_nested_to_py(obj: Any, *, _depth: int = 0) -> Any:
    """Best-effort recursive unwrap for scipy ``loadmat`` outputs.

    Handles structured arrays, ``dtype=object`` MATLAB cells, and common scalar wrappers.
    """
    if _depth > 80:
        raise RecursionError("mat_nested_to_py exceeded depth")

    if isinstance(obj, np.ndarray):
        if obj.dtype.names:
            return {str(n): mat_nested_to_py(obj[n][()], _depth=_depth + 1) for n in obj.dtype.names}

        if obj.dtype == object:
            flat = [mat_nested_to_py(obj.flat[i], _depth=_depth + 1) for i in range(obj.size)]
            if obj.ndim == 2 and obj.shape[0] == 1 and obj.shape[1] >= 1:
                # MATLAB 1×N horizontal struct/cell row → Python list of models
                return flat if len(flat) > 1 else flat[0]
            if obj.ndim == 2 and obj.shape[1] == 1 and obj.shape[0] >= 1:
                return flat[0] if len(flat) == 1 else flat
            if len(flat) == 1:
                return flat[0]
            return flat

        if np.issubdtype(obj.dtype, np.number) or obj.dtype == bool:
            out = np.asarray(obj)
            return out

        return np.asarray(obj)

    if isinstance(obj, np.void):
        names = getattr(obj.dtype, "names", None)
        if names:
            return {str(n): mat_nested_to_py(obj[n], _depth=_depth + 1) for n in names}

    if isinstance(obj, dict):
        return {k: mat_nested_to_py(v, _depth=_depth + 1) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        conv = [mat_nested_to_py(x, _depth=_depth + 1) for x in obj]
        return type(obj)(conv)

    return obj


def load_saved_rdp_as_py(mat_path: str | Path) -> Any:
    """Load ``RDP`` from ``saved_rdp_DEM_AtariIII.mat`` and convert for ``spm_MDP_checkX``."""
    from scipy.io import loadmat

    p = Path(mat_path)
    kw: dict[str, Any] = {}
    try:
        kw["simplify_cells"] = True
        raw = loadmat(str(p), **kw)
    except TypeError:
        raw = loadmat(str(p))
    if "RDP" not in raw:
        raise KeyError(f"expected variable RDP in {p}")
    return mat_nested_to_py(raw["RDP"])
