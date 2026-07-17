"""OPTIM1 path resolution — isolated outputs; DEMO1 fixtures are read-only authority."""

from __future__ import annotations

import os
from pathlib import Path

from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root


def optim1_repo_root() -> Path:
    """RGMs repo root (same as DEMO1)."""
    return demo1_repo_root()


def optim1_demo1_authority_fixtures_dir() -> Path:
    """
    Read-only DEMO1 parity authority (``tests/demo1/fixtures`` by default).

    OPTIM1 validation compares against mats/pkls produced by DEMO1 Product B.
    """
    return demo1_fixtures_dir()


def optim1_shipped_fixtures_dir() -> Path:
    """OPTIM1-owned parity checkpoints (resume / isolated runner outputs)."""
    return optim1_repo_root() / "tests" / "demo1" / "optim1" / "fixtures"


def optim1_fixtures_dir() -> Path:
    """
    OPTIM1 checkpoint root.

    Resolution order:
    1. ``RGMS_OPTIM1_FIXTURES_DIR``
    2. Shipped default ``tests/demo1/optim1/fixtures``
    """
    raw = str(os.getenv("RGMS_OPTIM1_FIXTURES_DIR", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim1_shipped_fixtures_dir()


def optim1_visualizations_dir() -> Path:
    return optim1_repo_root() / "visualizations" / "optim1"


def optim1_python_native_dir() -> Path:
    """Product A native artifacts — never DEMO1 ``python_native/`` or parity fixtures."""
    return optim1_repo_root() / "tests" / "demo1" / "optim1" / "python_native"


def optim1_python_native_driver_ctx_path() -> Path:
    return optim1_python_native_dir() / "OPTIM1_python_native_driver_ctx.pkl"


def optim1_python_native_pdp_path() -> Path:
    return optim1_python_native_dir() / "OPTIM1_python_native_PDP.pkl"


def optim1_shipped_parity_png() -> Path:
    return optim1_visualizations_dir() / "OPTIM1_matlab_python_parity_12plot.png"


def optim1_python_native_12plot_png_path(ts: str | None = None) -> Path:
    if ts is None:
        from datetime import datetime

        ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    return optim1_visualizations_dir() / f"OPTIM1_python_native_12plot_{ts}.png"
