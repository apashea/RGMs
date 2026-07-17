#!/usr/bin/env python3
"""OPTIM1 Entry 3 scale run — ``T=10000`` + compare vs DEMO1 authority fixtures.

Reads DEMO1 ``entry2_post`` GDP + ``dem_atari_rand_buf``; runs ``spm_MDP_generate_optim``;
compares ``PDP.o`` and ``PDP.O(:,1:1000)`` to ``PDP_o`` / ``PDP_O`` in pre_entry10 ``.mat``.

Usage (repo root)::

    python tests/demo1/optim1/optim1_run_entry3_scale.py
    python tests/demo1/optim1/optim1_run_entry3_scale.py --skip-compare
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.optimized.toolbox.DEM.fsl_backward_entry3_optim import (
    compare_entry3_optim_pdp_to_demo1_authority,
    run_entry3_optim_from_entry2_post_pkl,
    write_entry3_optim_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 3 scale (T=10000) vs DEMO1 fixtures")
    p.add_argument(
        "--entry2-post",
        type=Path,
        default=None,
        help="DEMO1 Entry 2 post PKL (default: tests/demo1/fixtures/...)",
    )
    p.add_argument(
        "--deadline-minutes",
        default="90",
        help="Wall deadline for DEM_AtariIII deadline checks (default 90)",
    )
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--skip-write", action="store_true")
    args = p.parse_args(argv)

    mat = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    entry2 = args.entry2_post or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry2_post.pkl"
    )
    for label, path in (("authority mat", mat), ("entry2 post", entry2)):
        if not path.is_file():
            print(f"[OPTIM1 Entry 3 scale] missing {label}: {path}", file=sys.stderr)
            return 2

    print("[OPTIM1 Entry 3 scale] T=10000 generate_optim from DEMO1 entry2_post", file=sys.stderr)
    t_wall = time.perf_counter()
    try:
        out = run_entry3_optim_from_entry2_post_pkl(
            entry2_post_pkl=entry2,
            deadline_minutes=str(args.deadline_minutes),
        )
    except Exception as exc:
        print(f"[OPTIM1 Entry 3 scale] FAIL: {exc}", file=sys.stderr)
        raise
    wall_s = time.perf_counter() - t_wall
    gen_s = float(out.get("entry3_generate_s", 0.0))
    print(
        f"[OPTIM1 Entry 3 scale] generate_s={gen_s:.3f} wall_s={wall_s:.3f} "
        f"K_3={out.get('k_3')} draws_used={out.get('draws_used')}",
        file=sys.stderr,
    )

    if not args.skip_write:
        pkl_out = write_entry3_optim_post_pkl(out)
        print(f"[OPTIM1 Entry 3 scale] wrote {pkl_out}", file=sys.stderr)

    if not args.skip_compare:
        compare_entry3_optim_pdp_to_demo1_authority(out["pdp"], authority_mat=mat)
        print(
            "[OPTIM1 Entry 3 scale] OK: PDP.o + PDP.O(:,1:1000) match DEMO1 authority",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
