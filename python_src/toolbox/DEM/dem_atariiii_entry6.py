"""DEM_AtariIII Entry 6 — rewarded/costly events and assimilation windows."""

from __future__ import annotations

from typing import Any

import numpy as np


def find_events_and_windows(
    pdp_o: np.ndarray, gdp_id: dict[str, Any], ne: int
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """MATLAB: ``spm_get_hits`` / ``spm_get_miss`` and ``t = (s+Ne):(r+Ne)`` windows."""
    ridx = int(np.asarray(gdp_id["reward"], dtype=np.int64).reshape(-1)[0]) - 1
    cidx = int(np.asarray(gdp_id["contraint"], dtype=np.int64).reshape(-1)[0]) - 1
    r = np.flatnonzero(np.asarray(pdp_o[ridx, :], dtype=np.float64) > 1.0) + 1
    c = np.flatnonzero(np.asarray(pdp_o[cidx, :], dtype=np.float64) > 1.0) + 1
    windows: list[dict[str, Any]] = []
    for i in range(r.size):
        ri = int(r[i])
        s = int(c[np.flatnonzero(c < ri)[-1]])
        t = np.arange(s + int(ne), ri + int(ne) + 1, dtype=np.int64)
        if t.size > 0:
            windows.append({"reward": ri, "start": s, "t": t})
    return r, c, windows
