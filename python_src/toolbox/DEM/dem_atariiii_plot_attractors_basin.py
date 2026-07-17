"""``DEM_AtariIII.m`` L166–171 — Attractors basin (final series only).

Sign-off numerics (``Atari_plotting.md`` Plot porting contract):
accumulated ``NS``…``NH`` after the basin loop’s last ``i`` (break or 128).
Not an ``spm_show_RGB`` / ``J``/``K``/``h`` site; mid-loop ``drawnow`` frames out of sign-off.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf

_FIGURE_TITLE = "Attractors"
_SERIES_KEYS = ("NS", "NU", "NA", "NO", "NH")


def _as_series(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=np.float64).reshape(-1)


def _series_from_mapping(series: Mapping[str, Any]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for key in _SERIES_KEYS:
        if key not in series:
            raise KeyError(f"basin series missing {key!r}")
        out[key] = _as_series(series[key])
    return out


def _apply_basin_ax_aesthetics(ax: Any, title: str) -> None:
    """Title/tick layout only — does not touch series numerics."""
    ax.set_title(title, fontsize=11, pad=8)
    ax.tick_params(labelsize=9)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))


def dem_atariiii_plot_attractors_basin(
    series: Mapping[str, Any],
    plot_ctx: Optional[dict[str, Any]] = None,
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Optional[Path]]:
    """
    Final Attractors basin series only (no mid-loop frames).

    Returns ``(NS, NU, NA, NO, NH, png_path)`` matching MATLAB subplot glue at
    ``DEM_AtariIII.m`` ~166–171. ``plot_ctx`` is unused (API parity with other
    ``dem_atariiii_plot_*`` sites).

    Stub ``spm_figure`` GetWin+clf only; no intermediate ``drawnow`` frames.
    """
    del plot_ctx  # fence series are self-contained; no RGB / GDP needed
    s = _series_from_mapping(series)
    ns, nu, na, no, nh = s["NS"], s["NU"], s["NA"], s["NO"], s["NH"]

    spm_figure("GetWin", _FIGURE_TITLE)
    spm_figure_clf(_FIGURE_TITLE)
    # Larger canvas (same aspect) so square panels + denser ticks stay readable.
    plt.gcf().set_size_inches(12.0, 12.0)
    ax = plt.subplot(4, 2, 1)
    ax.plot(ns)
    _apply_basin_ax_aesthetics(ax, "Deep states")
    ax.set_box_aspect(1)
    ax = plt.subplot(4, 2, 2)
    ax.plot(nu)
    _apply_basin_ax_aesthetics(ax, "Deep paths")
    ax.set_box_aspect(1)
    ax = plt.subplot(4, 2, 3)
    ax.plot(na)
    ax.plot(nh)
    _apply_basin_ax_aesthetics(ax, "Childless states")
    ax.set_box_aspect(1)
    ax = plt.subplot(4, 2, 4)
    ax.plot(no)
    _apply_basin_ax_aesthetics(ax, "Orphan states")
    ax.set_box_aspect(1)
    plt.tight_layout()
    plt.draw()

    out_png: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("save_png=True requires png_path")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(png_path, dpi=100, bbox_inches="tight", pad_inches=0.15)
        out_png = png_path

    return ns, nu, na, no, nh, out_png
