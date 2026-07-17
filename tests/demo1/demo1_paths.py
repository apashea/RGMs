"""DEMO1 fixture and repo path resolution (shipped parity + legacy dev fallback)."""

from __future__ import annotations

import os
from pathlib import Path


def demo1_repo_root() -> Path:
    """RGMs repo root (parent of ``tests/``)."""
    return Path(__file__).resolve().parents[2]


def demo1_fixtures_dir() -> Path:
    """
    Single artifact root for DEMO1 parity.

    Resolution order:
    1. ``RGMS_DEMO1_FIXTURES_DIR`` (orchestrator / explicit override)
    2. ``RGMS_ENTRY12_CAPTURE_OUT_DIR`` (Entry 12 parity alias)
    3. Shipped greenfield default ``tests/demo1/fixtures`` (fresh clone; empty until parity run)
    """
    for key in ("RGMS_DEMO1_FIXTURES_DIR", "RGMS_ENTRY12_CAPTURE_OUT_DIR"):
        raw = str(os.getenv(key, "")).strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return demo1_shipped_fixtures_dir()


def demo1_shipped_fixtures_dir() -> Path:
    """Greenfield shipped path (orchestrator sets env to this)."""
    return demo1_repo_root() / "tests" / "demo1" / "fixtures"


def demo1_matlab_src_dem_dir() -> Path:
    return demo1_repo_root() / "matlab_src" / "toolbox" / "DEM"


def demo1_visualizations_dir() -> Path:
    return demo1_repo_root() / "visualizations"


def demo1_shipped_parity_png() -> Path:
    return demo1_visualizations_dir() / "DEMO1_matlab_python_parity_12plot.png"


def demo1_python_native_dir() -> Path:
    """Product A native artifacts — never parity ``tests/demo1/fixtures/``."""
    return demo1_repo_root() / "tests" / "demo1" / "python_native"


def demo1_python_native_driver_ctx_path() -> Path:
    return demo1_python_native_dir() / "DEMO1_python_native_driver_ctx.pkl"


def demo1_python_native_pdp_path() -> Path:
    return demo1_python_native_dir() / "DEMO1_python_native_PDP.pkl"


def demo1_python_native_12plot_png_path(ts: str | None = None) -> Path:
    if ts is None:
        from datetime import datetime

        ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    return demo1_visualizations_dir() / f"DEMO1_python_native_12plot_{ts}.png"
