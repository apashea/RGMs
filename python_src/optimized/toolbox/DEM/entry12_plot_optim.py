"""OPTIM1 Product B (parity) ENTRY 12PLOT fence — DEMO1-faithful; parity PNG paths only."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.optimized.toolbox.DEM.spm_show_RGB_optim import spm_show_RGB_optim
from python_src.toolbox.DEM.entry12_plot import (
    compose_entry12plot_matlab_vs_pklpdp_png,
    entry12plot_timestamp,
    load_pdp_pkl_for_plot,
    load_plot_ctx_from_mat,
    pdp_pkl_path,
    plot_ctx_mat_path,
    resolve_matlab_12plot_reference_png,
    spm_get_hits,
)
from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf
from tests.demo1.optim1.optim1_paths import optim1_repo_root, optim1_visualizations_dir


def optim1_12plot_png_path(ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return optim1_visualizations_dir() / f"OPTIM1_12plot_{ts}.png"


def optim1_12plot_python_pkl_pdp_png_path(ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return optim1_visualizations_dir() / f"OPTIM1_12plot_python_pkl_pdp_{ts}.png"


def optim1_12plot_compare_matlab_vs_pklpdp_path(ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return (
        optim1_visualizations_dir()
        / f"OPTIM1_12plot_compare_matlab_vs_pklpdp_{ts}.png"
    )


def run_entry12plot_optim(
    pdp: Any,
    plot_ctx: Dict[str, Any],
    *,
    repo_root: Path | None = None,
    save_png: bool = True,
    png_path: Path | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Path | None]:
    """Run staged ENTRY 12PLOT fence; does not invoke VB (DEMO1-faithful; OPTIM1 paths)."""
    _ = repo_root or optim1_repo_root()
    rgb = plot_ctx["RGB"]
    gdp_id = plot_ctx["GDP"]["id"]

    spm_figure("GetWin", "Generative AI")
    spm_figure_clf("Generative AI")
    j, k = spm_show_RGB_optim(pdp, rgb)
    q_o = pdp["Q"]["o"]
    o1 = q_o[0] if isinstance(q_o, list) else q_o
    h = spm_get_hits(o1, gdp_id)

    fig = plt.gcf()
    ax_elbo = getattr(fig, "_rgms_elbo_ax", None)
    if ax_elbo is None:
        raise RuntimeError(
            "spm_show_RGB_optim did not set fig._rgms_elbo_ax for hits overlay"
        )
    ax_elbo.plot(h, np.zeros_like(h, dtype=np.float64), ".r", markersize=16)
    plt.draw()

    out_png: Path | None = None
    if save_png:
        out_png = png_path or optim1_12plot_png_path()
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(out_png, dpi=100, bbox_inches="tight", pad_inches=0.15)

    return j, k, h, out_png


def run_entry12plot_optim_phase_b_visual_review(
    repo_root: Path | None = None,
    *,
    ts: str | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Path, Optional[Path]]:
    """Phase **B** plot PNG + MATLAB-vs-**``.pkl``** side-by-side compare (no VB re-run)."""
    root = repo_root or optim1_repo_root()
    ts = ts or entry12plot_timestamp()
    ctx = load_plot_ctx_from_mat(plot_ctx_mat_path(root))
    pdp = load_pdp_pkl_for_plot(pdp_pkl_path(root))
    pkl_png = optim1_12plot_python_pkl_pdp_png_path(ts)
    j, k, h, saved = run_entry12plot_optim(
        pdp, ctx, repo_root=root, save_png=True, png_path=pkl_png
    )
    assert saved is not None
    matlab_ref = resolve_matlab_12plot_reference_png(root)
    compare: Optional[Path] = None
    if matlab_ref is not None:
        compare = compose_entry12plot_matlab_vs_pklpdp_png(
            matlab_ref,
            saved,
            optim1_12plot_compare_matlab_vs_pklpdp_path(ts),
        )
    return j, k, h, saved, compare
