"""``DEM_AtariIII.m`` L342–350 — Active inference (before compression)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

from python_src.toolbox.DEM.dem_atariiii_plot_rgb_fence import dem_atariiii_plot_rgb_with_hits

_FIGURE_TITLE = "Active inference (before compression)"
_NT = 8
_MOVIE = 0
_HITS_Y = -2.0


def dem_atariiii_plot_before_compression_rgb(
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[Path]]:
    """Post-VB hierarchical RGB + hits — ``spm_show_RGB(PDP,RGB,8,false)``."""
    return dem_atariiii_plot_rgb_with_hits(
        pdp,
        plot_ctx,
        figure_title=_FIGURE_TITLE,
        nt=_NT,
        movie=_MOVIE,
        hits_y_offset=_HITS_Y,
        save_png=save_png,
        png_path=png_path,
    )
