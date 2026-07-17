"""
DEMO1 Product B — strict MATLAB–Python parity orchestrator.

Fresh-user contract (see ``DEMO1.md`` §0, §4):
- Always sets ``RGMS_DEMO1_FIXTURES_DIR`` and ``RGMS_ENTRY12_CAPTURE_OUT_DIR`` to
  ``tests/demo1/fixtures`` (empty on clone; never reads oracle fixtures by default).
- Generates fixtures via Phase A–D producers when missing.

Usage (from repo root)::

    python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity.py
    python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity.py --check-only
    python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity.py --list-missing
    python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity.py --phase A   # dev: one phase
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from tests.demo1.demo1_env import apply_shipped_fixture_env
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root, demo1_matlab_src_dem_dir
from tests.demo1.demo1_parity_phases import run_full_parity, run_phase_a, run_phase_b, run_phase_c, run_phase_d
from tests.demo1.fixture_registry import FixtureArtifact, all_artifacts, missing_artifacts

_ORACLE_DEM = _repo / "tests" / "oracle" / "toolbox" / "DEM"


def _require_paths() -> list[str]:
    errors: list[str] = []
    for rel in (
        "matlab_compat.py",
        "matlab_src/toolbox/DEM",
        "matlab_custom/demo1/demo1_fixtures_dir.m",
        "matlab_custom/demo1/DEMO1_dump_all_fixtures.m",
        "tests/demo1/fixture_registry.py",
        "tests/demo1/demo1_parity_phases.py",
    ):
        if not (_repo / rel).exists():
            errors.append(f"missing required path: {rel}")
    if not _ORACLE_DEM.is_dir():
        errors.append("missing tests/oracle/toolbox/DEM parity scripts")
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
        return False, "matlabengine not installed (pip install matlabengine; see rgms-atari.yml)"
    return True, matlab


def check_prerequisites(*, require_matlab: bool) -> list[str]:
    errors = _require_paths() + _require_python_deps()
    ok, msg = _matlab_available()
    if require_matlab and not ok:
        errors.append(msg)
    elif ok:
        print(f"[DEMO1 parity] MATLAB: {msg}", file=sys.stderr)
    else:
        print(f"[DEMO1 parity] note: {msg}", file=sys.stderr)
    return errors


def list_missing_report() -> int:
    fix = demo1_fixtures_dir()
    missing = missing_artifacts(fix)
    print(f"[DEMO1 parity] fixture root: {fix}", file=sys.stderr)
    print(f"[DEMO1 parity] missing artifacts: {len(missing)} / {len(all_artifacts())}", file=sys.stderr)
    for art in missing:
        print(f"  [{art.phase}] {art.artifact_id}: {art.relative_path}  <- {art.producer}")
    return 0 if not missing else 2


def _run_matlab_function(mdir: Path, func: str, extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    cmd = [
        "matlab",
        "-batch",
        f"cd('{mdir.as_posix()}'); {func};",
    ]
    print(f"[DEMO1 parity] matlab -batch {func}", file=sys.stderr)
    subprocess.run(cmd, cwd=str(_repo), env=env, check=True)


def _run_python_script(script: Path, extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    print(f"[DEMO1 parity] python {script.relative_to(_repo)}", file=sys.stderr)
    subprocess.run([sys.executable, str(script)], cwd=str(_repo), env=env, check=True)


def _produce_phase_a_legacy(art: FixtureArtifact) -> None:
    """Run one Phase A producer (MATLAB or Python) — dev ``--phase A`` only."""
    prod = art.producer
    if prod.startswith("matlab_custom/"):
        rel = prod.split()[0]
        mpath = _repo / rel
        mdir = mpath.parent
        func = mpath.stem
        extra: dict[str, str] = {}
        if "SKIP_CALL2=1" in prod:
            extra["RGMS_ENTRY12_CAPTURE_SKIP_CALL2"] = "1"
        _run_matlab_function(mdir, func, extra_env=extra or None)
        return
    if prod.startswith("tests/"):
        script = _repo / prod.split()[0]
        _run_python_script(script)
        return
    raise NotImplementedError(f"Phase A producer not wired: {prod}")


def run_phase_a_legacy(*, force: bool = False) -> int:
    """Legacy per-artifact Phase A (dev only — not user cold start)."""
    fix = demo1_fixtures_dir()
    for art in all_artifacts():
        if art.phase != "A":
            continue
        target = art.path(fix)
        if target.is_file() and not force:
            print(f"[DEMO1 parity] skip {art.artifact_id} (exists)", file=sys.stderr)
            continue
        print(f"[DEMO1 parity] produce {art.artifact_id}", file=sys.stderr)
        _produce_phase_a_legacy(art)
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DEMO1 Product B — strict parity (see DEMO1.md).")
    p.add_argument("--check-only", action="store_true", help="Prerequisites + fixture root only.")
    p.add_argument("--list-missing", action="store_true", help="List missing artifacts under greenfield root.")
    p.add_argument("--phase", choices=("A", "B", "C", "D"), help="Dev: run one phase only.")
    p.add_argument("--force", action="store_true", help="Dev --phase A: re-run producers even if artifact exists.")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    apply_shipped_fixture_env()
    args = _parse_args(argv)
    dev_only = bool(args.check_only or args.list_missing or args.phase)
    require_matlab = not (args.check_only or args.list_missing)
    errors = check_prerequisites(require_matlab=require_matlab)
    if errors:
        for e in errors:
            print(f"[DEMO1 parity] ERROR: {e}", file=sys.stderr)
        return 1
    print(f"[DEMO1 parity] fixture root: {demo1_fixtures_dir()}", file=sys.stderr)
    print(f"[DEMO1 parity] matlab_src DEM: {demo1_matlab_src_dem_dir()}", file=sys.stderr)
    if args.check_only:
        return list_missing_report()
    if args.list_missing:
        return list_missing_report()
    if args.phase == "A":
        run_phase_a()
        return 0
    if args.phase == "B":
        run_phase_b()
        return 0
    if args.phase == "C":
        run_phase_c()
        return 0
    if args.phase == "D":
        run_phase_d()
        return 0
    if dev_only:
        print("[DEMO1 parity] specify --check-only, --list-missing, or --phase", file=sys.stderr)
        return 2
    print("[DEMO1 parity] full sign-off: Phase A → B → C → D", file=sys.stderr)
    run_full_parity()
    missing = missing_artifacts()
    if missing:
        print(f"[DEMO1 parity] still missing {len(missing)} artifact(s) after run", file=sys.stderr)
        return 2
    print("[DEMO1 parity] all registry artifacts present — exit 0", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
