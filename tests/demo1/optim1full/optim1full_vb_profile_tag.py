#!/usr/bin/env python3
"""W2 — cProfile one VB run on frozen Entry 12 tag fixtures (call3/call4 focus).

Usage::

    python tests/demo1/optim1full/optim1full_vb_profile_tag.py \\
        --tag rgms_atari_optim1full_call3 --lane fidelity --top 40
    python tests/demo1/optim1full/optim1full_vb_profile_tag.py \\
        --tag rgms_atari_optim1full_call4 --lane optim --top 40
"""
from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL3_TAG,
    )
    from tests.demo1.optim1full.optim1full_vb_optim_equivalence import (
        _configure_entry12_fixture_env,
        _load_tag_rdp_and_buf,
        _run_vb_tag_lane,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", default=ENTRY12_OPTIM1FULL_CALL3_TAG)
    p.add_argument("--lane", choices=("fidelity", "optim"), default="fidelity")
    p.add_argument("--top", type=int, default=35)
    p.add_argument("--sort", default="cumtime")
    args = p.parse_args(argv)

    tag = str(args.tag).strip()
    _configure_entry12_fixture_env(tag)
    rdp, _buf, k = _load_tag_rdp_and_buf(tag)
    print(f"[optim1full_vb_profile_tag] tag={tag!r} lane={args.lane!r} k={k}", file=sys.stderr, flush=True)

    prof = cProfile.Profile()
    prof.enable()
    _run_vb_tag_lane(rdp, lane=str(args.lane))
    prof.disable()

    stream = io.StringIO()
    ps = pstats.Stats(prof, stream=stream)
    ps.strip_dirs()
    ps.sort_stats(str(args.sort))
    ps.print_stats(int(args.top))
    print(stream.getvalue(), file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
