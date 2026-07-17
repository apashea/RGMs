#!/usr/bin/env python3
"""OPTIM1 Product A native gate — optim ≡ DEMO1 native authority (no MATLAB).

Tier **1** (fast): smoke + path tests (~seconds).
Tier **2** (medium): per-entry native scale + Entry **8+9** fidelity/optim compare (~10–15 min).
Tier **3** (slow): optim driver only vs **frozen** DEMO1 native ladder fixtures (~5 min per
``--entry-stop``); **strict** compare. Authority = ``tests/demo1/python_native/fixtures/``
from **one** ``demo1_native_dump.py`` run (seed **2**). **Do not** re-run fidelity DEMO1
during OPTIM1 development.

``--paired``: optional audit — same compare vs **live** fidelity run (~40 min Entry **3**).

Distinct from ``optim1_parity_gate.py`` (Product B vs DEMO1 MATLAB fixtures).

Usage (repo root)::

    python tests/demo1/demo1_native_dump.py          # once — builds authority fixtures
    python tests/demo1/optim1/optim1_native_gate.py --tier1
    python tests/demo1/optim1/optim1_native_gate.py --tier2
    python tests/demo1/optim1/optim1_native_gate.py --tier3 --entry-stop 3
    python tests/demo1/optim1/optim1_native_gate.py --all
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_native_rng import seed_native_driver_rng
from tests.demo1.optim1.optim1_env import apply_optim1_env
from tests.demo1.demo1_native_fixtures import assert_demo1_native_fixtures_present
from tests.demo1.optim1.optim1_native_compare import (
    assert_native_driver_ctx_equal,
    assert_native_driver_ctx_equal_at_entry_stop,
    compare_entry89_fidelity_vs_optim_native,
    load_demo1_native_authority_ctx,
)

_OPTIM_HUB = _REPO / "tests" / "demo1" / "optim1"


def _seed_and_log(label: str) -> int | None:
    seed = seed_native_driver_rng()
    if seed is not None:
        print(f"[OPTIM1 native gate] {label} native RNG seed={seed}", file=sys.stderr)
    else:
        print(
            f"[OPTIM1 native gate] {label} native RNG not reset (RGMS_NATIVE_DRIVER_RNG_SEED=none)",
            file=sys.stderr,
        )
    return seed


def _run_pytest(target: str) -> None:
    print(f"[OPTIM1 native gate] pytest {target}", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "pytest", target, "-q"],
        cwd=str(_REPO),
        check=True,
    )


def _run_scale(script: str, *, skip_write: bool = True) -> None:
    path = _OPTIM_HUB / script
    argv = [sys.executable, str(path)]
    if skip_write:
        argv.append("--skip-write")
    print(f"[OPTIM1 native gate] python {path.relative_to(_REPO)}", file=sys.stderr)
    subprocess.run(argv, cwd=str(_REPO), check=True)


def _run_tier1() -> None:
    print("[OPTIM1 native gate] Tier 1 — smoke + paths", file=sys.stderr)
    _run_pytest("tests/demo1/optim1/test_optim1_paths.py")
    _run_pytest("tests/demo1/optim1/test_DEM_AtariIII_optim_smoke.py")


def _run_tier2() -> None:
    print("[OPTIM1 native gate] Tier 2 — per-entry native compares", file=sys.stderr)
    _run_scale("optim1_run_entry4_scale.py")
    _run_scale("optim1_run_entry10_scale.py")
    print("[OPTIM1 native gate] Entry 8+9 fidelity vs optim native", file=sys.stderr)
    compare_entry89_fidelity_vs_optim_native()
    print("[OPTIM1 native gate] Entry 8+9 native compare OK", file=sys.stderr)


def _run_tier3(*, paired: bool = False, entry_stop: int = 12) -> float:
    print(
        f"[OPTIM1 native gate] Tier 3 — entry_stop={entry_stop} optim driver"
        + (" vs live fidelity (audit)" if paired else " vs DEMO1 native authority fixture"),
        file=sys.stderr,
    )
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim

    import io
    from contextlib import redirect_stderr

    if not paired:
        assert_demo1_native_fixtures_present()
        print(
            "[OPTIM1 native gate] Tier 3 vs frozen fixtures — build once with "
            "python tests/demo1/demo1_native_dump.py (seed 2)",
            file=sys.stderr,
        )
    _seed_and_log("optim run")
    buf = io.StringIO()
    t0 = time.perf_counter()
    with redirect_stderr(buf):
        ctx = run_dem_atariiii_optim(entry_stop=entry_stop)
    wall_s = time.perf_counter() - t0
    stderr = buf.getvalue()
    if stderr:
        print(stderr, file=sys.stderr, end="")

    if paired:
        from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii

        _seed_and_log("fidelity run")
        buf2 = io.StringIO()
        with redirect_stderr(buf2):
            ref_ctx = run_dem_atariiii(entry_stop=entry_stop)
        ref_stderr = buf2.getvalue()
        if ref_stderr:
            print(ref_stderr, file=sys.stderr, end="")
        assert_native_driver_ctx_equal_at_entry_stop(ctx, ref_ctx, entry_stop)
    else:
        ref_ctx = load_demo1_native_authority_ctx(entry_stop=entry_stop)
        assert_native_driver_ctx_equal_at_entry_stop(ctx, ref_ctx, entry_stop)

    print(
        f"[OPTIM1 native gate] Tier 3 OK: full driver wall_s={wall_s:.3f}",
        file=sys.stderr,
    )
    return wall_s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Product A native gate (see OPTIM1.md §8)")
    p.add_argument("--tier1", action="store_true")
    p.add_argument("--tier2", action="store_true")
    p.add_argument("--tier3", action="store_true")
    p.add_argument("--all", action="store_true", help="Tier 1 + 2 + 3")
    p.add_argument(
        "--benchmark",
        action="store_true",
        help="Run optim1_benchmark_native_full.py after tiers",
    )
    p.add_argument(
        "--paired",
        action="store_true",
        help="Tier 3 audit only: compare optim to live fidelity run (~40 min Entry 3; seed 2)",
    )
    p.add_argument(
        "--entry-stop",
        type=int,
        default=12,
        metavar="N",
        help="Tier 3: driver entry_stop (ladder 3, 7, 9, 12; default 12)",
    )
    args = p.parse_args(argv)

    apply_optim1_env()

    if not (args.tier1 or args.tier2 or args.tier3 or args.all or args.benchmark):
        p.print_help()
        return 2

    if args.tier1 or args.all:
        _run_tier1()
    if args.tier2 or args.all:
        _run_tier2()
    if args.tier3 or args.all:
        entry_stop = int(args.entry_stop)
        if entry_stop < 1 or entry_stop > 12:
            raise SystemExit("--entry-stop must be 1..12")
        _run_tier3(paired=bool(args.paired), entry_stop=entry_stop)
    if args.benchmark:
        print("[OPTIM1 native gate] benchmark — native full driver", file=sys.stderr)
        subprocess.run(
            [sys.executable, str(_OPTIM_HUB / "optim1_benchmark_native_full.py")],
            cwd=str(_REPO),
            check=True,
        )

    print("[OPTIM1 native gate] PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
