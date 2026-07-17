#!/usr/bin/env python3
"""OPTIM1 Entry 4 scale — structure learning optim vs fidelity native on DEMO1 boundary.

Reads DEMO1 ``MDP_pre_entry4``; runs ``spm_faster_structure_learning_optim``;
compares post-Entry-4 ``MDP`` to fidelity native on the same boundary (holistic contract).

Usage (repo root)::

    python tests/demo1/optim1/optim1_run_entry4_scale.py
    python tests/demo1/optim1/optim1_run_entry4_scale.py --skip-write
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.optimized.toolbox.DEM.fsl_backward_entry4_optim import (
    compare_entry4_optim_to_fidelity_native,
    run_entry4_optim_from_pre_entry4_pkl,
    write_entry4_optim_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 4 scale vs fidelity native")
    p.add_argument("--pre-entry4", type=Path, default=None)
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--skip-write", action="store_true")
    args = p.parse_args(argv)

    pre4 = args.pre_entry4 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"
    )
    if not pre4.is_file():
        print(f"[OPTIM1 Entry 4 scale] missing pre_entry4: {pre4}", file=sys.stderr)
        return 2

    print("[OPTIM1 Entry 4 scale] structure_optim from DEMO1 pre_entry4", file=sys.stderr)
    t_wall = time.perf_counter()
    try:
        out = run_entry4_optim_from_pre_entry4_pkl(pre_entry4_pkl=pre4)
    except Exception as exc:
        print(f"[OPTIM1 Entry 4 scale] FAIL: {exc}", file=sys.stderr)
        raise
    wall_s = time.perf_counter() - t_wall
    loop_s = float(out.get("entry4_loop_s", 0.0))
    print(
        f"[OPTIM1 Entry 4 scale] entry4_loop_s={loop_s:.3f} wall_s={wall_s:.3f} "
        f"Nm={out.get('Nm')}",
        file=sys.stderr,
    )

    if not args.skip_write:
        pkl_out = write_entry4_optim_post_pkl(out)
        print(f"[OPTIM1 Entry 4 scale] wrote {pkl_out}", file=sys.stderr)

    if not args.skip_compare:
        compare_entry4_optim_to_fidelity_native(out, pre_entry4_pkl=pre4)
        print(
            "[OPTIM1 Entry 4 scale] OK: optim ≡ fidelity native on pre_entry4",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
