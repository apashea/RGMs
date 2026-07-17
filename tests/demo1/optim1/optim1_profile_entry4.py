#!/usr/bin/env python3
"""OPTIM1 Entry 4 scoping — cProfile Entry 4 ledger on DEMO1 boundary.

Entry **4** runs ``spm_faster_structure_learning`` on ``PDP.O(:,1:1000)``.
Default: fidelity ledger. ``--optim`` profiles ``run_entry4_optim_from_boundary``.

Usage (repo root)::

    conda activate rgms
    python tests/demo1/optim1/optim1_profile_entry4.py
    python tests/demo1/optim1/optim1_profile_entry4.py --optim
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


def _profile_entry4_once(boundary: dict[str, Any], *, optim: bool) -> dict[str, float]:
    if optim:
        from python_src.optimized.toolbox.DEM.fsl_backward_entry4_optim import (
            run_entry4_optim_from_boundary,
        )

        runner = run_entry4_optim_from_boundary
    else:
        from python_src.toolbox.DEM.fsl_backward_entry4 import run_entry4_from_boundary

        runner = run_entry4_from_boundary

    t0 = time.perf_counter()
    out = runner(boundary)
    wall_s = time.perf_counter() - t0
    return {
        "wall_s": wall_s,
        "nm": float(out.get("Nm", 0)),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 4 cProfile")
    p.add_argument("--pre-entry4", type=Path, default=None)
    p.add_argument("--optim", action="store_true", help="Profile optim ledger")
    p.add_argument("--sort", default="cumtime", choices=("cumtime", "tottime"))
    p.add_argument("--top", type=int, default=40)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Report path (default: logs/optim1_entry4_profile_<lane>.txt)",
    )
    args = p.parse_args(argv)

    pre4 = args.pre_entry4 or (demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl")
    if not pre4.is_file():
        print(f"[OPTIM1 profile Entry 4] missing {pre4}", file=sys.stderr)
        return 2

    with pre4.open("rb") as f:
        boundary = pickle.load(f)

    lane = "optim" if args.optim else "fidelity"
    out_path = args.out or (_REPO / "logs" / f"optim1_entry4_profile_{lane}.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[OPTIM1 profile Entry 4] run_entry4 ({lane})", file=sys.stderr)
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    stats = _profile_entry4_once(boundary, optim=args.optim)
    pr.disable()
    elapsed = time.perf_counter() - t0

    buf = io.StringIO()
    pstats.Stats(pr, stream=buf).sort_stats(args.sort).print_stats(args.top)

    o_cols = boundary.get("entry4_o_cols", 1000)
    report = "\n".join(
        [
            f"OPTIM1 Entry 4 {lane} profile report",
            f"pre_entry4={pre4}",
            f"entry4_o_cols={o_cols} Nm={int(stats['nm'])}",
            "",
            f"=== run_entry4 wall_s={elapsed:.6f} (top {args.top} by {args.sort}) ===",
            buf.getvalue(),
            "=== summary ===",
            f"entry4_wall_s={elapsed:.6f}",
            f"Nm={int(stats['nm'])}",
        ]
    )
    out_path.write_text(report, encoding="utf-8")
    print(f"[OPTIM1 profile Entry 4] wrote {out_path}", file=sys.stderr)
    print(f"entry4_wall_s={elapsed:.6f} Nm={int(stats['nm'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
