#!/usr/bin/env python3
"""OPTIM1 Entry 10 scale — sort+goals optim vs fidelity native on DEMO1 boundary.

Authority for OPTIM1: **optim ≡ fidelity** on ``MDP_pre_entry10`` with native ``eig``
(same contract as holistic ``DEM_AtariIII_optim``). Does **not** compare to
``MDP_pre_entry11`` MATLAB-eig FSL authority (see ``Atari_example.md`` Entry 10 eigen note).

Usage::

    python tests/demo1/optim1/optim1_run_entry10_scale.py
    python tests/demo1/optim1/optim1_run_entry10_scale.py --skip-write
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.optimized.toolbox.DEM.fsl_backward_entry10_optim import (
    compare_entry10_optim_to_fidelity_native,
    run_entry10_optim_from_pre_entry10_pkl,
    write_entry10_optim_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 10 scale vs fidelity native")
    p.add_argument("--pre-entry10", type=Path, default=None)
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--skip-write", action="store_true")
    args = p.parse_args(argv)

    pre10 = args.pre_entry10 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    )
    if not pre10.is_file():
        print(f"[OPTIM1 Entry 10 scale] missing {pre10}", file=sys.stderr)
        return 2

    print("[OPTIM1 Entry 10 scale] sort_optim+goals from DEMO1 pre_entry10", file=sys.stderr)
    t_wall = time.perf_counter()
    out = run_entry10_optim_from_pre_entry10_pkl(pre_entry10_pkl=pre10)
    wall_s = time.perf_counter() - t_wall
    print(
        f"[OPTIM1 Entry 10 scale] entry10_wall_s={float(out.get('entry10_wall_s', wall_s)):.3f} "
        f"wall_s={wall_s:.3f}",
        file=sys.stderr,
    )

    if not args.skip_write:
        pkl_out = write_entry10_optim_post_pkl(out)
        print(f"[OPTIM1 Entry 10 scale] wrote {pkl_out}", file=sys.stderr)

    if not args.skip_compare:
        compare_entry10_optim_to_fidelity_native(out, pre_entry10_pkl=pre10)
        print(
            "[OPTIM1 Entry 10 scale] OK: optim ≡ fidelity native on pre_entry10",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
