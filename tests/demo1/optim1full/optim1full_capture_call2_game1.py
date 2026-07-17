#!/usr/bin/env python3
"""OPTIM1FULL — produce Entry 12 call-2 game-1 sign-off fixtures (``rgms_atari_call2``)."""
from __future__ import annotations

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

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _set_matlab_optim1full_fixture_env(eng)
        eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_call2_game1');",
            nargout=0,
        )
    finally:
        eng.quit()
    print("[optim1full_capture_call2_game1] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
