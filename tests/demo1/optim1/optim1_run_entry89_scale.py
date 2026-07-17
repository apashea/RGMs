#!/usr/bin/env python3
"""OPTIM1 Entry 8+9 scale run — merge+basin loop vs DEMO1 ``MDP_pre_entry10`` authority.

Reads DEMO1 ``MDP_pre_entry9`` boundary; runs optim merge + ``spm_RDP_basin_optim`` loop;
compares post-Entry-9 ``MDP`` to ``MDP_pre_entry10`` in pre_entry10 ``.mat``.

Usage (repo root)::

    python tests/demo1/optim1/optim1_run_entry89_scale.py
    python tests/demo1/optim1/optim1_run_entry89_scale.py --skip-compare
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.optimized.toolbox.DEM.fsl_backward_entry9_optim import (
    compare_entry9_optim_mdp_to_demo_authority,
    run_entry9_optim_from_pre_entry9_pkl,
    write_entry9_optim_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="OPTIM1 Entry 8+9 scale (n_outer=128) vs DEMO1 fixtures"
    )
    p.add_argument(
        "--pre-entry9",
        type=Path,
        default=None,
        help="DEMO1 pre_entry9 PKL (default: tests/demo1/fixtures/...)",
    )
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--skip-write", action="store_true")
    args = p.parse_args(argv)

    mat = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    pre9 = args.pre_entry9 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
    )
    for label, path in (("authority mat", mat), ("pre_entry9", pre9)):
        if not path.is_file():
            print(f"[OPTIM1 Entry 8+9 scale] missing {label}: {path}", file=sys.stderr)
            return 2

    print("[OPTIM1 Entry 8+9 scale] merge+basin_optim from DEMO1 pre_entry9", file=sys.stderr)
    t_wall = time.perf_counter()
    try:
        out = run_entry9_optim_from_pre_entry9_pkl(pre_entry9_pkl=pre9)
    except Exception as exc:
        print(f"[OPTIM1 Entry 8+9 scale] FAIL: {exc}", file=sys.stderr)
        raise
    wall_s = time.perf_counter() - t_wall
    e8_s = float(out.get("entry8_loop_s", 0.0))
    e9_s = float(out.get("entry9_loop_s", 0.0))
    print(
        f"[OPTIM1 Entry 8+9 scale] entry8_loop_s={e8_s:.3f} entry9_loop_s={e9_s:.3f} "
        f"wall_s={wall_s:.3f} n_outer={out.get('n_outer')}",
        file=sys.stderr,
    )

    if not args.skip_write:
        pkl_out = write_entry9_optim_post_pkl(out)
        print(f"[OPTIM1 Entry 8+9 scale] wrote {pkl_out}", file=sys.stderr)

    if not args.skip_compare:
        compare_entry9_optim_mdp_to_demo_authority(out["mdp"], authority_mat=mat)
        print(
            "[OPTIM1 Entry 8+9 scale] OK: MDP matches DEMO1 MDP_pre_entry10 authority",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
