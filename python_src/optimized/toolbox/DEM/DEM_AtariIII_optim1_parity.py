"""
OPTIM1 Product B — strict parity orchestrator (mirrors DEMO1 Product B).

Reuses **DEMO1** ``tests/demo1/fixtures/`` as numerical authority. Phase **A** only
verifies those mats exist (no MATLAB re-dump). Phase **B** runs fidelity FSL scripts
for entries **1–2, 4–6, 11** and optim scale runners for **3, 7, 8, 9, 10** (Entry **4**
stays fidelity MATLAB SL). Phase **C** delegates to DEMO1 Entry **12** lane. Phase **D**
writes ``visualizations/optim1/OPTIM1_matlab_python_parity_12plot.png``.

Usage (repo root)::

    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1_parity.py
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1_parity.py --check-only
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1_parity.py --phase B
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1_parity.py --optim-only --fresh
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Sequence

_repo = Path(__file__).resolve().parents[4]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from tests.demo1.demo1_paths import demo1_fixtures_dir
from tests.demo1.optim1.optim1_authority import missing_demo1_authority
from tests.demo1.optim1.optim1_env import apply_optim1_env
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir
from tests.demo1.optim1.optim1_parity_phases import (
    authority_missing_report,
    run_full_parity,
    run_phase_a,
    run_phase_b,
    run_phase_b_optim_only,
    run_phase_d,
)
from tests.demo1.demo1_parity_phases import run_phase_c


def _require_paths() -> list[str]:
    errors: list[str] = []
    for rel in (
        "python_src/optimized/toolbox/DEM/DEM_AtariIII_optim.py",
        "tests/demo1/optim1/optim1_parity_phases.py",
        "tests/demo1/optim1/optim1_parity_gate.py",
        "tests/demo1/optim1/optim1_run_entry3_scale.py",
        "tests/demo1/optim1/optim1_run_entry7_scale.py",
        "tests/demo1/optim1/optim1_run_entry8_scale.py",
        "tests/demo1/optim1/optim1_run_entry89_scale.py",
        "tests/demo1/optim1/optim1_run_entry10_matlab_eig_scale.py",
    ):
        if not (_repo / rel).exists():
            errors.append(f"missing required path: {rel}")
    return errors


def _require_python_deps() -> list[str]:
    errors: list[str] = []
    for mod in ("numpy", "scipy", "pytest"):
        if importlib.util.find_spec(mod) is None:
            errors.append(f"missing Python package: {mod}")
    return errors


def _matlab_available() -> tuple[bool, str]:
    matlab = shutil.which("matlab")
    if not matlab:
        return False, "matlab not on PATH (install MATLAB 2024b for parity)"
    try:
        import matlab.engine  # noqa: F401
    except ImportError:
        return False, "matlabengine not installed (pip install matlabengine)"
    return True, matlab


def check_prerequisites(*, require_matlab: bool) -> list[str]:
    errors = _require_paths() + _require_python_deps()
    ok, msg = _matlab_available()
    if require_matlab and not ok:
        errors.append(msg)
    elif ok:
        print(f"[OPTIM1 parity] MATLAB: {msg}", file=sys.stderr)
    else:
        print(f"[OPTIM1 parity] note: {msg}", file=sys.stderr)
    return errors


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OPTIM1 Product B — parity (see OPTIM1.md §10).")
    p.add_argument("--check-only", action="store_true", help="Prerequisites + DEMO1 authority check.")
    p.add_argument("--list-missing", action="store_true", help="List missing DEMO1 authority artifacts.")
    p.add_argument("--phase", choices=("A", "B", "C", "D"), help="Run one phase only.")
    p.add_argument(
        "--optim-only",
        action="store_true",
        help="Phase B optim entries 3/8/9/10 only (critical gate before more optimization).",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="With --optim-only: ignore checkpoints, run --skip-write compares only.",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    apply_optim1_env()
    args = _parse_args(argv)
    dev_only = bool(args.check_only or args.list_missing or args.phase or args.optim_only)
    require_matlab = not (args.check_only or args.list_missing)
    errors = check_prerequisites(require_matlab=require_matlab)
    if errors:
        for e in errors:
            print(f"[OPTIM1 parity] ERROR: {e}", file=sys.stderr)
        return 1

    print(f"[OPTIM1 parity] DEMO1 authority: {demo1_fixtures_dir()}", file=sys.stderr)
    print(f"[OPTIM1 parity] OPTIM1 checkpoints: {optim1_fixtures_dir()}", file=sys.stderr)

    if args.check_only or args.list_missing:
        n, lines = authority_missing_report()
        print(f"[OPTIM1 parity] missing DEMO1 authority: {n}", file=sys.stderr)
        for line in lines:
            print(line, file=sys.stderr)
        return 0 if n == 0 else 2

    if args.optim_only:
        run_phase_a()
        run_phase_b_optim_only(fresh=bool(args.fresh))
        print("[OPTIM1 parity] optim-only Phase B complete — exit 0", file=sys.stderr)
        return 0

    if args.phase == "A":
        run_phase_a()
        return 0
    if args.phase == "B":
        run_phase_a()
        wall = run_phase_b()
        print(f"[OPTIM1 parity] Phase B wall_s={wall:.3f}", file=sys.stderr)
        return 0
    if args.phase == "C":
        run_phase_a()
        run_phase_c()
        return 0
    if args.phase == "D":
        run_phase_a()
        run_phase_d()
        return 0

    if dev_only:
        print("[OPTIM1 parity] specify --check-only, --list-missing, --phase, or --optim-only", file=sys.stderr)
        return 2

    print("[OPTIM1 parity] full sign-off: Phase A → B → C → D", file=sys.stderr)
    wall = run_full_parity()
    still = missing_demo1_authority()
    if still:
        print(f"[OPTIM1 parity] DEMO1 authority missing after run: {len(still)}", file=sys.stderr)
        return 2
    print(f"[OPTIM1 parity] complete — exit 0 (wall_s={wall:.3f})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
