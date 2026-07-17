"""Shared Orbits figure panels for ``dem_orbits_before`` / ``dem_orbits_after``.

Mirrors ``DEM_AtariIII.m`` L354–373 / L406–425: ``spm_dir_orbits(PDP.B{1}, HID, 64)``
plus paths-to-hits at threshold ``1/32``. Spectral policy B injects optional.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.toolbox.DEM.dem_atariiii_paths import dem_atariiii_paths_to_hits_P
from python_src.toolbox.DEM.spm_dir_orbits import spm_dir_orbits
from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf

_FIGURE_TITLE = "Orbits"
_ORBITS_N = 64
_PATHS_NT = 32
_PATHS_B_THRESHOLD = 1.0 / 32.0


def _pdp_b1(pdp: Mapping[str, Any]) -> np.ndarray:
    b_field = pdp["B"]
    b1 = b_field[0] if isinstance(b_field, list) else b_field
    arr = np.asarray(b1, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(f"PDP.B{{1}} expected 3-D array, got shape {arr.shape!r}")
    return arr


def _pdp_hid(pdp: Mapping[str, Any]) -> np.ndarray:
    id_rec = pdp["id"]
    if not isinstance(id_rec, dict) or "hid" not in id_rec:
        raise KeyError("PDP.id.hid required for Orbits figure")
    return np.asarray(id_rec["hid"], dtype=np.int64).ravel(order="F")


def dem_atariiii_plot_orbits_figure(
    pdp: Mapping[str, Any],
    plot_ctx: Optional[dict[str, Any]] = None,
    *,
    orbits_subplot: int,
    paths_subplot: int,
    paths_title: str,
    save_png: bool = False,
    png_path: Optional[Path] = None,
    eig: Optional[Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]] = None,
    svd: Optional[Callable[..., np.ndarray]] = None,
    ness_order: Optional[Callable[[np.ndarray, int], np.ndarray]] = None,
    eng: Any = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[Path]]:
    """
    Orbits + paths-to-hits panels on a fence ``PDP``.

    Returns ``(u, I, HID, png_path)``. ``plot_ctx`` unused (API parity).
    """
    del plot_ctx
    b1 = _pdp_b1(pdp)
    hid = _pdp_hid(pdp)

    spm_figure("GetWin", _FIGURE_TITLE)
    spm_figure_clf(_FIGURE_TITLE)
    plt.gcf().set_size_inches(12.0, 12.0)

    ax_orb = plt.subplot(2, 2, int(orbits_subplot), projection="3d")
    plt.sca(ax_orb)
    u = spm_dir_orbits(
        b1,
        hid,
        _ORBITS_N,
        eig=eig,
        svd=svd,
        ness_order=ness_order,
        eng=eng,
        plot=True,
    )
    ax_orb.tick_params(labelsize=9)
    ax_orb.set_title("Orbits", fontsize=11, pad=8)

    B_mask = (np.sum(b1, axis=2) > _PATHS_B_THRESHOLD).astype(np.float64)
    I = dem_atariiii_paths_to_hits_P(B_mask, hid, _PATHS_NT)
    HID = hid.copy()

    ax = plt.subplot(2, 2, int(paths_subplot))
    ax.imshow(I, aspect="auto", origin="upper", interpolation="nearest", cmap="gray")
    if HID.size:
        ax.plot(
            HID.astype(np.float64) - 1.0,
            np.zeros(HID.shape) + 0.5,
            "o",
            markersize=8,
            markerfacecolor="none",
            markeredgecolor="r",
            markeredgewidth=1.0,
        )
    ax.set_title(str(paths_title), fontsize=11, pad=8)
    ax.set_xlabel("latent states")
    ax.set_ylabel("time steps")
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

    return u, I, HID, out_png
