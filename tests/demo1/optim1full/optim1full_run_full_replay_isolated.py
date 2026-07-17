#!/usr/bin/env python3
"""OPTIM1FULL Product B — step **4** full-replay isolated runner.

See ``optim1full_parity_contract.py`` for lane discipline.

Runs ``run_dem_atariiii_optim1full_parity()`` under Model **B** phased ledger replay.
Always dumps ``ctx['MDP_post_nr']`` (NR boundary) for ``optim1full_compare_post_nr_pkl_to_mat.py``.
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
        run_dem_atariiii_optim1full_parity,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_post_nr_pkl
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        add_vb_dev_optim_cli_argument,
        apply_vb_dev_optim_cli,
        optim1full_vb_dev_optim_enabled,
    )

    p = argparse.ArgumentParser(description="OPTIM1FULL Product B full-replay isolated run")
    p.add_argument(
        "--deadline-minutes",
        default="240",
        help="sign-off wall-clock budget (optim1full_signoff_env)",
    )
    p.add_argument(
        "--stop-after-nr",
        action="store_true",
        help="omit VB calls 3/4; dump MDP_post_nr snapshot for compare (faster iteration)",
    )
    p.add_argument(
        "--plot-witness",
        action="store_true",
        help="enable W1-B inline plot asserts (sets RGMS_OPTIM1FULL_PLOT=1)",
    )
    add_vb_dev_optim_cli_argument(p)
    args = p.parse_args(argv)
    apply_vb_dev_optim_cli(args)

    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")
    if args.plot_witness:
        os.environ["RGMS_OPTIM1FULL_PLOT"] = "1"
        os.environ.setdefault("MPLBACKEND", "Agg")
        # Pre-load matplotlib before the driver starts any MATLAB Engine (Windows pyexpat).
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401

    buf, manifest = load_validated_optim1full_ledger()
    t0 = time.perf_counter()
    print(
        "[OPTIM1FULL full-replay] starting run_dem_atariiii_optim1full_parity "
        f"(K_total={manifest.k_total}, deadline_minutes={args.deadline_minutes}"
        f"{', vb_dev_optim=1' if optim1full_vb_dev_optim_enabled() else ''}"
        f"{', plot_witness=1' if args.plot_witness or os.getenv('RGMS_OPTIM1FULL_PLOT', '').strip() in ('1', 'true', 'yes') else ''})",
        file=sys.stderr,
        flush=True,
    )
    ctx = run_dem_atariiii_optim1full_parity(
        deadline_minutes=str(args.deadline_minutes),
        stop_after_nr=bool(args.stop_after_nr),
    )
    wall_s = time.perf_counter() - t0

    mdp_out = ctx.get("MDP_post_nr", ctx["MDP"])
    np_val = int(ctx.get("optim1full_np", 0))
    nm = len(mdp_out)

    out = optim1full_post_nr_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                "mdp": mdp_out,
                "nm": nm,
                "np": np_val,
                "wall_s": wall_s,
                "boundary": (
                    "optim1full_full_replay_post_nr"
                    if args.stop_after_nr
                    else "optim1full_full_replay"
                ),
                "ledger_protocol": manifest.protocol,
                "ledger_k_total": manifest.k_total,
                "optim1full_parity_lane": ctx.get("_optim1full_parity_lane"),
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(
        f"[OPTIM1FULL full-replay] wrote {out} Nm={nm} optim1full_np={np_val} wall_s={wall_s:.3f}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
