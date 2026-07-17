#!/usr/bin/env python3
"""OPTIM1FULL Product B — call-3 RDP assembly from ``MDP_post_nr`` (Engine ``spm_RDP_sort``).

Loads ``DEMAtariIII_optim1full_MDP_post_nr.mat``; runs Engine ``spm_RDP_sort`` then Python
goals / costs / ``spm_mdp2rdp`` (``RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1`` default).
Compare: ``optim1full_compare_call3_rdp_pkl_to_mat.py``.
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
    import matlab.engine

    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import atari_ns_concentration
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call3_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
        validation_sort_metadata,
    )
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.demo1.optim1full.optim1full_paths import optim1full_call3_rdp_pkl, optim1full_mdp_post_nr_mat

    if not optim1full_matlab_sort_enabled():
        print(
            "[OPTIM1FULL call3 asm] RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=0 — "
            "not Product B sign-off",
            file=sys.stderr,
        )
        return 2

    pre = optim1full_mdp_post_nr_mat()
    if not pre.is_file():
        print(f"[OPTIM1FULL call3 asm] missing {pre}", file=sys.stderr)
        return 2

    print(f"[OPTIM1FULL call3 asm] input {pre}", file=sys.stderr)
    mdp = load_mdp_from_mat(pre, "MDP_post_nr")
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        c_val = atari_c_value()
        ns = atari_ns_concentration()
        t0 = time.perf_counter()
        rdp = assemble_rdp_call3_post_nr_optim1full_parity(
            eng,
            mdp,
            c_val,
            ns,
            mat_path=pre,
            mat_var="MDP_post_nr",
        )
        wall_s = time.perf_counter() - t0
    finally:
        eng.quit()

    out = optim1full_call3_rdp_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                "rdp": rdp,
                "source_mat": str(pre.resolve()),
                "c_val": c_val,
                "ns": ns,
                "wall_s": wall_s,
                "boundary": "optim1full_call3_assembly",
                "validation": validation_sort_metadata(),
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[OPTIM1FULL call3 asm] wrote {out} wall_s={wall_s:.3f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
