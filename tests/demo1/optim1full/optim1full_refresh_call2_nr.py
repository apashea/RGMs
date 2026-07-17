#!/usr/bin/env python3
"""OPTIM1FULL — refresh Entry **12** dumps for call-2 NR tags (no NR loop).

Use after **12F** v7.3 save fix when ``in`` was dropped from v7 mats (games **4+**).
Default refresh range: games **4–32** via ``RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM`` / ``_TO``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _set_matlab_optim1full_fixture_env(eng) -> None:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fix = str(optim1full_fixtures_dir().resolve())
    eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
    eng.setenv("RGMS_OPTIM1_FIXTURES_DIR", fix, nargout=0)


def main() -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

    if not os.environ.get("RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM"):
        os.environ["RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM"] = "4"
    if not os.environ.get("RGMS_OPTIM1FULL_CALL2_CAPTURE_TO"):
        os.environ["RGMS_OPTIM1FULL_CALL2_CAPTURE_TO"] = "32"

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _set_matlab_optim1full_fixture_env(eng)
        eng.setenv(
            "RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM",
            os.environ["RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM"],
            nargout=0,
        )
        eng.setenv(
            "RGMS_OPTIM1FULL_CALL2_CAPTURE_TO",
            os.environ["RGMS_OPTIM1FULL_CALL2_CAPTURE_TO"],
            nargout=0,
        )
        eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('refresh_optim1full_call2_nr');",
            nargout=0,
        )
    finally:
        eng.quit()
    print("[optim1full_refresh_call2_nr] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
