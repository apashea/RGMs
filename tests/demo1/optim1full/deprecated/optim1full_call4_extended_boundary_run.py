#!/usr/bin/env python3
"""OPTIM1FULL call4 — extended boundary capture/compare (t=10,20,30) one step at a time.

Steps (never run in parallel):
  matlab  — script **1b** re-dump call4 via ``matlab_custom/optim1full/`` dump fork
  pytest3 — script **3** with extended-boundary monkey-patch (no ``spm_MDP_VB_XXX.py`` edit)
  compare — extended boundary py vs mat witness compare
  lean    — re-run lean ``*_in.mat`` rewrite for call4 (if sidecars stale)

See ``OPTIM1FULL.md`` § Call4 VB investigation.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

TAG = "rgms_atari_optim1full_call4"


def _fixtures() -> Path:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    return optim1full_fixtures_dir()


def _backup_call4_bands(fix: Path) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = fix.parent / "probe" / f"backup_call4_pre_extended_{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for band in ("12D", "12E", "12F"):
        for ext in (".mat", ".pkl"):
            src = fix / f"DEMAtariIII_entry12_{TAG}_{band}{ext}"
            if src.is_file():
                shutil.copy2(src, dest / src.name)
    return dest


def _step_matlab() -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

    fix = _fixtures()
    backup = _backup_call4_bands(fix)
    print(f"[optim1full call4 extended] backup -> {backup}", flush=True)

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        opt_posix = str((_REPO / "matlab_custom" / "optim1full").resolve()).replace("\\", "/")
        entry12_posix = str((_REPO / "matlab_custom" / "entry12").resolve()).replace("\\", "/")
        repo_posix = str(_REPO.resolve()).replace("\\", "/")
        eng.cd(repo_posix, nargout=0)
        eng.eval(f"addpath('{opt_posix}','-begin');", nargout=0)
        eng.eval(f"addpath('{entry12_posix}');", nargout=0)
        fix_s = str(fix.resolve()).replace("\\", "/")
        eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix_s, nargout=0)
        eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix_s, nargout=0)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_call4_extended_boundaries');",
            nargout=0,
        )
    finally:
        eng.quit()
    print("[optim1full call4 extended] matlab dump done", flush=True)
    return 0


def _step_pytest3() -> int:
    """Script **3** — tier **3f** oracle test (call4 boundary keys in ``spm_MDP_VB_XXX``)."""
    from tests.demo1.optim1full.optim1full_rng_authority import optim1full_entry12_subprocess_env

    env = optim1full_entry12_subprocess_env(TAG)
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    print(
        "[optim1full call4 extended] script 3 in-process "
        f"(test_xxx_12_fsl_rdp_to_pdp_pkl tag={TAG!r})",
        flush=True,
    )
    try:
        from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import (
            test_xxx_12_fsl_rdp_to_pdp_pkl,
        )

        test_xxx_12_fsl_rdp_to_pdp_pkl()
        print("[optim1full call4 extended] script 3 done", flush=True)
        return 0
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def _step_compare() -> int:
    from tests.demo1.optim1full.optim1full_call4_extended_boundary_compare import run_compare

    run_compare()
    return 0


def _step_lean() -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_rewrite_entry12_lean_sidecars import _rewrite_tags

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _rewrite_tags(eng, [TAG], _fixtures())
    finally:
        eng.quit()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "step",
        choices=("matlab", "pytest3", "compare", "lean"),
        help="one step only",
    )
    args = p.parse_args()
    steps = {
        "matlab": _step_matlab,
        "pytest3": _step_pytest3,
        "compare": _step_compare,
        "lean": _step_lean,
    }
    return int(steps[args.step]())


if __name__ == "__main__":
    raise SystemExit(main())
