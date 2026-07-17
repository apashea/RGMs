#!/usr/bin/env python3
"""OPTIM1 consolidated parity gate — run before further optimization work.

Tier **1** (fast): per-function ``*_optim`` oracle pytest suite (~2 min).
Tier **2** (slow): production-scale Entry **3, 7, 8+9, 10** vs DEMO1 authority (~15–35 min).
Tier **3** (full orchestrator): ``run_full_parity()`` Phases **A–D** with wall timing.

Authority: **read-only** ``tests/demo1/fixtures/`` (DEMO1 Product B). Never mutates DEMO1 mats.

Usage (repo root)::

    python tests/demo1/optim1/optim1_parity_gate.py --tier1
    python tests/demo1/optim1/optim1_parity_gate.py --tier2
    python tests/demo1/optim1/optim1_parity_gate.py --tier2 --fresh
    python tests/demo1/optim1/optim1_parity_gate.py --tier3
    python tests/demo1/optim1/optim1_parity_gate.py --tier3 --fresh
    python tests/demo1/optim1/optim1_parity_gate.py --all
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

from tests.demo1.optim1.optim1_authority import assert_demo1_authority_present
from tests.demo1.optim1.optim1_env import apply_optim1_env
from tests.demo1.optim1.optim1_parity_phases import authority_missing_report, run_full_parity, run_phase_b_optim_only

_TIER1_TARGETS = (
    "tests/oracle/toolbox/DEM/test_spm_MDP_generate_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_merge_structure_learning_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_information_distance_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_unique_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_set_goals_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_RDP_compress_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_RDP_basin_optim.py",
    "tests/oracle/toolbox/DEM/test_spm_RDP_sort_optim.py",
    "tests/oracle/toolbox/DEM/test_optim1_entry89_capture_regression.py",
    "tests/oracle/toolbox/DEM/test_optim1_entry89_unique_capture.py",
    "tests/demo1/optim1/test_optim1_paths.py",
    "tests/demo1/optim1/test_optim1_checkpoint_resume.py",
)

_RESET_SCRIPT = _REPO / "python_src" / "optimized" / "toolbox" / "DEM" / "DEM_AtariIII_optim1_parity_reset.py"


def _run_tier1() -> None:
    print("[OPTIM1 parity gate] Tier 1 — fast oracle pytest", file=sys.stderr)
    cmd = [sys.executable, "-m", "pytest", *_TIER1_TARGETS, "-q"]
    subprocess.run(cmd, cwd=str(_REPO), check=True)


def _run_tier2(*, fresh: bool = False) -> None:
    label = "fresh compare" if fresh else "checkpoint-aware"
    print(
        f"[OPTIM1 parity gate] Tier 2 — Entry 3/7/8+9/10 scale vs DEMO1 ({label})",
        file=sys.stderr,
    )
    assert_demo1_authority_present()
    run_phase_b_optim_only(fresh=fresh)


def _run_tier3(*, fresh: bool = False) -> float:
    label = "after OPTIM1 reset" if fresh else "checkpoint-aware"
    print(
        f"[OPTIM1 parity gate] Tier 3 — full Product B Phases A–D ({label})",
        file=sys.stderr,
    )
    if fresh:
        if not _RESET_SCRIPT.is_file():
            raise FileNotFoundError(f"missing reset script: {_RESET_SCRIPT}")
        subprocess.run([sys.executable, str(_RESET_SCRIPT)], cwd=str(_REPO), check=True)
    t0 = time.perf_counter()
    wall = run_full_parity()
    print(
        f"[OPTIM1 parity gate] Tier 3 wall_s={wall:.3f} (gate harness {time.perf_counter() - t0:.3f})",
        file=sys.stderr,
    )
    return wall


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 parity gate (see OPTIM1.md §8)")
    p.add_argument("--tier1", action="store_true", help="Fast oracle pytest only")
    p.add_argument("--tier2", action="store_true", help="Entry 3/7/8+9/10 scale gates vs DEMO1")
    p.add_argument(
        "--tier3",
        action="store_true",
        help="Full Product B orchestrator Phases A–D (see --fresh)",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="With --tier2: ignore checkpoints, run --skip-write compares only; "
        "with --tier3: reset OPTIM1 checkpoints then full orchestrator",
    )
    p.add_argument("--all", action="store_true", help="Tier 1 then Tier 2")
    p.add_argument("--check-authority", action="store_true", help="List missing DEMO1 authority only")
    args = p.parse_args(argv)

    apply_optim1_env()

    if args.check_authority:
        n, lines = authority_missing_report()
        if n:
            print(f"[OPTIM1 parity gate] missing DEMO1 authority: {n}", file=sys.stderr)
            for line in lines:
                print(line, file=sys.stderr)
            return 2
        print("[OPTIM1 parity gate] DEMO1 authority OK", file=sys.stderr)
        return 0

    if not (args.tier1 or args.tier2 or args.tier3 or args.all):
        p.print_help()
        return 2

    if args.tier1 or args.all:
        _run_tier1()
    if args.tier2 or args.all:
        _run_tier2(fresh=args.fresh)
    if args.tier3:
        _run_tier3(fresh=args.fresh)

    print("[OPTIM1 parity gate] PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
