"""
ENTRY DEMO1 — consolidated Python demo for ``DEM_AtariIII.m`` through first VB + 12PLOT.

Runs staged ledger entries **1–12** (compute) via ``run_dem_atariiii(entry_stop=12)``, then
optional **ENTRY 12PLOT** via ``run_entry12plot``. Scope matches ``Atari_example.md`` staged
fence through ``%%% ENTRY 12PLOT`` — **not** active-inference VB calls 2–4 or postponed
*PLOT entries (2PLOT–10PLOT).

Plotting policy: ``Atari_plotting.md``. Entry **12** compute remains frozen in
``spm_MDP_VB_XXX.py``; this module orchestrates only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from typing import Any

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
from python_src.toolbox.DEM.entry12_plot import run_entry12plot


def _repo_root() -> Path:
    return _repo


def _plot_ctx_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Minimal context for ``run_entry12plot`` from ``run_dem_atariiii`` output."""
    missing = [k for k in ("RGB", "GDP", "Nm", "PDP") if k not in ctx]
    if missing:
        raise KeyError(f"DEMO1 plot requires driver keys {missing!r} after entry_stop=12")
    return {
        "RGB": ctx["RGB"],
        "GDP": ctx["GDP"],
        "Nm": int(ctx["Nm"]),
    }


def run_dem_atariiii_demo(
    *,
    plot: bool = True,
    save_png: bool = True,
    png_path: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """
    Run ENTRY DEMO1: entries **1–12** + optional **12PLOT**.

    Parameters
    ----------
    plot
        When ``True``, run the staged 12PLOT fence on ``ctx['PDP']`` (does not re-run VB).
    save_png
        When ``plot`` is ``True``, write a PNG under ``visualizations/`` unless ``png_path`` is set.
    png_path
        Optional explicit PNG path for 12PLOT output.
    repo_root
        Repository root for visualization paths (defaults to RGMs project root).

    Returns
    -------
    dict
        Driver context from ``run_dem_atariiii(entry_stop=12)``. When ``plot`` is ``True``,
        adds ``ctx['entry12plot']`` with keys ``J``, ``K``, ``h``, ``png``.
    """
    ctx = run_dem_atariiii(entry_stop=12)

    if not plot:
        return ctx

    root = repo_root or _repo_root()
    plot_ctx = _plot_ctx_from_driver_ctx(ctx)
    j, k, h, out_png = run_entry12plot(
        ctx["PDP"],
        plot_ctx,
        repo_root=root,
        save_png=save_png,
        png_path=png_path,
    )
    ctx["entry12plot"] = {
        "J": j,
        "K": k,
        "h": h,
        "png": out_png,
    }
    return ctx


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ENTRY DEMO1 — DEM_AtariIII through first VB and 12PLOT (see Atari_example.md)."
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Compute entries 1–12 only; skip ENTRY 12PLOT.",
    )
    parser.add_argument(
        "--no-save-png",
        action="store_true",
        help="Run 12PLOT interactively but do not write a PNG file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ctx = run_dem_atariiii_demo(
        plot=not args.no_plot,
        save_png=not args.no_save_png,
    )
    if args.no_plot:
        print("[DEM_AtariIII_demo] entries 1–12 complete (plot skipped).", file=sys.stderr)
    else:
        png = ctx.get("entry12plot", {}).get("png")
        print(f"[DEM_AtariIII_demo] entries 1–12 + 12PLOT complete. png={png!s}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
