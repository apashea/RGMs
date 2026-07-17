#!/usr/bin/env python3
"""OPTIM1FULL — rewrite Entry **12** ``*_in.mat`` sidecars to lean v7 (script **4** load path).

Does **not** edit shared ``spm_MDP_VB_XXX_entry12_dump.m``. Calls
``optim1full_entry12_rewrite_in_sidecars_for_tag`` in ``matlab_custom/demo1/optim1full_entry12_rewrite_in_sidecars_for_tag.m``.

Use after ``optim1full_capture_entry12_from_authority.py`` phase **2**, or standalone
on existing fixtures when only sidecar ingest is broken.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_TAGS = (
    "rgms_atari_optim1full_call2",
    "rgms_atari_optim1full_call3",
    "rgms_atari_optim1full_call4",
)


def _rewrite_tags(eng, tags: tuple[str, ...], fixtures: Path) -> None:
    fix_posix = str(fixtures.resolve()).replace("\\", "/")
    eng.addpath(str(_REPO / "matlab_custom" / "demo1"), nargout=0)
    for tag in tags:
        print(f"[optim1full_rewrite_entry12_lean_sidecars] tag={tag!r}", file=sys.stderr, flush=True)
        eng.optim1full_entry12_rewrite_in_sidecars_for_tag(tag, fix_posix, nargout=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="Entry 12 run tag (repeatable; default: call2/3/4 optim1full tags)",
    )
    args = parser.parse_args()
    tags = tuple(args.tags) if args.tags else _DEFAULT_TAGS

    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fixtures = optim1full_fixtures_dir()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _rewrite_tags(eng, tags, fixtures)
    finally:
        eng.quit()

    print("[optim1full_rewrite_entry12_lean_sidecars] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
