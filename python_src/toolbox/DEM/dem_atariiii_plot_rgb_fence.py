"""Shared ``spm_show_RGB`` + hits fence for OPTIM1FULL RGB plot sites.

Internal helper only — each site exposes one public ``dem_atariiii_plot_*`` function.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.toolbox.DEM.entry12_plot import spm_get_hits
from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf
from python_src.toolbox.DEM.spm_show_RGB import spm_show_RGB


def dem_atariiii_plot_rgb_with_hits(
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    figure_title: str,
    nt: int,
    movie: int,
    hits_y_offset: float,
    save_png: bool = False,
    png_path: Optional[Path] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[Path]]:
    """
    ``DEM_AtariIII.m`` illustrate block: ``spm_show_RGB`` + hits overlay.

    Returns ``(J, K, h, png_path)``. Does not invoke VB.
    """
    rgb = plot_ctx["RGB"]
    gdp_id = plot_ctx["GDP"]["id"]

    spm_figure("GetWin", figure_title)
    spm_figure_clf(figure_title)

    j, k = spm_show_RGB(pdp, rgb, Nt=int(nt), MOVIE=int(movie))

    q_o = pdp["Q"]["o"]
    o1 = q_o[0] if isinstance(q_o, list) else q_o
    h = spm_get_hits(o1, gdp_id)

    fig = plt.gcf()
    ax_elbo = getattr(fig, "_rgms_elbo_ax", None)
    if ax_elbo is None:
        raise RuntimeError("spm_show_RGB did not set fig._rgms_elbo_ax for hits overlay")
    y_hit = np.full_like(h, float(hits_y_offset), dtype=np.float64)
    ax_elbo.plot(h, y_hit, ".r", markersize=16)
    plt.draw()

    out_png: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("save_png=True requires png_path")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(png_path, dpi=100, bbox_inches="tight", pad_inches=0.15)
        out_png = png_path

    return j, k, h, out_png
