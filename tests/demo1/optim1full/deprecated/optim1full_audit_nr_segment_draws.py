#!/usr/bin/env python3
"""OPTIM1FULL Product B — Model B NR segment draw audit (§ ``OPTIM1.md`` **11.7.3**).

Measures ``draws_used`` vs manifest ``k`` for NR ledger segments. Sign-off instrument
for gates **G0**–**G31**; does **not** fix compute.

Modes
-----
``--game N``
    Audit NR game ``N`` VB draw count only (manifest segment ``nr_game_NN``).

    Game **1**: fidelity assembly per § **11.7.1** (``spm_set_goals`` → ``spm_set_costs`` →
    ``spm_mdp2rdp``) on ``MDP_pre_active_inference``, then one ``spm_MDP_VB_XXX``.

    Game ``N>1``: run full NR loop for games ``1..N-1`` (current
    ``active_inference_nr_loop`` path), then fidelity assembly + VB for game ``N``.

``--through N``
    Cumulative audit: replay ledger ``[nr_game_01.start, nr_game_NN.end)`` while running
    ``active_inference_nr_loop`` for ``N`` games (same path as tier **3g** lean runner).

Exit **0** iff ``draws_used == k_manifest`` for the audited slice.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _segment_id(game: int) -> str:
    if game < 1 or game > 32:
        raise ValueError(f"NR game index must be 1..32, got {game}")
    return f"nr_game_{game:02d}"


def assemble_nr_rdp_parity(
    mdp: list[dict[str, Any]],
    c_val: float,
    ne: int,
    *,
    nt: int = 256,
    ns: float = 256.0,
) -> dict[str, Any]:
    """MATLAB ``DEM_AtariIII.m`` NR assembly (§ **11.7.1**) — fidelity ``python_src`` only."""
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
    from python_src.toolbox.DEM.spm_set_goals import spm_set_goals

    rdp = spm_set_goals(mdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_mdp2rdp(rdp, 0, 1.0 / float(ns))
    rdp["T"] = float(int(nt / int(ne)))
    return rdp


def _rdp_shape_summary(rdp: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    def _scalar(x: object) -> float:
        return float(np.asarray(x, dtype=np.float64).reshape(-1)[0])

    return {
        "nA": len(rdp.get("A", [])),
        "nB": len(rdp.get("B", [])),
        "T": _scalar(rdp.get("T", 0)),
        "L": int(rdp.get("L")) if rdp.get("L") is not None else None,
        "hasMDP": "MDP" in rdp,
    }


def audit_nr_game_vb(
    game: int,
    *,
    deadline_minutes: str = "120",
) -> dict[str, Any]:
    """Audit single NR game VB segment (gate **G0** when ``game==1``)."""
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
        ATARI_NS_DEFAULT,
        ATARI_NT_DEFAULT,
        active_inference_nr_loop,
    )
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import _dem_atari_ledger_hooks
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        optim1full_replay_matlab_draws,
    )
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.demo1.optim1full.optim1full_signoff_env import (
        OPTIM1FULL_CANONICAL_NR,
        optim1full_signoff_env,
    )

    seg_id = _segment_id(game)
    pre_mat = optim1full_mdp_pre_active_inference_mat()
    if not pre_mat.is_file():
        raise FileNotFoundError(f"missing pre-NR authority: {pre_mat}")

    buf, manifest = load_validated_optim1full_ledger()
    seg = manifest.segment(seg_id)
    c_val = atari_c_value()
    hooks = _dem_atari_ledger_hooks()

    with optim1full_signoff_env(deadline_minutes=deadline_minutes):
        mdp_in = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
        ne = load_ne_from_mat(pre_mat, "Ne")

        if game > 1:
            prior = manifest.segment(_segment_id(game - 1))
            k_prior = prior.end - manifest.segment("nr_game_01").start
            with optim1full_replay_matlab_draws(
                buf, start_index=manifest.segment("nr_game_01").start, k_use=k_prior
            ):
                mdp_in = active_inference_nr_loop(
                    mdp_in,
                    None,
                    ne,
                    c_val,
                    nt=ATARI_NT_DEFAULT,
                    nr=game - 1,
                    ns=ATARI_NS_DEFAULT,
                    hooks=hooks,
                )

        rdp = assemble_nr_rdp_parity(
            mdp_in, c_val, ne, nt=ATARI_NT_DEFAULT, ns=ATARI_NS_DEFAULT
        )
        shape = _rdp_shape_summary(rdp)

        with optim1full_replay_matlab_draws(
            buf, start_index=seg.start, k_use=seg.k
        ) as ctr:
            vb_complete = True
            vb_error: str | None = None
            try:
                spm_MDP_VB_XXX(rdp)
            except RuntimeError as exc:
                vb_complete = False
                vb_error = str(exc)
        draws_used = int(ctr[0])

    gate = "G0" if game == 1 else f"G_game_{game:02d}"
    passed = vb_complete and draws_used == int(seg.k)
    out: dict[str, Any] = {
        "gate": gate,
        "mode": "game",
        "game": game,
        "segment_id": seg_id,
        "k_manifest": int(seg.k),
        "draws_used": draws_used,
        "vb_complete": vb_complete,
        "pass": passed,
        "assembly": "parity_fidelity",
        "rdp": shape,
        "nr_signoff": OPTIM1FULL_CANONICAL_NR,
    }
    if vb_error is not None:
        out["vb_error"] = vb_error
    return out


def audit_nr_through(
    through: int,
    *,
    deadline_minutes: str = "180",
) -> dict[str, Any]:
    """Cumulative NR audit through game ``through`` (gate **G31** when ``through==32``)."""
    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
        ATARI_NS_DEFAULT,
        ATARI_NT_DEFAULT,
        active_inference_nr_loop,
    )
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import _dem_atari_ledger_hooks
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        optim1full_replay_matlab_draws,
    )
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env

    if through < 1 or through > 32:
        raise ValueError(f"--through must be 1..32, got {through}")

    pre_mat = optim1full_mdp_pre_active_inference_mat()
    if not pre_mat.is_file():
        raise FileNotFoundError(f"missing pre-NR authority: {pre_mat}")

    buf, manifest = load_validated_optim1full_ledger()
    first = manifest.segment("nr_game_01")
    last = manifest.segment(_segment_id(through))
    k_manifest = int(last.end - first.start)
    c_val = atari_c_value()
    hooks = _dem_atari_ledger_hooks()

    with optim1full_signoff_env(deadline_minutes=deadline_minutes):
        mdp_in = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
        ne = load_ne_from_mat(pre_mat, "Ne")
        with optim1full_replay_matlab_draws(
            buf, start_index=first.start, k_use=k_manifest
        ) as ctr:
            loop_complete = True
            loop_error: str | None = None
            try:
                active_inference_nr_loop(
                    mdp_in,
                    None,
                    ne,
                    c_val,
                    nt=ATARI_NT_DEFAULT,
                    nr=through,
                    ns=ATARI_NS_DEFAULT,
                    hooks=hooks,
                )
            except RuntimeError as exc:
                loop_complete = False
                loop_error = str(exc)
        draws_used = int(ctr[0])

    gate = "G31" if through == 32 else f"G_through_{through:02d}"
    passed = loop_complete and draws_used == k_manifest
    out: dict[str, Any] = {
        "gate": gate,
        "mode": "through",
        "through": through,
        "segment_id": f"nr_game_01..{_segment_id(through)}",
        "k_manifest": k_manifest,
        "draws_used": draws_used,
        "loop_complete": loop_complete,
        "pass": passed,
        "assembly": "active_inference_nr_loop_current",
    }
    if loop_error is not None:
        out["loop_error"] = loop_error
    return out


def _print_report(report: dict[str, Any], *, wall_s: float) -> None:
    line = (
        f"[optim1full_audit_nr_segment_draws] gate={report['gate']} "
        f"segment_id={report['segment_id']} k_manifest={report['k_manifest']} "
        f"draws_used={report['draws_used']} vb_complete={str(report.get('vb_complete', True)).lower()} "
        f"pass={str(report['pass']).lower()} "
        f"wall_s={wall_s:.3f}"
    )
    if "rdp" in report:
        r = report["rdp"]
        line += f" nA={r['nA']} nB={r['nB']} T={r['T']}"
    print(line, file=sys.stderr, flush=True)
    print(json.dumps(report, sort_keys=True), flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1FULL Model B NR segment draw audit")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--game", type=int, metavar="N", help="audit NR game N VB segment (G0 when N=1)")
    g.add_argument(
        "--through",
        type=int,
        metavar="N",
        help="cumulative audit through NR game N (G31 when N=32)",
    )
    p.add_argument("--deadline-minutes", default="120")
    args = p.parse_args(argv)

    t0 = time.perf_counter()
    if args.game is not None:
        report = audit_nr_game_vb(int(args.game), deadline_minutes=str(args.deadline_minutes))
    else:
        report = audit_nr_through(int(args.through), deadline_minutes=str(args.deadline_minutes))

    _print_report(report, wall_s=time.perf_counter() - t0)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
