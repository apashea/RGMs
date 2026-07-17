"""``DEM_AtariIII.m`` L221–229 — Generative AI (first post-VB ``spm_show_RGB``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

from python_src.toolbox.DEM.dem_atariiii_plot_rgb_fence import dem_atariiii_plot_rgb_with_hits

_FIGURE_TITLE = "Generative AI"
_NT = 4
_MOVIE = 1
_HITS_Y = 0.0


def dem_atariiii_plot_generative_ai(
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
) -> Tuple[Any, Any, Any, Optional[Path]]:
    """``spm_show_RGB(PDP,RGB)`` + hits at **y=0** (``zeros(size(h))`` in script)."""
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
