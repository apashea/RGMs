"""DEM_AtariIII Entry 2 — ``spm_MDP_pong`` + snippet ``S`` matrix."""

from __future__ import annotations

from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong


def build_s_matrix(nr: int, nc: int) -> np.ndarray:
    """MATLAB snippet ``S = ones(4,3); S(1,:) = [Nr, Nc, 1];`` (rows 2–4 stay ones)."""
    s = np.ones((4, 3), dtype=np.float64)
    s[0, :] = [float(nr), float(nc), 1.0]
    return s


def run_entry2_pong(
    nr: int,
    nc: int,
    nd: int,
    *,
    na: bool = True,
    np_dist: int = 0,
) -> dict[str, Any]:
    """``[GDP, hid, cid, con, RGB] = spm_MDP_pong(Nr, Nc, Nd, true, 0);`` on the ledger."""
    gdp, hid, cid, con, rgb, _nP = spm_MDP_pong(nr, nc, nd, 1 if na else 0, np_dist)
    return {
        "gdp": gdp,
        "hid": hid,
        "cid": cid,
        "con": con,
        "rgb": rgb,
        "S": build_s_matrix(nr, nc),
    }


def run_entry2_from_constants(
    *,
    nr: int = 12,
    nc: int = 9,
    nd: int = 4,
    na: bool = True,
    np_dist: int = 0,
) -> dict[str, Any]:
    """Entry **2** ledger from Atari snippet constants (Entry **1**)."""
    return run_entry2_pong(nr, nc, nd, na=na, np_dist=np_dist)
