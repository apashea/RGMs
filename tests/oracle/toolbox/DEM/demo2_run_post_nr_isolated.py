#!/usr/bin/env python3
"""DEMO2 lane B — materialize post–NR ``MDP`` from preamble ``ctx`` (isolated NR loop).

Loads ``fixtures/DEMAtariIII_demo2_preamble_ctx.pkl`` (or ``RGMS_DEMO2_PREAMBLE_CTX_PKL``).
Runs GDP attach + full ``active_inference_nr_loop`` at ``NR=32`` / ``NT=256``.
Writes ``fixtures/DEMAtariIII_demo2_post_nr_mdp.pkl`` (``mdp`` field).

Optional lane B VB replay for NR game **1** only (Entry **12** call **2** tag):
``RGMS_DEMO2_LANE_B_VB_REPLAY_CALL2=1`` → ``spm_MDP_VB_XXX(..., reuse_matlab_draws=True)``.

Compare with ``demo2_compare_post_nr_mdp_pkl_to_mat.py`` vs
``DEMAtariIII_demo2_MDP_pre_call3_post_nr.mat``.

See ``Atari_example.md`` § **ENTRY DEMO2 FULL ATARI** — lane B implementation order.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def _preamble_pkl() -> Path:
    raw = str(os.getenv("RGMS_DEMO2_PREAMBLE_CTX_PKL", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_demo2_preamble_ctx.pkl"


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_DEMO2_POST_NR_MDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_demo2_post_nr_mdp.pkl"


def _lane_b_replay_signoff_enabled() -> bool:
    return str(os.getenv("RGMS_DEMO2_LANE_B_REPLAY", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _lane_b_vb_replay_call2_enabled() -> bool:
    return str(os.getenv("RGMS_DEMO2_LANE_B_VB_REPLAY_CALL2", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _vb_game1_kwargs() -> dict[str, Any] | None:
    if not _lane_b_vb_replay_call2_enabled():
        return None
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_vb_oracle_flags

    return entry12_vb_oracle_flags(reuse_matlab_draws=True)


def main() -> int:
    if not _lane_b_replay_signoff_enabled():
        print(
            "[DEMO2 post-NR isolated] FAIL: lane B sign-off requires "
            "RGMS_DEMO2_LANE_B_REPLAY=1 and DEMO2B-P green (see Atari_example.md § DEMO2B). "
            "Native preamble PKL + native VB is diagnostic only — not lane B.",
            file=sys.stderr,
        )
        return 2

    from python_src_demo2.toolbox.DEM.demo2_preamble_ctx import load_demo2_preamble_ctx
    from python_src_demo2.toolbox.DEM.dem_atariiii_post12 import (
        active_inference_nr_loop,
        atari_nr_replications,
        atari_ns_concentration,
        atari_nt_game_length,
    )

    pre = _preamble_pkl()
    if not pre.is_file():
        print(
            f"[DEMO2 post-NR isolated] missing preamble PKL: {pre}\n"
            "Run DEM_AtariIII_dump_preamble.py first.",
            file=sys.stderr,
        )
        return 2

    ctx = load_demo2_preamble_ctx(path=pre)
    c_val = float(ctx["C"])
    ne = int(ctx["Ne"])
    nr = atari_nr_replications()
    nt = atari_nt_game_length()
    ns = atari_ns_concentration()
    vb_kw = _vb_game1_kwargs()

    print(
        f"[DEMO2 post-NR isolated] preamble={pre} NR={nr} NT={nt} "
        f"vb_game1_replay={vb_kw is not None}",
        file=sys.stderr,
    )

    mdp_post = active_inference_nr_loop(
        ctx["MDP"],
        ctx["GDP"],
        ne,
        c_val,
        nt=nt,
        nr=nr,
        ns=ns,
        vb_game1_kwargs=vb_kw,
    )

    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "mdp": mdp_post,
        "C": c_val,
        "Ne": ne,
        "Nm": int(ctx["Nm"]),
        "NR": nr,
        "NT": nt,
        "NS": ns,
        "source_preamble_pkl": str(pre),
        "lane_b_vb_replay_call2": vb_kw is not None,
    }
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[DEMO2 post-NR isolated] wrote {out} (Nm={len(mdp_post)})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
