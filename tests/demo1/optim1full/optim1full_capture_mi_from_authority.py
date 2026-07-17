#!/usr/bin/env python3
"""OPTIM1FULL — MI-382/429 authority re-capture from Python ``MDP_post_nr``.

Runs MATLAB ``capture_optim1full_mi_from_authority``: loads on-disk
``DEMAtariIII_optim1full_MDP_post_nr.mat`` (``capture_optim1full_python_product_b``),
writes MI boundary + causal mats only. Does **not** overwrite authority ``MDP_post_nr``.

Then refreshes Python MI pkls and runs tier **1** compare scripts unless ``--matlab-only``.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _backup_mi_artifacts(fixtures: Path, backup_dir: Path) -> int:
    from tests.demo1.optim1full.optim1full_authority import optim1full_required_mi_mats

    backup_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in optim1full_required_mi_mats():
        src = fixtures / name
        if src.is_file():
            shutil.copy2(src, backup_dir / name)
            n += 1
    for name in (
        "DEMAtariIII_optim1full_mi382_post.pkl",
        "DEMAtariIII_optim1full_mi429_post.pkl",
    ):
        src = fixtures / name
        if src.is_file():
            shutil.copy2(src, backup_dir / name)
            n += 1
    return n


def _run_cmd(cmd: list[str]) -> int:
    print(f"[optim1full_capture_mi] RUN {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=str(_REPO))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Do not copy prior MI mats/pkls to deprecated/",
    )
    parser.add_argument(
        "--matlab-only",
        action="store_true",
        help="MATLAB MI capture only; skip Python MI runners and tier1",
    )
    parser.add_argument(
        "--skip-tier1",
        action="store_true",
        help="After MI pkls, skip optim1full_parity_gate.py --tier1",
    )
    args = parser.parse_args()

    from tests.demo1.optim1full.optim1full_authority import assert_optim1full_mdp_ledger_session
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir, optim1full_mdp_post_nr_mat

    fixtures = optim1full_fixtures_dir()
    post_mat = optim1full_mdp_post_nr_mat()
    if not post_mat.is_file():
        print(f"[optim1full_capture_mi] missing {post_mat}", file=sys.stderr)
        return 2

    assert_optim1full_mdp_ledger_session(fixtures)

    if not args.skip_backup:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_dir = fixtures / "deprecated" / f"mi_pre_authority_recapture_{stamp}"
        n = _backup_mi_artifacts(fixtures, backup_dir)
        print(
            f"[optim1full_capture_mi] backed up {n} files -> {backup_dir}",
            file=sys.stderr,
            flush=True,
        )

    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

    t0 = time.perf_counter()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        fix = str(fixtures.resolve())
        eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix, nargout=0)
        eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
        eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        print(
            f"[optim1full_capture_mi] MATLAB capture from {post_mat}",
            file=sys.stderr,
            flush=True,
        )
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_mi_from_authority');",
            nargout=0,
        )
    finally:
        eng.quit()

    matlab_s = time.perf_counter() - t0
    print(f"[optim1full_capture_mi] MATLAB phase wall_s={matlab_s:.3f}", file=sys.stderr, flush=True)

    if args.matlab_only:
        return 0

    for rel in (
        "tests/demo1/optim1full/optim1full_run_mi382_isolated.py",
        "tests/demo1/optim1full/optim1full_run_mi429_isolated.py",
    ):
        if _run_cmd([sys.executable, str(_REPO / rel)]) != 0:
            return 1

    if args.skip_tier1:
        return 0

    return _run_cmd(
        [sys.executable, str(_REPO / "tests/demo1/optim1full/optim1full_parity_gate.py"), "--tier1"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
