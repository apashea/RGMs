#!/usr/bin/env python3
"""OPTIM1 Entry 7 scale run — hit/miss assimilations vs DEMO1 ``MDP_pre_entry9`` authority.

Reads DEMO1 ``MDP_pre_entry7`` boundary; runs ``spm_merge_structure_learning_optim`` loop;
compares post-Entry-7 ``MDP`` to ``MDP_pre_entry9`` in pre_entry10 ``.mat``.

Usage (repo root)::

    python tests/demo1/optim1/optim1_run_entry7_scale.py
    python tests/demo1/optim1/optim1_run_entry7_scale.py --skip-write
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.optimized.toolbox.DEM.fsl_backward_entry7_optim import (
    compare_entry7_optim_mdp_to_demo_authority,
    run_entry7_optim_from_pre_entry7_pkl,
    write_entry7_optim_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 7 scale vs DEMO1 fixtures")
    p.add_argument("--pre-entry7", type=Path, default=None)
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--skip-write", action="store_true")
    args = p.parse_args(argv)

    mat = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    pre7 = args.pre_entry7 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl"
    )
    for label, path in (("authority mat", mat), ("pre_entry7", pre7)):
        if not path.is_file():
            print(f"[OPTIM1 Entry 7 scale] missing {label}: {path}", file=sys.stderr)
            return 2

    print("[OPTIM1 Entry 7 scale] merge_optim hit/miss from DEMO1 pre_entry7", file=sys.stderr)
    t_wall = time.perf_counter()
    try:
        out = run_entry7_optim_from_pre_entry7_pkl(pre_entry7_pkl=pre7)
    except Exception as exc:
        print(f"[OPTIM1 Entry 7 scale] FAIL: {exc}", file=sys.stderr)
        raise
    wall_s = time.perf_counter() - t_wall
    loop_s = float(out.get("entry7_loop_s", 0.0))
    print(
        f"[OPTIM1 Entry 7 scale] entry7_loop_s={loop_s:.3f} wall_s={wall_s:.3f} "
        f"n_windows={out.get('n_windows')}",
        file=sys.stderr,
    )

    if not args.skip_write:
        pkl_out = write_entry7_optim_post_pkl(out)
        print(f"[OPTIM1 Entry 7 scale] wrote {pkl_out}", file=sys.stderr)

    if not args.skip_compare:
        compare_entry7_optim_mdp_to_demo_authority(out["mdp"], authority_mat=mat)
        print(
            "[OPTIM1 Entry 7 scale] OK: MDP matches DEMO1 MDP_pre_entry9 authority",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
