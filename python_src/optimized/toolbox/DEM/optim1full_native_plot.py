"""
OPTIM1FULL Product A (W3 native) — final-frame plot hooks.

Calls existing library ``dem_atariiii_plot_*`` modules on live native fence objects.
No Model B ledger, no Engine eig/MI/sort injects, no MATLAB plot-oracle asserts.

Env: ``RGMS_OPTIM1FULL_NATIVE_PLOT=1`` (distinct from parity ``RGMS_OPTIM1FULL_PLOT``).
See ``OPTIM1FULL.md`` § **W3 NATIVE + COLAB1 — plan and living status**.
"""

from __future__ import annotations

import copy
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

_NATIVE_PLOT_ENV = "RGMS_OPTIM1FULL_NATIVE_PLOT"


def optim1full_native_plot_requested() -> bool:
    return os.getenv(_NATIVE_PLOT_ENV, "").strip().lower() in ("1", "true", "yes")


def build_native_plot_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Plot palette/context from live native driver ctx (not frozen parity plot_ctx.mat)."""
    for key in ("RGB", "GDP", "Nm"):
        if key not in ctx:
            raise KeyError(f"native ctx missing {key!r} required for plots")
    return {
        "RGB": ctx["RGB"],
        "GDP": ctx["GDP"],
        "Nm": int(ctx["Nm"]),
    }


def native_plot_png_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[4]
    out = root / "visualizations" / "optim1full_native"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def _png_path(out_dir: Path, site_id: str) -> Path:
    return out_dir / f"AtariIII_native_{site_id}_{_ts()}.png"


def _unwrap_b1_from_mdp(mdp: Any) -> np.ndarray:
    if not isinstance(mdp, list) or not mdp:
        raise TypeError("MDP must be a non-empty list for post_sort b1")
    end = mdp[-1]
    b = end["b"]
    x = b[0] if isinstance(b, list) else b
    while isinstance(x, list):
        if not x:
            raise ValueError("empty b cell")
        x = x[0]
    arr = np.asarray(x, dtype=np.float64)
    while arr.ndim > 3 and int(arr.shape[0]) == 1:
        arr = arr[0]
    return arr


def run_native_plots_at_fence(
    site_id: str,
    fence: Any,
    plot_ctx: dict[str, Any],
    *,
    out_dir: Path,
) -> Path:
    """
    Run one §13 library plot on a native fence object; save final-frame PNG.

    ``fence`` is site-specific (PDP, basin series dict, post_sort payload, or F array).
    """
    import matplotlib

    matplotlib.use("Agg")

    png = _png_path(out_dir, site_id)
    print(
        f"[OPTIM1FULL native plot] {site_id} → {png.name}",
        file=sys.stderr,
        flush=True,
    )

    if site_id == "dem_gameplay":
        from python_src.toolbox.DEM.dem_atariiii_plot_gameplay import (
            dem_atariiii_plot_gameplay,
        )

        dem_atariiii_plot_gameplay(fence, plot_ctx, save_png=True, png_path=png)
    elif site_id == "dem_attractors_basin":
        from python_src.toolbox.DEM.dem_atariiii_plot_attractors_basin import (
            dem_atariiii_plot_attractors_basin,
        )

        dem_atariiii_plot_attractors_basin(fence, plot_ctx, save_png=True, png_path=png)
    elif site_id == "dem_attractors_mdp_post_sort":
        from python_src.toolbox.DEM.dem_atariiii_plot_attractors_mdp_post_sort import (
            dem_atariiii_plot_attractors_mdp_post_sort,
        )

        # Native: no Engine eig/svd injects (policy B injects stay None).
        dem_atariiii_plot_attractors_mdp_post_sort(
            fence, plot_ctx, save_png=True, png_path=png
        )
    elif site_id == "dem_generative_ai":
        from python_src.toolbox.DEM.dem_atariiii_plot_generative_ai import (
            dem_atariiii_plot_generative_ai,
        )

        dem_atariiii_plot_generative_ai(fence, plot_ctx, save_png=True, png_path=png)
    elif site_id == "dem_active_inference_nr":
        from python_src.toolbox.DEM.dem_atariiii_plot_active_inference_nr import (
            dem_atariiii_plot_active_inference_nr,
        )

        dem_atariiii_plot_active_inference_nr(
            fence, plot_ctx, save_png=True, png_path=png
        )
    elif site_id == "dem_structure_learning":
        from python_src.toolbox.DEM.dem_atariiii_plot_structure_learning import (
            dem_atariiii_plot_structure_learning,
        )

        dem_atariiii_plot_structure_learning(
            fence, plot_ctx, save_png=True, png_path=png
        )
    elif site_id == "dem_before_compression_rgb":
        from python_src.toolbox.DEM.dem_atariiii_plot_before_compression_rgb import (
            dem_atariiii_plot_before_compression_rgb,
        )

        dem_atariiii_plot_before_compression_rgb(
            fence, plot_ctx, save_png=True, png_path=png
        )
    elif site_id == "dem_orbits_before":
        from python_src.toolbox.DEM.dem_atariiii_plot_orbits_before import (
            dem_atariiii_plot_orbits_before,
        )

        dem_atariiii_plot_orbits_before(fence, plot_ctx, save_png=True, png_path=png)
    elif site_id == "dem_with_compression_rgb":
        from python_src.toolbox.DEM.dem_atariiii_plot_with_compression_rgb import (
            dem_atariiii_plot_with_compression_rgb,
        )

        dem_atariiii_plot_with_compression_rgb(
            fence, plot_ctx, save_png=True, png_path=png
        )
    elif site_id == "dem_orbits_after":
        from python_src.toolbox.DEM.dem_atariiii_plot_orbits_after import (
            dem_atariiii_plot_orbits_after,
        )

        dem_atariiii_plot_orbits_after(fence, plot_ctx, save_png=True, png_path=png)
    else:
        raise ValueError(f"unknown native plot site_id={site_id!r}")

    if not png.is_file():
        raise RuntimeError(f"native plot did not write PNG: {png}")
    return png


def attach_native_plot_hooks(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare plot state on ctx after preamble Entries 1–12 (vb_call1 PDP present).

    Expects ``PDP_generate`` (gameplay), basin series keys, ``hid``, MDP for post_sort.
    """
    plot_ctx = build_native_plot_ctx(ctx)
    out_dir = native_plot_png_dir()
    written: list[str] = []

    # Script-order early fences (still on ctx after preamble).
    if "PDP_generate" in ctx:
        p = run_native_plots_at_fence(
            "dem_gameplay", ctx["PDP_generate"], plot_ctx, out_dir=out_dir
        )
        written.append(str(p))

    basin = {k: ctx[k] for k in ("NS", "NU", "NA", "NO", "NH") if k in ctx}
    if len(basin) == 5:
        p = run_native_plots_at_fence(
            "dem_attractors_basin", basin, plot_ctx, out_dir=out_dir
        )
        written.append(str(p))

    if "hid" in ctx and "MDP" in ctx:
        payload = {"b1": _unwrap_b1_from_mdp(ctx["MDP"]), "hid": ctx["hid"]}
        p = run_native_plots_at_fence(
            "dem_attractors_mdp_post_sort", payload, plot_ctx, out_dir=out_dir
        )
        written.append(str(p))

    # Generative AI — post vb_call1 (ctx['PDP'] still call1 here).
    p = run_native_plots_at_fence(
        "dem_generative_ai", ctx["PDP"], plot_ctx, out_dir=out_dir
    )
    written.append(str(p))
    ctx["PDP_call1"] = copy.deepcopy(ctx["PDP"])

    ctx["_optim1full_native_plot"] = {
        "enabled": True,
        "out_dir": str(out_dir),
        "plot_ctx": plot_ctx,
        "pngs": written,
        "F_cols": [],
    }
    return ctx


