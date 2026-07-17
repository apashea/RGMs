"""
OPTIM1FULL Product A — Python-native full ``DEM_AtariIII.m`` compute (W3).

Wraps ``run_dem_atariiii_optim_full()`` (Entries 1–12 + NR + VB calls 3–4) with
native RNG and ``spm_MDP_VB_XXX_optim`` (no Model B ledger / Engine MI-eig-sort).
Optional final-frame plots: ``--plot`` / ``RGMS_OPTIM1FULL_NATIVE_PLOT=1``.
Normative plan: ``OPTIM1FULL.md`` § **W3 NATIVE + COLAB1 — plan and living status**.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[4]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim_full import run_dem_atariiii_optim_full
from python_src.toolbox.DEM.native_driver_rng import seed_native_driver_rng


def run_dem_atariiii_optim1full_python() -> dict:
    seed = seed_native_driver_rng()
    if seed is not None:
        print(f"[OPTIM1FULL Product A] native RNG seed={seed} (MATLAB rng(2) intent)", file=sys.stderr)
    ctx = run_dem_atariiii_optim_full()
    np_count = ctx.get("optim1full_np")
    print(f"[OPTIM1FULL Product A] optim1full_np={np_count}", file=sys.stderr)
    return ctx


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "OPTIM1FULL Product A (W3 native) — full DEM_AtariIII compute, "
            "optim VB (see OPTIM1FULL.md § W3 NATIVE + COLAB1)."
        )
    )
    p.add_argument(
        "--plot",
        action="store_true",
        help=(
            "Enable final-frame native plots (sets RGMS_OPTIM1FULL_NATIVE_PLOT=1). "
            "Writes PNGs under visualizations/optim1full_native/; not MATLAB parity."
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)
    if ns.plot:
        os.environ["RGMS_OPTIM1FULL_NATIVE_PLOT"] = "1"
    ctx = run_dem_atariiii_optim1full_python()
    print(f"[OPTIM1FULL Product A] complete keys={sorted(ctx.keys())}", file=sys.stderr)
    native_meta = ctx.get("_optim1full_native_plot")
    if isinstance(native_meta, dict):
        print(
            f"[OPTIM1FULL Product A] native_png_count={len(native_meta.get('pngs', []))}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
