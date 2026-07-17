#!/usr/bin/env python3
"""OPTIM1FULL Product B — Entries **1–11** isolated run (pairing audit, pre-**4a**).

Runs ``run_optim1full_optim1_through_mdp_pre`` on Model **B** ledger (Entries **1–11** +
``vb_call1`` + GDP attach). Compare via ``optim1full_compare_mdp_pre_pkl_to_mat.py`` or
``optim1full_parity_gate.py --pairing-audit``.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim1full_parity import (
        run_optim1full_optim1_through_mdp_pre,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_pkl
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env

    p = argparse.ArgumentParser(description="OPTIM1FULL OPTIM1 segment isolated run (diagnostic)")
    p.add_argument("--deadline-minutes", default="120")
    p.add_argument(
        "--stop-after",
        choices=("entries_11", "vb_call1", "mdp_pre"),
        default="mdp_pre",
        help="stop after entries_1_11, vb_call1, or full MDP_pre (default)",
    )
    args = p.parse_args(argv)

    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")

    buf, manifest = load_validated_optim1full_ledger()
    seg11 = manifest.segment("entries_1_11")
    print(
        f"[OPTIM1FULL optim1_segment] start stop_after={args.stop_after} "
        f"entries_1_11.k={seg11.k} deadline_minutes={args.deadline_minutes}",
        file=sys.stderr,
        flush=True,
    )
    t0 = time.perf_counter()
    with optim1full_signoff_env(deadline_minutes=str(args.deadline_minutes)):
        ctx = run_optim1full_optim1_through_mdp_pre(
            buf,
            manifest,
            deadline_minutes=str(args.deadline_minutes),
            stop_after=str(args.stop_after),
        )
    wall_s = time.perf_counter() - t0

    mdp_out = ctx.get("MDP_pre_active_inference", ctx["MDP"])
    nm = len(mdp_out)
    ne = int(ctx.get("Ne", 0))

    out = optim1full_mdp_pre_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                "mdp": mdp_out,
                "nm": nm,
                "ne": ne,
                "wall_s": wall_s,
                "boundary": f"optim1full_mdp_pre_{args.stop_after}",
                "ledger_protocol": manifest.protocol,
                "stop_after": args.stop_after,
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(
        f"[OPTIM1FULL optim1_segment] wrote {out} Nm={nm} Ne={ne} "
        f"stop_after={args.stop_after} wall_s={wall_s:.3f}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
