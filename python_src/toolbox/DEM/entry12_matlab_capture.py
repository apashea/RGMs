"""Load Entry 12 MATLAB subentry checkpoint ``.mat`` files (``DEMAtariIII_entry12_<tag>_12X.mat``).

Built by ``matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m`` (writes **12A**–**12I** in one run).
Uses ``scipy.io.loadmat`` **MAT-format v7** (not v7.3 HDF5) — MATLAB ``save(..., '-v7')``.

Does **not** import any ``tests/oracle`` Entry 1–11 modules.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_MATLAB_META_KEYS = frozenset({"__header__", "__version__", "__globals__"})

# Pinned capture tag for documentation / CI (override via ``RGMS_ENTRY12_CANONICAL_RUN_TAG``).
# Generate mats in MATLAB with:
#   ``setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', ENTRY12_CANONICAL_RUN_TAG);``
#   ``DEMAtariIII_entry12_dump_all_subentries();``
ENTRY12_CANONICAL_RUN_TAG = (
    os.getenv("RGMS_ENTRY12_CANONICAL_RUN_TAG", "rgms_canonical").strip() or "rgms_canonical"
)


def rgms_repo_root() -> Path:
    """``RGMs`` repo root (parent of ``python_src``)."""
    return Path(__file__).resolve().parents[3]


def default_entry12_mat_output_dir() -> Path:
    """Default directory written by ``DEMAtariIII_entry12_dump_all_subentries.m`` (``matlab_custom/entry12/out``)."""
    return rgms_repo_root() / "matlab_custom" / "entry12" / "out"


def saved_rdp_dem_atariiii_mat_path() -> Path:
    """Default ``saved_rdp_DEM_AtariIII.mat`` beside ``dump_rdp_DEM_AtariIII.m`` (same layout as MATLAB capture)."""
    return rgms_repo_root() / "matlab_custom" / "saved_rdp_DEM_AtariIII.mat"


def entry12_subentry_mat_path_canonical(
    code: str,
    *,
    out_dir: Path | str | None = None,
) -> Path:
    """Path to ``DEMAtariIII_entry12_<canonical>_12X.mat`` using :data:`ENTRY12_CANONICAL_RUN_TAG`."""
    return entry12_subentry_mat_path(ENTRY12_CANONICAL_RUN_TAG, code, out_dir=out_dir)


def entry12_capture_artifacts_exist(
    *,
    run_tag: str | None = None,
    out_dir: Path | str | None = None,
    require_subentries: tuple[str, ...] = ("12A", "12H"),
) -> bool:
    """Return True if expected ``.mat`` files exist for ``run_tag`` (default: canonical)."""
    tag = run_tag if run_tag is not None else ENTRY12_CANONICAL_RUN_TAG
    base = Path(out_dir) if out_dir is not None else default_entry12_mat_output_dir()
    return all((base / entry12_subentry_mat_filename(tag, c)).is_file() for c in require_subentries)


def entry12_subentry_mat_filename(run_tag: str, code: str) -> str:
    """Basename ``DEMAtariIII_entry12_<runTag>_12X.mat`` with ``code`` like ``12A`` … ``12I``."""
    tag = _sanitize_run_tag(run_tag)
    c = code.strip().upper()
    if not re.match(r"^12[A-I]$", c):
        raise ValueError(f"code must match 12A-12I, got {code!r}")
    return f"DEMAtariIII_entry12_{tag}_{c}.mat"


def entry12_subentry_mat_path(
    run_tag: str,
    code: str,
    *,
    out_dir: Path | str | None = None,
) -> Path:
    """Absolute path to a subentry ``.mat`` for ``run_tag`` and ``code`` (``12A`` … ``12I``)."""
    base = Path(out_dir) if out_dir is not None else default_entry12_mat_output_dir()
    return base / entry12_subentry_mat_filename(run_tag, code)


def _sanitize_run_tag(run_tag: str) -> str:
    raw = str(run_tag).strip()
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw)
    return safe or "default"


def load_entry12_subentry_mat(path: Path | str) -> dict[str, Any]:
    """Load a MATLAB ``.mat`` file and return user variables (no ``__header__`` / ``__version__``).

    Nested MATLAB structs arrive as ``numpy`` structured arrays / objects depending on
    ``scipy`` version; callers performing oracle compares should normalize further as needed.
    """
    from scipy.io import loadmat

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))

    kw: dict[str, Any] = {}
    try:
        kw["simplify_cells"] = True
        mat = loadmat(str(p), **kw)
    except TypeError:
        mat = loadmat(str(p))

    return {k: v for k, v in mat.items() if k not in _MATLAB_META_KEYS}


def load_entry12_subentry_mat_from_env(code: str) -> dict[str, Any]:
    """Load using ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` and optional ``RGMS_ENTRY12_CAPTURE_OUT_DIR``."""
    tag = os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "default").strip() or "default"
    out = os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    od: Path | None = Path(out) if out else None
    return load_entry12_subentry_mat(entry12_subentry_mat_path(tag, code, out_dir=od))


__all__ = [
    "ENTRY12_CANONICAL_RUN_TAG",
    "default_entry12_mat_output_dir",
    "entry12_capture_artifacts_exist",
    "entry12_subentry_mat_filename",
    "entry12_subentry_mat_path",
    "entry12_subentry_mat_path_canonical",
    "load_entry12_subentry_mat",
    "load_entry12_subentry_mat_from_env",
    "rgms_repo_root",
    "saved_rdp_dem_atariiii_mat_path",
]
