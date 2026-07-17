"""``DEM_AtariIII.m`` L354–373 — Orbits before compression (``dem_orbits_before``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Tuple

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_plot_orbits_figure import dem_atariiii_plot_orbits_figure


def dem_atariiii_plot_orbits_before(
    pdp: Mapping[str, Any],
    plot_ctx: Optional[dict[str, Any]] = None,
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
    eig: Optional[Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]] = None,
    svd: Optional[Callable[..., np.ndarray]] = None,
    ness_order: Optional[Callable[[np.ndarray, int], np.ndarray]] = None,
    eng: Any = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[Path]]:
    """Before-compression Orbits: subplot ``(2,2,1)`` + paths ``(2,2,3)``."""
    return dem_atariiii_plot_orbits_figure(
        pdp,
        plot_ctx,
        orbits_subplot=1,
        paths_subplot=3,
        paths_title="Paths to hits (before)",
        save_png=save_png,
        png_path=png_path,
        eig=eig,
        svd=svd,
        ness_order=ness_order,
        eng=eng,
    )
