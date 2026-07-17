#!/usr/bin/env python3
"""OPTIM1 Entry 10 scale — MATLAB ``eig`` + optim vs DEMO1 ``MDP_pre_entry11`` authority.

**Framework parity gate (Tier 2):** same FSL contract as DEMO1 Product B
(``fsl_backward_run_entry10_isolated.py`` + ``fsl_backward_compare_entry10_pkl_to_mat.py``)
but uses ``spm_RDP_sort_optim`` + ``spm_set_goals_optim``.

Injects Engine ``eig(B,'nobalance')`` into ``spm_RDP_sort_optim``; compares post-Entry-10
``MDP`` to ``DEMAtariIII_fsl_backward_MDP_pre_entry11.mat``.

Usage::

    python tests/demo1/optim1/optim1_run_entry10_matlab_eig_scale.py
    python tests/demo1/optim1/optim1_run_entry10_matlab_eig_scale.py --skip-write
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.optimized.toolbox.DEM.fsl_backward_entry10_optim import (
    compare_entry10_optim_mdp_to_demo_matlab_authority,
    run_entry10_optim_from_pre_entry10_pkl,
    write_entry10_optim_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="OPTIM1 Entry 10 MATLAB-eig scale vs MDP_pre_entry11 authority"
    )
    p.add_argument("--pre-entry10", type=Path, default=None)
    p.add_argument(
        "--authority-mat",
        type=Path,
        default=None,
        help="default: DEMO1 MDP_pre_entry11.mat",
    )
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument("--skip-write", action="store_true")
    args = p.parse_args(argv)

    pre10 = args.pre_entry10 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    )
    mat11 = args.authority_mat or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat"
    )
    for label, path in (
        ("pre_entry10", pre10),
        ("MDP_pre_entry11 authority", mat11),
    ):
        if not path.is_file():
            print(f"[OPTIM1 Entry 10 MATLAB-eig scale] missing {label}: {path}", file=sys.stderr)
            return 2

    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig

    print(
        "[OPTIM1 Entry 10 MATLAB-eig scale] sort_optim+goals with Engine eig(B,'nobalance')",
        file=sys.stderr,
    )
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        eig_fn = _make_matlab_spm_RDP_sort_eig(eng)
        t_wall = time.perf_counter()
        out = run_entry10_optim_from_pre_entry10_pkl(pre_entry10_pkl=pre10, eig=eig_fn)
        wall_s = time.perf_counter() - t_wall
    finally:
        eng.quit()

    out = {
        **out,
        "validation_lane": "optim1_entry10_matlab_eig",
        "entry10_wall_s": float(out.get("entry10_wall_s", wall_s)),
    }
    print(
        f"[OPTIM1 Entry 10 MATLAB-eig scale] entry10_wall_s={out['entry10_wall_s']:.3f} "
        f"wall_s={wall_s:.3f}",
        file=sys.stderr,
    )

    if not args.skip_write:
        pkl_out = write_entry10_optim_post_pkl(out, eig_source="matlab_engine")
        print(f"[OPTIM1 Entry 10 MATLAB-eig scale] wrote {pkl_out}", file=sys.stderr)

    if not args.skip_compare:
        compare_entry10_optim_mdp_to_demo_matlab_authority(out["mdp"], authority_mat=mat11)
        print(
            "[OPTIM1 Entry 10 MATLAB-eig scale] OK: optim MDP matches DEMO1 MDP_pre_entry11",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
