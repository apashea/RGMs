"""``DEM_AtariIII.m`` L88–97 — Gameplay (final ``t=128`` only).

Sign-off numerics (``Atari_plotting.md`` Plot porting contract):
``spm_O2rgb(PDP.O(:,t), RGB)`` frame + control ``PDP.O{con,t}'``.
Not an ``spm_show_RGB`` / ``J``/``K``/``h`` site.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf
from python_src.toolbox.DEM.spm_O2rgb import spm_O2rgb

_FIGURE_TITLE = "Gameplay"
_FINAL_T_1BASED = 128


def _o_column_at_t(o_cells: Any, t_1based: int) -> list[Any]:
    """MATLAB ``PDP.O(:,t)`` — one outcome column at 1-based time ``t``."""
    t0 = int(t_1based) - 1
    if not isinstance(o_cells, list) or not o_cells:
        raise TypeError("PDP.O must be a non-empty No×T list-of-lists")
    col: list[Any] = []
    for row in o_cells:
        if not isinstance(row, (list, tuple)):
            raise TypeError("PDP.O rows must be time-indexed lists")
        if t0 < 0 or t0 >= len(row):
            raise IndexError(f"PDP.O time t={t_1based} out of range (len={len(row)})")
        col.append(row[t0])
    return col


def _control_index_1based(pdp: Any) -> int:
    id_field = pdp["id"] if isinstance(pdp, dict) else getattr(pdp, "id")
    if isinstance(id_field, dict):
        con = id_field["control"]
    else:
        con = getattr(id_field, "control")
    return int(np.asarray(con, dtype=np.int64).ravel()[0])


def dem_atariiii_plot_gameplay(
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    t: int = _FINAL_T_1BASED,
    save_png: bool = False,
    png_path: Optional[Path] = None,
) -> Tuple[np.ndarray, np.ndarray, Optional[Path]]:
    """
    Final Gameplay frame only (default ``t=128``).

    Returns ``(frame_rgb, control, png_path)`` where:
    - ``frame_rgb`` — ``uint8`` HxWx3 from ``spm_O2rgb(PDP.O(:,t), RGB)``
    - ``control`` — ``PDP.O{con,t}'`` (row vector, float64)
    - ``png_path`` — optional saved figure path

    Stub ``spm_figure`` GetWin+clf only; no VideoWriter; no frames ``1…127``.
    """
    rgb = plot_ctx["RGB"]
    o_cells = pdp["O"]
    t_use = int(t)
    o_col = _o_column_at_t(o_cells, t_use)
    frame_rgb = spm_O2rgb(o_col, rgb)

    con = _control_index_1based(pdp)
    control = np.asarray(o_cells[con - 1][t_use - 1], dtype=np.float64).reshape(-1)
    # MATLAB ``PDP.O{con,t}'`` — transpose of the control outcome column.
    control = control.reshape(1, -1) if control.ndim == 1 else control.T

    spm_figure("GetWin", _FIGURE_TITLE)
    spm_figure_clf(_FIGURE_TITLE)
    ax1 = plt.subplot(2, 1, 1)
    ax1.imshow(np.asarray(frame_rgb, dtype=np.uint8))
    ax1.set_axis_off()
    ax2 = plt.subplot(4, 3, 8)
    ax2.imshow(np.asarray(control, dtype=np.float64))
    ax2.set_axis_off()
    plt.draw()

    out_png: Optional[Path] = None
    if save_png:
        if png_path is None:
            raise ValueError("save_png=True requires png_path")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(png_path, dpi=100, bbox_inches="tight", pad_inches=0.15)
        out_png = png_path

    return frame_rgb, control, out_png