def native_nr_structure_f_hook(ctx: dict[str, Any]):
    """Accumulate structure ``F`` columns during NR (pre-merge); plot at i=NR with RGB."""
    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
        atari_nr_replications,
    )
    from python_src.toolbox.DEM.dem_atariiii_structure_learning_f import (
        structure_learning_f_column,
    )

    nr_final = int(atari_nr_replications())
    plot_state = ctx["_optim1full_native_plot"]
    plot_ctx = plot_state["plot_ctx"]
    out_dir = Path(plot_state["out_dir"])
    gdp_id = plot_ctx["GDP"]["id"]
    cols: list[np.ndarray] = plot_state["F_cols"]

    def _pre_merge(game_i: int, pdp: dict[str, Any], mdp: list[dict[str, Any]]) -> None:
        cols.append(structure_learning_f_column(pdp, mdp, gdp_id))

    def _on_pdp(game_i: int, pdp: dict[str, Any]) -> None:
        if int(game_i) != nr_final:
            return
        p = run_native_plots_at_fence(
            "dem_active_inference_nr", pdp, plot_ctx, out_dir=out_dir
        )
        plot_state["pngs"].append(str(p))
        if len(cols) != nr_final:
            raise RuntimeError(
                f"structure F expected {nr_final} columns, got {len(cols)}"
            )
        F = np.column_stack(cols)
        ctx["F"] = F
        p2 = run_native_plots_at_fence(
            "dem_structure_learning", F, plot_ctx, out_dir=out_dir
        )
        plot_state["pngs"].append(str(p2))

    return _pre_merge, _on_pdp


def run_native_plots_post_call3(ctx: dict[str, Any]) -> None:
    plot_state = ctx["_optim1full_native_plot"]
    plot_ctx = plot_state["plot_ctx"]
    out_dir = Path(plot_state["out_dir"])
    pdp = ctx["PDP_call3"]
    for site in ("dem_before_compression_rgb", "dem_orbits_before"):
        p = run_native_plots_at_fence(site, pdp, plot_ctx, out_dir=out_dir)
        plot_state["pngs"].append(str(p))


def run_native_plots_post_call4(ctx: dict[str, Any]) -> None:
    plot_state = ctx["_optim1full_native_plot"]
    plot_ctx = plot_state["plot_ctx"]
    out_dir = Path(plot_state["out_dir"])
    pdp = ctx["PDP_call4"]
    for site in ("dem_with_compression_rgb", "dem_orbits_after"):
        p = run_native_plots_at_fence(site, pdp, plot_ctx, out_dir=out_dir)
        plot_state["pngs"].append(str(p))


__all__ = [
    "attach_native_plot_hooks",
    "build_native_plot_ctx",
    "native_nr_structure_f_hook",
    "native_plot_png_dir",
    "optim1full_native_plot_requested",
    "run_native_plots_at_fence",
    "run_native_plots_post_call3",
    "run_native_plots_post_call4",
]
