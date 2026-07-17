#!/usr/bin/env python3
"""OPTIM1FULL Product B — tier **3g**: post–NR ``MDP`` rebuild (lean ledger slice).

Loads ``DEMAtariIII_optim1full_MDP_pre_active_inference.mat``, replays the Model **B**
ledger from ``nr_game_01`` through ``nr_game_32`` only, runs the NR loop (``NR=32``),
then writes ``DEMAtariIII_optim1full_post_nr.pkl`` for compare.
"""
from __future__ import annotations

import pickle
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import _dem_atari_ledger_hooks
    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
        ATARI_NR_DEFAULT,
        ATARI_NS_DEFAULT,
        ATARI_NT_DEFAULT,
        active_inference_nr_loop,
        atari_nr_replications,
    )
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mdp_pre_active_inference_mat,
        optim1full_post_nr_pkl,
    )
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        optim1full_vb_kwargs_provider_for_ledger_nr_loop,
    )
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.demo1.optim1full.optim1full_signoff_env import (
        OPTIM1FULL_CANONICAL_NR,
        optim1full_signoff_env,
    )

    pre_mat = optim1full_mdp_pre_active_inference_mat()
    if not pre_mat.is_file():
        raise FileNotFoundError(
            f"missing pre-NR authority: {pre_mat} — run capture_optim1full_rand_ledger "
            "(or capture_optim1full_parity) first"
        )

    buf, manifest = load_validated_optim1full_ledger()
    nr_first = manifest.segment("nr_game_01")
    nr_last = manifest.segment("nr_game_32")
    k_nr = nr_last.end - nr_first.start

    t0 = time.perf_counter()
    c_val = atari_c_value()
    hooks = _dem_atari_ledger_hooks()

    with optim1full_signoff_env(deadline_minutes="180"):
        if atari_nr_replications() != OPTIM1FULL_CANONICAL_NR:
            raise RuntimeError(
                f"sign-off env failed: NR={atari_nr_replications()} expected {OPTIM1FULL_CANONICAL_NR}"
            )
        mdp_in = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
        ne = load_ne_from_mat(pre_mat, "Ne")
        print(
            f"[OPTIM1FULL post-NR] ledger NR reuse: games 1..{OPTIM1FULL_CANONICAL_NR} "
            f"segment k={nr_first.k} each (reuse_matlab_draws lane)",
            file=sys.stderr,
            flush=True,
        )
        mdp_out = active_inference_nr_loop(
            mdp_in,
            None,
            ne,
            c_val,
            nt=ATARI_NT_DEFAULT,
            nr=ATARI_NR_DEFAULT,
            ns=ATARI_NS_DEFAULT,
            hooks=hooks,
            fidelity_nr_assembly=True,
            vb_kwargs_for_game=optim1full_vb_kwargs_provider_for_ledger_nr_loop(buf, manifest),
        )

    wall_s = time.perf_counter() - t0

    out = optim1full_post_nr_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                "mdp": mdp_out,
                "nm": len(mdp_out),
                "wall_s": wall_s,
                "boundary": "optim1full_post_nr",
                "ledger_protocol": manifest.protocol,
                "ledger_start": nr_first.start,
                "k_nr": k_nr,
                "pre_nr_mat": str(pre_mat.resolve()),
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[OPTIM1FULL post-NR] wrote {out} Nm={len(mdp_out)} wall_s={wall_s:.3f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
