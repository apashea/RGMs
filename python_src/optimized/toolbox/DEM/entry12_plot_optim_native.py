"""OPTIM1 Product A (native) ENTRY 12PLOT — verbatim copy of DEMO1 ``run_entry12plot``; native PNG path only."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.optimized.toolbox.DEM.spm_show_RGB_optim_native import (
    spm_show_RGB_optim_native,
)
from python_src.toolbox.DEM.entry12_plot import entry12plot_timestamp, spm_get_hits
from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf
from tests.demo1.optim1.optim1_paths import optim1_python_native_12plot_png_path


def run_entry12plot_optim_native(
    pdp: Any,
    plot_ctx: Dict[str, Any],
    *,
    repo_root: Path | None = None,
    save_png: bool = True,
    png_path: Path | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Path | None]:
    """Run staged ENTRY 12PLOT fence; does not invoke VB (DEMO1-native copy)."""
    _ = repo_root
    rgb = plot_ctx["RGB"]
    gdp_id = plot_ctx["GDP"]["id"]

    spm_figure("GetWin", "Generative AI")
    spm_figure_clf("Generative AI")
    j, k = spm_show_RGB_optim_native(pdp, rgb)
    q_o = pdp["Q"]["o"]
    o1 = q_o[0] if isinstance(q_o, list) else q_o
    h = spm_get_hits(o1, gdp_id)

    fig = plt.gcf()
    ax_elbo = getattr(fig, "_rgms_elbo_ax", None)
    if ax_elbo is None:
        raise RuntimeError(
            "spm_show_RGB_optim_native did not set fig._rgms_elbo_ax for hits overlay"
        )
    ax_elbo.plot(h, np.zeros_like(h, dtype=np.float64), ".r", markersize=16)
    plt.draw()

    out_png: Path | None = None
    if save_png:
        out_png = png_path or optim1_python_native_12plot_png_path(entry12plot_timestamp())
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(out_png, dpi=100, bbox_inches="tight", pad_inches=0.15)

    return j, k, h, out_png
