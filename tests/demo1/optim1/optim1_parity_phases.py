"""OPTIM1 parity phase runners (invoked by ``DEM_AtariIII_optim1_parity.py``).

Phase **A** — verify DEMO1 authority (no MATLAB re-dump).
Phase **B** — FSL backward **1→11**: fidelity scripts for entries **1–2, 4–6, 11**;
optim scale runners for **3, 7, 8+9, 10** vs DEMO1 mats (Entry **10** = MATLAB-eig).
Entry **8+9** = ``optim1_run_entry89_scale.py`` only (merge+basin; not merge-only Entry **8**).
Phase **C** — delegate to DEMO1 Entry **12** lane (authority = DEMO1 fixtures).
Phase **D** — 12PLOT pytest + shipped PNG under ``visualizations/optim1/``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from tests.demo1.demo1_checkpoint_resume import log_checkpoint_skip
from tests.demo1.demo1_parity_phases import run_phase_c
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root
from tests.demo1.optim1.optim1_authority import assert_demo1_authority_present, missing_demo1_authority
from tests.demo1.optim1.optim1_checkpoint_resume import (
    log_optim1_checkpoint_skip,
    optim1_checkpoint_present,
    optim1_phase_b_units,
)
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir, optim1_shipped_parity_png

_REPO = demo1_repo_root()
_ORACLE_DEM = _REPO / "tests" / "oracle" / "toolbox" / "DEM"
_OPTIM_HUB = _REPO / "tests" / "demo1" / "optim1"


def _env_base() -> dict[str, str]:
    env = os.environ.copy()
    env["RGMS_DEMO1_FIXTURES_DIR"] = str(demo1_fixtures_dir())
    env["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = str(demo1_fixtures_dir())
    env["RGMS_OPTIM1_FIXTURES_DIR"] = str(optim1_fixtures_dir())
    env["RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS"] = "1"
    return env


def _run_python(script: Path, extra_env: dict[str, str] | None = None) -> None:
    env = _env_base()
    if extra_env:
        env.update(extra_env)
    print(f"[OPTIM1 parity] python {script.relative_to(_REPO)}", file=sys.stderr)
    subprocess.run([sys.executable, str(script)], cwd=str(_REPO), env=env, check=True)


def _run_pytest(target: str, extra_env: dict[str, str] | None = None) -> None:
    env = _env_base()
    if extra_env:
        env.update(extra_env)
    print(f"[OPTIM1 parity] pytest {target}", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "pytest", target, "-q"],
        cwd=str(_REPO),
        env=env,
        check=True,
    )


def optim1_phase_d_skip() -> bool:
    return optim1_shipped_parity_png().is_file()


def run_phase_a() -> None:
    """Assert DEMO1 authority mats present — OPTIM1 never re-runs DEMO1 Phase A."""
    root = assert_demo1_authority_present()
    print(f"[OPTIM1 parity] Phase A: DEMO1 authority OK ({root})", file=sys.stderr)


def run_phase_b() -> float:
    """FSL backward 1→11 with optim swaps on entries 3, 7, 8+9, 10."""
    t0 = time.perf_counter()
    demo_fix = demo1_fixtures_dir()
    optim_fix = optim1_fixtures_dir()
    optim_fix.mkdir(parents=True, exist_ok=True)

    for unit in optim1_phase_b_units():
        if optim1_checkpoint_present(unit, demo_fixtures=demo_fix, optim_fixtures=optim_fix):
            if unit.optim_lane:
                log_optim1_checkpoint_skip(unit.label, artifact_id=unit.artifact_id)
            else:
                log_checkpoint_skip(unit.label, artifact_id=unit.artifact_id)
            continue

        for name in unit.scripts:
            if unit.optim_lane:
                path = _OPTIM_HUB / name
            else:
                path = _ORACLE_DEM / name
            if not path.is_file():
                raise FileNotFoundError(f"missing Phase B script: {path}")
            if name == "fsl_backward_validate_entry11_through_entry12.py":
                env = _env_base()
                print(
                    f"[OPTIM1 parity] python {path.relative_to(_REPO)} --vb-only",
                    file=sys.stderr,
                )
                subprocess.run(
                    [sys.executable, str(path), "--vb-only"],
                    cwd=str(_REPO),
                    env=env,
                    check=True,
                )
            else:
                _run_python(path)
    return time.perf_counter() - t0


def run_phase_b_optim_only(*, fresh: bool = False) -> None:
    """Run optim entries 3, 7, 8+9, 10 scale gates (critical path before more optimization).

    When ``fresh=True``, ignore OPTIM1 checkpoints and pass ``--skip-write`` (compare only).
    """
    demo_fix = demo1_fixtures_dir()
    optim_fix = optim1_fixtures_dir()
    optim_fix.mkdir(parents=True, exist_ok=True)
    assert_demo1_authority_present(demo_fix)

    for unit in optim1_phase_b_units():
        if not unit.optim_lane:
            continue
        if not fresh and optim1_checkpoint_present(
            unit, demo_fixtures=demo_fix, optim_fixtures=optim_fix
        ):
            log_optim1_checkpoint_skip(unit.label, artifact_id=unit.artifact_id)
            continue
        for name in unit.scripts:
            path = _OPTIM_HUB / name
            if not path.is_file():
                raise FileNotFoundError(f"missing optim scale script: {path}")
            if fresh:
                env = _env_base()
                argv = [sys.executable, str(path), "--skip-write"]
                print(
                    f"[OPTIM1 parity] python {path.relative_to(_REPO)} --skip-write (fresh)",
                    file=sys.stderr,
                )
                subprocess.run(argv, cwd=str(_REPO), env=env, check=True)
            else:
                _run_python(path)


def run_phase_d() -> None:
    """12PLOT pytest + shipped parity PNG under ``visualizations/optim1/``."""
    if optim1_phase_d_skip():
        log_optim1_checkpoint_skip("Phase D visual", artifact_id="D3_optim_png")
        return
    _run_pytest(str(_ORACLE_DEM / "test_spm_show_RGB_entry12plot.py"))
    script = (
        "from pathlib import Path\n"
        "import shutil\n"
        "from tests.demo1.optim1.optim1_paths import optim1_repo_root, optim1_shipped_parity_png\n"
        "from python_src.optimized.toolbox.DEM.entry12_plot_optim import run_entry12plot_optim_phase_b_visual_review\n"
        "root = optim1_repo_root()\n"
        "_, _, _, _, compare = run_entry12plot_optim_phase_b_visual_review(repo_root=root)\n"
        "if compare is None or not compare.is_file():\n"
        "    raise SystemExit('missing 12PLOT compare PNG')\n"
        "shipped = optim1_shipped_parity_png()\n"
        "shipped.parent.mkdir(parents=True, exist_ok=True)\n"
        "shutil.copy2(compare, shipped)\n"
        "print(f'[OPTIM1 parity] shipped PNG {shipped}')\n"
    )
    env = _env_base()
    print("[OPTIM1 parity] python (subprocess) entry12plot phase B visual review", file=sys.stderr)
    subprocess.run([sys.executable, "-c", script], cwd=str(_REPO), env=env, check=True)


def run_full_parity() -> float:
    """Phases A→D; return total wall seconds."""
    t0 = time.perf_counter()
    for label, fn in (
        ("Phase A", run_phase_a),
        ("Phase B", run_phase_b),
        ("Phase C", run_phase_c),
        ("Phase D", run_phase_d),
    ):
        t_phase = time.perf_counter()
        result = fn()
        phase_s = (result if isinstance(result, float) else None) or (time.perf_counter() - t_phase)
        print(f"[OPTIM1 parity] {label} wall_s={phase_s:.3f}", file=sys.stderr)
    wall = time.perf_counter() - t0
    print(f"[OPTIM1 parity] full sign-off wall_s={wall:.3f}", file=sys.stderr)
    return wall


def authority_missing_report() -> tuple[int, list[str]]:
    missing = missing_demo1_authority()
    lines = [f"  [{m.artifact_id}] {m.relative_path}" for m in missing]
    return len(missing), lines
