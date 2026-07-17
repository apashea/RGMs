"""``DEM_AtariIII.m`` L275–282 — Active inference (NR game ``i=NR``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

from python_src.toolbox.DEM.dem_atariiii_plot_rgb_fence import dem_atariiii_plot_rgb_with_hits

_FIGURE_TITLE = "Active inference"
_NT = 4
_MOVIE = 0
_HITS_Y = -2.0


def dem_atariiii_plot_active_inference_nr(
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
) -> Tuple[Any, Any, Any, Optional[Path]]:
    """Inside NR loop — ``spm_show_RGB(PDP,RGB,4,0)`` + hits at **y=-2**."""
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
