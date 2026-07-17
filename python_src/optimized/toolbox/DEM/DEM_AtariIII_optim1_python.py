"""
OPTIM1 Product A — Python-native demo (optimized driver).

Wraps ``run_dem_atariiii_optim(entry_stop=12)`` + optional **12PLOT**.
Artifacts under ``tests/demo1/optim1/python_native/``. See ``OPTIM1.md`` §2.
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[4]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from typing import Any

from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim
from python_src.toolbox.DEM.entry12_plot import entry12plot_timestamp
from python_src.optimized.toolbox.DEM.entry12_plot_optim_native import (
    run_entry12plot_optim_native,
)
from tests.demo1.demo1_native_rng import seed_native_driver_rng
from tests.demo1.optim1.optim1_paths import (
    optim1_python_native_12plot_png_path,
    optim1_python_native_dir,
    optim1_python_native_driver_ctx_path,
    optim1_python_native_pdp_path,
)


def _repo_root() -> Path:
    return _repo


def _plot_ctx_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in ("RGB", "GDP", "Nm", "PDP") if k not in ctx]
    if missing:
        raise KeyError(f"OPTIM1 plot requires driver keys {missing!r} after entry_stop=12")
    return {
        "RGB": ctx["RGB"],
        "GDP": ctx["GDP"],
        "Nm": int(ctx["Nm"]),
    }


def _save_native_artifacts(ctx: dict[str, Any]) -> dict[str, Path]:
    out_dir = optim1_python_native_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    driver_path = optim1_python_native_driver_ctx_path()
    pdp_path = optim1_python_native_pdp_path()
    keys = (
        "GDP",
        "RGB",
        "MDP",
        "RDP",
        "PDP",
        "Nm",
        "Ne",
        "NS",
        "NU",
        "entry12plot",
    )
    slim = {k: ctx[k] for k in keys if k in ctx}
    with driver_path.open("wb") as f:
        pickle.dump(slim, f, protocol=pickle.HIGHEST_PROTOCOL)
    with pdp_path.open("wb") as f:
        pickle.dump(ctx["PDP"], f, protocol=pickle.HIGHEST_PROTOCOL)
    return {"driver_ctx": driver_path, "pdp": pdp_path}


def run_dem_atariiii_optim1_python(
    *,
    plot: bool = True,
    save_png: bool = True,
    png_path: Path | None = None,
    repo_root: Path | None = None,
    save_artifacts: bool = False,
) -> dict[str, Any]:
    seed = seed_native_driver_rng()
    if seed is not None:
        print(f"[OPTIM1 Product A] native RNG seed={seed} (MATLAB rng(2) intent)", file=sys.stderr)
    ctx = run_dem_atariiii_optim(entry_stop=12)
    root = repo_root or _repo_root()
    if plot:
        plot_ctx = _plot_ctx_from_driver_ctx(ctx)
        if png_path is None and save_png:
            png_path = optim1_python_native_12plot_png_path(entry12plot_timestamp())
        j, k, h, out_png = run_entry12plot_optim_native(
            ctx["PDP"],
            plot_ctx,
            repo_root=root,
            save_png=save_png,
            png_path=png_path,
        )
        ctx["entry12plot"] = {"J": j, "K": k, "h": h, "png": out_png}
    if save_artifacts:
        saved = _save_native_artifacts(ctx)
        ctx["optim1_python_native_artifacts"] = {k: str(v) for k, v in saved.items()}
    return ctx


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OPTIM1 Product A — optimized DEM_AtariIII through 12PLOT (see OPTIM1.md)."
    )
    parser.add_argument("--no-plot", action="store_true", help="Skip ENTRY 12PLOT.")
    parser.add_argument("--no-save-png", action="store_true", help="12PLOT without PNG.")
    parser.add_argument(
        "--no-save-artifacts",
        action="store_true",
        help="Do not write tests/demo1/optim1/python_native/*.pkl.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ctx = run_dem_atariiii_optim1_python(
        plot=not args.no_plot,
        save_png=not args.no_save_png,
        save_artifacts=not args.no_save_artifacts,
    )
    print(f"[OPTIM1 Product A] complete keys={sorted(ctx.keys())}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
