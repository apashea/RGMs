"""Convert MATLAB ``loadmat`` values (v7, ``simplify_cells``) to nested Python for DEM MDP/RDP.

Used by Entry 12 ``.mat`` oracles. Keeps nested translation quirks localized to tests,
not ``python_src`` runtime paths.

"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

_MATLAB_CLASS_TO_NUMPY: dict[str, np.dtype] = {
    "logical": np.dtype(bool),
    "double": np.dtype(np.float64),
    "single": np.dtype(np.float32),
    "int8": np.dtype(np.int8),
    "int16": np.dtype(np.int16),
    "int32": np.dtype(np.int32),
    "int64": np.dtype(np.int64),
    "uint8": np.dtype(np.uint8),
    "uint16": np.dtype(np.uint16),
    "uint32": np.dtype(np.uint32),
    "uint64": np.dtype(np.uint64),
}


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
            if obj.ndim == 2 and obj.shape[0] >= 1 and obj.shape[1] >= 1:
                if obj.shape[0] == 1 and obj.shape[1] >= 1:
                    flat = [mat_nested_to_py(obj.flat[i], _depth=_depth + 1) for i in range(obj.size)]
                    return flat if len(flat) > 1 else flat[0]
                if obj.shape[1] == 1 and obj.shape[0] >= 1:
                    flat = [mat_nested_to_py(obj.flat[i], _depth=_depth + 1) for i in range(obj.size)]
                    return flat[0] if len(flat) == 1 else flat
                if obj.shape[0] > 1 and obj.shape[1] > 1:
                    return [
                        [
                            mat_nested_to_py(obj[i, j], _depth=_depth + 1)
                            for j in range(obj.shape[1])
                        ]
                        for i in range(obj.shape[0])
                    ]
            flat = [mat_nested_to_py(obj.flat[i], _depth=_depth + 1) for i in range(obj.size)]
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


def entry12_call2_gp_matlab_class_fixture_path() -> Path:
    """MATLAB-exported generative-process class metadata for call-2 ``RDP.MDP``."""
    return _FIXTURES_DIR / "entry12_call2_gp_matlab_class.json"


@lru_cache(maxsize=1)
def _load_entry12_call2_gp_matlab_class_meta() -> dict[str, Any]:
    path = entry12_call2_gp_matlab_class_fixture_path()
    if not path.is_file():
        raise FileNotFoundError(f"missing call-2 GP class fixture: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"expected dict in {path}, got {type(raw).__name__}")
    return raw


def restore_array_matlab_class(arr: Any, matlab_class: str) -> Any:
    """Restore a leaf array to the MATLAB ``class(...)`` recorded at capture time."""
    if not isinstance(arr, np.ndarray):
        return arr
    target = _MATLAB_CLASS_TO_NUMPY.get(str(matlab_class))
    if target is None:
        return np.asarray(arr)
    return np.asarray(arr, dtype=target)


def _restore_cell_block_from_meta(cells: list[Any], entries: list[dict[str, Any]]) -> None:
    if len(entries) != len(cells):
        raise ValueError(f"GP cell block length mismatch: meta={len(entries)} cells={len(cells)}")
    for ent, cell in zip(entries, cells, strict=True):
        g_meta = int(ent["g"])
        g_idx = g_meta - 1
        if g_idx < 0 or g_idx >= len(cells):
            raise IndexError(f"GP meta g={g_meta} out of range for cell block length {len(cells)}")
        cells[g_idx] = restore_array_matlab_class(cell, str(ent["matlab_class"]))


def restore_entry12_call2_gp_dtypes(rdp: dict[str, Any]) -> None:
    """Restore ``RDP.MDP.{GA,GB,GU,GD}`` dtypes lost by ``loadmat`` on call-2 fixtures.

    ``scipy.io.loadmat`` maps MATLAB ``logical`` to ``uint8`` and can also collapse
    small binary ``double`` arrays (e.g. ``eye(Nc,Nc)`` proprioception) to ``uint8``.
    Restoration uses per-modality MATLAB class metadata from
    ``entry12_call2_gp_matlab_class.json`` (exported from the paired ``.mat`` in MATLAB).
    """
    meta = _load_entry12_call2_gp_matlab_class_meta()
    mdp = rdp.get("MDP")
    if not isinstance(mdp, dict):
        raise TypeError("call-2 RDP must contain dict MDP for GP dtype restore")

    ga = mdp.get("GA")
    if isinstance(ga, list):
        _restore_cell_block_from_meta(ga, meta["GA"])

    gb = mdp.get("GB")
    if isinstance(gb, list) and meta.get("GB"):
        _restore_cell_block_from_meta(gb, meta["GB"])

    gu = mdp.get("GU")
    gu_meta = meta.get("GU")
    if isinstance(gu, np.ndarray) and isinstance(gu_meta, dict):
        mdp["GU"] = restore_array_matlab_class(gu, str(gu_meta["matlab_class"]))

    gd = mdp.get("GD")
    if isinstance(gd, list) and meta.get("GD"):
        _restore_cell_block_from_meta(gd, meta["GD"])


def mat_nested_rdp_from_loadmat(raw: dict[str, Any], *, tag: str | None = None) -> Any:
    """Convert ``loadmat(...)['RDP']`` and apply tag-specific dtype restoration."""
    if "RDP" not in raw:
        raise KeyError("expected variable RDP in loadmat payload")
    rdp = mat_nested_to_py(raw["RDP"])
    if tag in (
        "rgms_atari_call2",
        "rgms_atari_call3",
        "rgms_atari_call4",
        "rgms_atari_optim1full_nr_g01",
        "rgms_optim1full_nr_g01",
    ) and isinstance(rdp, dict):
        restore_entry12_call2_gp_dtypes(rdp)
    return rdp


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


def load_entry12_rdp_mat_nested_for_tag(tag: str, mat_path: str | Path) -> dict[str, Any]:
    """Load paired Entry 12 ``RDP`` ``.mat`` with tag-aware dtype restoration."""
    from scipy.io import loadmat

    p = Path(mat_path)
    kw: dict[str, Any] = {}
    try:
        kw["simplify_cells"] = True
        raw = loadmat(str(p), **kw)
    except TypeError:
        raw = loadmat(str(p))
    nested = mat_nested_rdp_from_loadmat(raw, tag=tag)
    if not isinstance(nested, dict):
        raise TypeError(f"RDP must convert to dict, got {type(nested).__name__}")
    return nested
