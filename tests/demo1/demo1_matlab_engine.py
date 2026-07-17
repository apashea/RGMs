"""MATLAB Engine paths for DEMO1 — ``matlab_src`` only (no external ``spm-main``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.demo1.demo1_paths import demo1_matlab_src_dem_dir, demo1_repo_root


def configure_dem_matlab_engine(eng: Any, repo_root: Path | None = None) -> Path:
    """
    Add repo + staged SPM paths for DEM toolbox work.

    Returns ``matlab_src/toolbox/DEM`` for optional ``eng.cd``.
    """
    repo = repo_root or demo1_repo_root()
    dem_path = demo1_matlab_src_dem_dir()
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath(str(repo / "matlab_custom"), nargout=0)
    return dem_path
