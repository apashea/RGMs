#!/usr/bin/env python3
"""OPTIM1FULL W2 — **historical diagnostic**: fidelity vs ``spm_MDP_VB_XXX_optim`` PDP.

**Not** the W2 sign-off authority after optim intentionally diverged from fidelity
scaffolding (e.g. ``entry12_Yfill`` probe, fidelity-shaped ``Q.E`` list layout).
Sign-off uses ``optim1full_vb_optim_matlab_equivalence.py`` (optim vs frozen MATLAB
``pdp_mat`` with MATLAB-layout alignment).

Phase **0:** optim module delegates to fidelity — expect **PASS** (scaffold wiring).
Phase **1+:** re-run only for regression/diagnostic; expand tag surface after MATLAB
authority ladder is green.

Default tag: tier **3a** ``rgms_atari_optim1full_call2`` (frozen RDP + ``vb_rand_buf``).

Does **not** replace tier **3a** MATLAB oracle (script **3** + audit + script **4**).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.optim1full.optim1full_vb_tag_lane import (
    _assert_pdp_equal,
    _configure_entry12_fixture_env,
    _load_tag_rdp_and_buf,
    _load_tier3a_rdp_and_buf,
    _run_vb_tag_lane,
    assert_pdp_equal,
    configure_entry12_fixture_env,
    load_tag_rdp_and_buf,
    run_vb_tag_lane,
)


def run_vb_optim_equivalence(
    tag: str,
    *,
    deadline_minutes: str = "120",
) -> dict[str, Any]:
    """Run fidelity + optim VB on frozen tag fixtures; assert PDP match."""
    os.environ.setdefault("RGMS_ATARI_RUN_DEADLINE_MINUTES", str(deadline_minutes))
    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")

    configure_entry12_fixture_env(tag)
    rdp, buf, k = load_tag_rdp_and_buf(tag)

    print(
        f"[optim1full_vb_optim_equivalence] tag={tag!r} vb_rand_buf.k={k} lane=entry12_tag",
        file=sys.stderr,
        flush=True,
    )

    t0 = time.perf_counter()
    pdp_fidelity = run_vb_tag_lane(rdp, lane="fidelity")
    t_fidelity = time.perf_counter() - t0

    t1 = time.perf_counter()
    pdp_optim = run_vb_tag_lane(rdp, lane="optim")
    t_optim = time.perf_counter() - t1

    assert_pdp_equal(pdp_fidelity, pdp_optim, label=f"W2 fidelity vs optim ({tag})")

    wall = time.perf_counter() - t0
    out = {
        "tag": tag,
        "k": k,
        "wall_s": wall,
        "fidelity_vb_s": t_fidelity,
        "optim_vb_s": t_optim,
    }
    print(
        f"[optim1full_vb_optim_equivalence] PASS tag={tag!r} "
        f"fidelity_s={t_fidelity:.3f} optim_s={t_optim:.3f} wall_s={wall:.3f}",
        file=sys.stderr,
        flush=True,
    )
    return out


def run_vb_optim_equivalence_tier3a(
    tag: str,
    *,
    deadline_minutes: str = "120",
) -> dict[str, Any]:
    """Back-compat wrapper — prefer :func:`run_vb_optim_equivalence`."""
    return run_vb_optim_equivalence(tag, deadline_minutes=deadline_minutes)


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL2_TAG,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--tag",
        default=ENTRY12_OPTIM1FULL_CALL2_TAG,
        help="Entry 12 VB tag (default: tier 3a call2)",
    )
    p.add_argument("--deadline-minutes", default="120")
    args = p.parse_args(argv)

    try:
        run_vb_optim_equivalence(
            str(args.tag).strip(),
            deadline_minutes=str(args.deadline_minutes),
        )
    except Exception as exc:
        print(f"[optim1full_vb_optim_equivalence] FAIL: {exc!r}", file=sys.stderr, flush=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
