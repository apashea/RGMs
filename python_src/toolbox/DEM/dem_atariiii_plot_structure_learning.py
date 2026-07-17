"""``DEM_AtariIII.m`` L309–323 — Structure learning ``F`` traces (final ``i=NR``).

Sign-off numerics (``Atari_plotting.md`` Plot porting contract): full ``F`` (6×NR)
after ``i=NR`` (32). Mid-NR ``drawnow`` frames out of sign-off. Panels show rows
1–4; row 4 is redrawn vs frames ``(1:NR)*NT``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf

_FIGURE_TITLE = "Structure learning"
_DEFAULT_NT = 256  # DEM_AtariIII.m NT for NR games
_PANEL_TITLES = (
    "Latent states",
    "Latent paths",
    "ELBO",
    "Reward count",
)


def _as_F(F: Any) -> np.ndarray:
    arr = np.asarray(F, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != 6:
        raise ValueError(f"structure F expected shape (6, NR), got {arr.shape!r}")
    return arr


def dem_atariiii_plot_structure_learning(
    series: Mapping[str, Any] | np.ndarray,
    plot_ctx: Optional[dict[str, Any]] = None,
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
    nt: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[Path]]:
    """
    Final Structure learning panels for fence ``F``.

    Returns ``(F, png_path)``. ``plot_ctx`` unused (API parity).
    """
    del plot_ctx
    if isinstance(series, Mapping):
        if "F" not in series:
            raise KeyError("structure series missing 'F'")
        F = _as_F(series["F"])
    else:
        F = _as_F(series)

    nr = int(F.shape[1])
    nt_i = int(nt if nt is not None else _DEFAULT_NT)

    spm_figure("GetWin", _FIGURE_TITLE)
    spm_figure_clf(_FIGURE_TITLE)
    plt.gcf().set_size_inches(12.0, 12.0)

    for f_idx, title in enumerate(_PANEL_TITLES):
        ax = plt.subplot(3, 2, f_idx + 1)
        ax.plot(F[f_idx, :])
        ax.set_title(title, fontsize=11, pad=8)
        ax.set_xlabel("game")
        ax.set_box_aspect(1)
        ax.tick_params(labelsize=9)

    # DEM_AtariIII.m L319–322 — overwrite reward panel vs frames
    ax = plt.subplot(3, 2, 4)
    t = (np.arange(1, nr + 1, dtype=np.float64)) * float(nt_i)
    ax.plot(t, F[3, :])
    ax.set_title(_PANEL_TITLES[3], fontsize=11, pad=8)
    ax.set_xlabel("frames")
    ax.set_box_aspect(1)
    ax.tick_params(labelsize=9)
    plt.tight_layout()
    plt.draw()

    out_png: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("save_png=True requires png_path")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(png_path, dpi=100, bbox_inches="tight", pad_inches=0.15)
        out_png = png_path

    return F, out_png
