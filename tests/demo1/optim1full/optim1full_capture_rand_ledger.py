#!/usr/bin/env python3
"""OPTIM1FULL — one-shot MATLAB ``capture_optim1full_rand_ledger`` (Model B, § **11.7.2**).

With ``--nr-authority-trace`` the same single ``rng(2)`` session additionally dumps the
per-game NR authority (VB input ``RDP``, MATLAB VB output ``PDP``, post-merge/basin
``MDP_post_game``) for all 32 games into ``fixtures/optim1full_nr_authority/`` — see
``OPTIM1FULL.md`` § "Per-game NR authority trace". Default behavior is unchanged.
"""
from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--nr-authority-trace",
        action="store_true",
        help=(
            "Also dump per-game NR authority (RDP/PDP/MDP_post_game x32) into "
            "fixtures/optim1full_nr_authority/ (OPTIM1FULL.md § Per-game NR authority trace)"
        ),
    )
    p.add_argument(
        "--plot-fence-trace",
        action="store_true",
        help=(
            "Also dump MATLAB-owned plot-fence authority in-flow: PDP fences "
            "(gameplay + 4 RGB) as DEMAtariIII_optim1full_<site>_matlab_pdp.mat, and "
            "payload fences (attractors basin NS…NH, post-sort b1/hid, structure-learning F) "
            "as DEMAtariIII_optim1full_<site>_matlab_payload.mat "
            "(OPTIM1FULL.md § Genuine plot-fn parity wiring)"
        ),
    )
    args = p.parse_args(argv)

    print(
        "[optim1full_capture_rand_ledger] Model B — one rng(2) scalar ledger capture "
        f"(do not run concurrently with gates); nr_authority_trace={bool(args.nr_authority_trace)} "
        f"plot_fence_trace={bool(args.plot_fence_trace)}",
        file=sys.stderr,
        flush=True,
    )
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _set_matlab_optim1full_fixture_env(eng)
        # Env-gated per-game NR authority trace (read by the MATLAB ledger loop).
        eng.setenv(
            "RGMS_OPTIM1FULL_NR_AUTHORITY_TRACE",
            "1" if args.nr_authority_trace else "0",
            nargout=0,
        )
        # Env-gated plot-fence authority trace (read by the MATLAB ledger capture mode).
        eng.setenv(
            "RGMS_OPTIM1FULL_PLOT_FENCE_TRACE",
            "1" if args.plot_fence_trace else "0",
            nargout=0,
        )
        eng.cd(str(_REPO), nargout=0)
        eng.addpath(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_rand_ledger');",
            nargout=0,
        )
    finally:
        eng.quit()
    print("[optim1full_capture_rand_ledger] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
