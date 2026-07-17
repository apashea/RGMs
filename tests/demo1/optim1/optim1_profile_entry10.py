#!/usr/bin/env python3
"""OPTIM1 Entry 10 scoping — cProfile ``run_entry10_from_mdp`` on DEMO1 boundary.

Profiles the **fidelity** Entry 10 ledger (what the holistic OPTIM1 driver still uses).
Native ``eig`` path (no MATLAB Engine) — same as ``DEM_AtariIII_optim`` Entry 10.

Usage (repo root)::

    python tests/demo1/optim1/optim1_profile_entry10.py
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


def _load_pre_entry10() -> tuple[list[dict[str, Any]], float]:
    pkl = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 boundary: {pkl}")
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "mdp" not in blob:
        raise TypeError(f"expected dict with mdp in {pkl}")
    c_val = float(blob.get("C", 32.0))
    return blob["mdp"], c_val


def _profile_entry10_once(*, optim: bool) -> None:
    mdp, c_val = _load_pre_entry10()
    if optim:
        from python_src.optimized.toolbox.DEM.fsl_backward_entry10_optim import (
            run_entry10_optim_from_mdp,
        )

        run_entry10_optim_from_mdp(mdp, c_val=c_val)
    else:
        from python_src.toolbox.DEM.fsl_backward_entry10 import run_entry10_from_mdp

        run_entry10_from_mdp(mdp, c_val=c_val)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 10 cProfile")
    p.add_argument("--optim", action="store_true", help="Profile optim ledger (default: fidelity)")
    p.add_argument("--sort", default="cumtime", choices=("cumtime", "tottime"))
    p.add_argument("--top", type=int, default=40)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Report (default logs/optim1_entry10_profile.txt)",
    )
    args = p.parse_args(argv)

    out_path = args.out or (
        _REPO / "logs" / ("optim1_entry10_optimpath_profile.txt" if args.optim else "optim1_entry10_profile.txt")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lane = "optim ledger" if args.optim else "fidelity ledger"
    print(f"[OPTIM1 profile Entry 10] run_entry10 ({lane}, native eig)", file=sys.stderr)
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    _profile_entry10_once(optim=args.optim)
    pr.disable()
    wall_s = time.perf_counter() - t0

    buf = io.StringIO()
    ps = pstats.Stats(pr, stream=buf).sort_stats(args.sort)
    ps.print_stats(args.top)

    report = "\n".join(
        [
            f"OPTIM1 Entry 10 profile ({lane}, native eig)",
            f"pre_entry10={demo1_fixtures_dir() / 'DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl'}",
            f"wall_s={wall_s:.6f}",
            "",
            f"=== top {args.top} by {args.sort} ===",
            buf.getvalue(),
        ]
    )
    out_path.write_text(report, encoding="utf-8")
    print(f"[OPTIM1 profile Entry 10] wall_s={wall_s:.3f} wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
