"""Shared pytest fixtures for DEM oracle tests under ``tests/oracle/toolbox/DEM/``."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def dem_eng_entry12(eng):
    """MATLAB Engine configured for DEM ``toolbox/DEM`` work (Entry 12 oracles and captures).

    Mirrors the workspace path/``cd`` behavior needed to run translated DEM scripts via the Engine.
    Defined here so Entry 12 tests do not need to import other entry-scoped test modules.
    """
    repo = Path(__file__).resolve().parents[4]
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

    dem_path = configure_dem_matlab_engine(eng, repo)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


__all__ = ["dem_eng_entry12"]
