#!/usr/bin/env python3
"""OPTIM1 Entry 7 scoping — cProfile Entry 7 ledger on DEMO1 boundary.

Entry **7** assimilates hit/miss windows via repeated ``spm_merge_structure_learning``.
Default: fidelity ledger. ``--optim`` profiles ``run_entry7_optim_from_boundary``.

Usage (repo root)::

    conda activate rgms
    python tests/demo1/optim1/optim1_profile_entry7.py
    python tests/demo1/optim1/optim1_profile_entry7.py --optim
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pickle
import pstats
import sys
import time
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _load_pre_entry7() -> dict[str, Any]:
    pkl = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl"
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 boundary: {pkl}")
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {pkl}")
    return blob


def _profile_entry7_once(boundary: dict[str, Any], *, optim: bool) -> dict[str, float]:
    if optim:
        from python_src.optimized.toolbox.DEM.fsl_backward_entry7_optim import (
            run_entry7_optim_from_boundary,
        )

        runner = run_entry7_optim_from_boundary
    else:
        from python_src.toolbox.DEM.fsl_backward_entry7 import run_entry7_from_boundary

        runner = run_entry7_from_boundary

    t0 = time.perf_counter()
    out = runner(boundary)
    wall_s = time.perf_counter() - t0
    return {
        "wall_s": wall_s,
        "n_windows": float(out.get("n_windows", 0)),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 7 fidelity cProfile")
    p.add_argument("--pre-entry7", type=Path, default=None)
    p.add_argument("--optim", action="store_true", help="Profile optim ledger")
    p.add_argument("--sort", default="cumtime", choices=("cumtime", "tottime"))
    p.add_argument("--top", type=int, default=40)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Report path (default: logs/optim1_entry7_profile.txt)",
    )
    args = p.parse_args(argv)

    pre7 = args.pre_entry7 or (demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl")
    if not pre7.is_file():
        print(f"[OPTIM1 profile Entry 7] missing {pre7}", file=sys.stderr)
        return 2

    with pre7.open("rb") as f:
        boundary = pickle.load(f)

    lane = "optim" if args.optim else "fidelity"
    out_path = args.out or (_REPO / "logs" / f"optim1_entry7_profile_{lane}.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[OPTIM1 profile Entry 7] run_entry7 ({lane})", file=sys.stderr)
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    stats = _profile_entry7_once(boundary, optim=args.optim)
    pr.disable()
    elapsed = time.perf_counter() - t0

    buf = io.StringIO()
    pstats.Stats(pr, stream=buf).sort_stats(args.sort).print_stats(args.top)

    ne = boundary.get("Ne")
    report = "\n".join(
        [
            f"OPTIM1 Entry 7 {lane} profile report",
            f"pre_entry7={pre7}",
            f"Ne={ne} n_windows={int(stats['n_windows'])}",
            "",
            f"=== run_entry7_from_boundary wall_s={elapsed:.6f} (top {args.top} by {args.sort}) ===",
            buf.getvalue(),
            "=== summary ===",
            f"entry7_wall_s={elapsed:.6f}",
            f"n_windows={int(stats['n_windows'])}",
        ]
    )
    out_path.write_text(report, encoding="utf-8")
    print(f"[OPTIM1 profile Entry 7] wrote {out_path}", file=sys.stderr)
    print(f"entry7_wall_s={elapsed:.6f} n_windows={int(stats['n_windows'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
