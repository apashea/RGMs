"""``DEM_AtariIII.m`` L188–206 — Attractors post-sort orbits + paths-to-hits.

Sign-off numerics (``Atari_plotting.md`` Plot porting contract):
``spm_dir_orbits`` latent ``u`` + paths ``I``/``HID`` (threshold ``> 0``).
Spectral policy B: Engine ``eig``/``spm_svd`` injects; paths pure Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from python_src.toolbox.DEM.dem_atariiii_paths import dem_atariiii_paths_to_hits_P
from python_src.toolbox.DEM.spm_dir_orbits import spm_dir_orbits
from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf

_FIGURE_TITLE = "Attractors"
_ORBITS_N = 64
_PATHS_NT = 32


def _as_b1(b1: Any) -> np.ndarray:
    return np.asarray(b1, dtype=np.float64)


def _as_hid(hid: Any) -> np.ndarray:
    return np.asarray(hid, dtype=np.int64).ravel(order="F")


def _payload_from_mapping(payload: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    if "b1" not in payload:
        raise KeyError("post_sort payload missing 'b1'")
    if "hid" not in payload:
        raise KeyError("post_sort payload missing 'hid'")
    return _as_b1(payload["b1"]), _as_hid(payload["hid"])


def dem_atariiii_plot_attractors_mdp_post_sort(
    payload: Mapping[str, Any],
    plot_ctx: Optional[dict[str, Any]] = None,
    *,
    save_png: bool = False,
    png_path: Optional[Path] = None,
    eig: Optional[Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]] = None,
    svd: Optional[Callable[..., np.ndarray]] = None,
    ness_order: Optional[Callable[[np.ndarray, int], np.ndarray]] = None,
    eng: Any = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[Path]]:
    """
    Post-sort Attractors panels: orbits (``u``) + paths-to-hits (``I``, ``HID``).

    Returns ``(u, I, HID, png_path)``. ``plot_ctx`` unused (API parity).
    """
    del plot_ctx
    b1, hid = _payload_from_mapping(payload)

    spm_figure("GetWin", _FIGURE_TITLE)
    spm_figure_clf(_FIGURE_TITLE)
    plt.gcf().set_size_inches(12.0, 12.0)

    ax3 = plt.subplot(2, 2, 3, projection="3d")
    plt.sca(ax3)
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
    ax3.tick_params(labelsize=9)
    ax3.set_title("Orbits", fontsize=11, pad=8)

    # paths to hits — DEM_AtariIII.m L194–205 (threshold > 0)
    B_mask = (np.sum(b1, axis=2) > 0).astype(np.float64)
    I = dem_atariiii_paths_to_hits_P(B_mask, hid, _PATHS_NT)
    HID = hid.copy()

    ax = plt.subplot(2, 2, 4)
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
    ax.set_title("Paths to hits", fontsize=11, pad=8)
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
