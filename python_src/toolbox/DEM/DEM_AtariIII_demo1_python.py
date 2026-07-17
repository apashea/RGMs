"""
DEMO1 Product A — Python-native demo (shipped entry point).

Wraps ``DEM_AtariIII_demo.py``: entries **1–12** + optional **12PLOT** with native NumPy RNG.
No MATLAB. Writes optional native artifacts under ``tests/demo1/python_native/`` (distinct
from Product B parity fixtures). See ``DEMO1.md`` §4 and §5.
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from typing import Any

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
from python_src.toolbox.DEM.entry12_plot import entry12plot_timestamp, run_entry12plot
from tests.demo1.demo1_native_fixtures import (
    DEMO1_NATIVE_LADDER_ENTRY_STOPS,
    capture_env_for_native_dump,
    collect_driver_captures_to_fixtures,
    write_demo1_native_manifest,
)
from tests.demo1.demo1_native_rng import seed_native_driver_rng
from tests.demo1.demo1_paths import (
    demo1_python_native_12plot_png_path,
    demo1_python_native_dir,
    demo1_python_native_driver_ctx_path,
    demo1_python_native_pdp_path,
)


def _repo_root() -> Path:
    return _repo


def _plot_ctx_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in ("RGB", "GDP", "Nm", "PDP") if k not in ctx]
    if missing:
        raise KeyError(f"DEMO1 plot requires driver keys {missing!r} after entry_stop=12")
    return {
        "RGB": ctx["RGB"],
        "GDP": ctx["GDP"],
        "Nm": int(ctx["Nm"]),
    }


def _save_native_artifacts(ctx: dict[str, Any]) -> dict[str, Path]:
    """Persist Product A outputs under ``tests/demo1/python_native/`` (not parity fixtures)."""
    out_dir = demo1_python_native_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    driver_path = demo1_python_native_driver_ctx_path()
    pdp_path = demo1_python_native_pdp_path()
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


def run_dem_atariiii_demo1_python(
    *,
    plot: bool = True,
    save_png: bool = True,
    png_path: Path | None = None,
    repo_root: Path | None = None,
    save_artifacts: bool = False,
) -> dict[str, Any]:
    seed = seed_native_driver_rng()
    if seed is not None:
        print(f"[DEM_AtariIII_demo1_python] native RNG seed={seed} (MATLAB rng(2) intent)", file=sys.stderr)
    cap_env = capture_env_for_native_dump() if save_artifacts else {}
    old_env = {k: os.environ.get(k) for k in cap_env}
    try:
        if cap_env:
            os.environ.update(cap_env)
        ctx = run_dem_atariiii(entry_stop=12)
    finally:
        for k in cap_env:
            if old_env[k] is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old_env[k]
    root = repo_root or _repo_root()
    if plot:
        plot_ctx = _plot_ctx_from_driver_ctx(ctx)
        if png_path is None and save_artifacts:
            png_path = demo1_python_native_12plot_png_path(entry12plot_timestamp())
        j, k, h, out_png = run_entry12plot(
            ctx["PDP"],
            plot_ctx,
            repo_root=root,
            save_png=save_png,
            png_path=png_path,
        )
        ctx["entry12plot"] = {"J": j, "K": k, "h": h, "png": out_png}
    if save_artifacts:
        collect_driver_captures_to_fixtures()
        write_demo1_native_manifest(rng_seed=seed, entry_stops=DEMO1_NATIVE_LADDER_ENTRY_STOPS)
        saved = _save_native_artifacts(ctx)
        ctx["demo1_python_native_artifacts"] = {k: str(v) for k, v in saved.items()}
        for n in DEMO1_NATIVE_LADDER_ENTRY_STOPS:
            print(
                f"[DEM_AtariIII_demo1_python] native authority entry {n:02d} fixture installed",
                file=sys.stderr,
            )
    return ctx


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DEMO1 Product A — Python-native DEM_AtariIII through 12PLOT (see DEMO1.md)."
    )
    parser.add_argument("--no-plot", action="store_true", help="Skip ENTRY 12PLOT.")
    parser.add_argument("--no-save-png", action="store_true", help="12PLOT without PNG.")
    parser.add_argument(
        "--no-save-artifacts",
        action="store_true",
        help="Do not write tests/demo1/python_native/*.pkl (smoke/tests).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ctx = run_dem_atariiii_demo1_python(
        plot=not args.no_plot,
        save_png=not args.no_save_png,
        save_artifacts=not args.no_save_artifacts,
    )
    if args.no_plot:
        print("[DEM_AtariIII_demo1_python] entries 1–12 complete (plot skipped).", file=sys.stderr)
    else:
        png = ctx.get("entry12plot", {}).get("png")
        arts = ctx.get("demo1_python_native_artifacts", {})
        print(
            f"[DEM_AtariIII_demo1_python] entries 1–12 + 12PLOT complete. png={png!s} artifacts={arts!s}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
