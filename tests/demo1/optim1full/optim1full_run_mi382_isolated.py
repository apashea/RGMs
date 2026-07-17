#!/usr/bin/env python3
"""OPTIM1FULL — MI-382 isolated run: ``spm_RDP_MI`` on MATLAB ``MDP_pre_mi382``.

Loads ``tests/demo1/optim1/fixtures/DEMAtariIII_optim1full_MDP_pre_mi382.mat``.
Writes ``DEMAtariIII_optim1full_mi382_post.pkl``.

Compare: ``optim1full_compare_mi382_pkl_to_mat.py``. See ``OPTIM1.md`` § **11**.
"""
from __future__ import annotations

import copy
import os
import pickle
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _pre_mat() -> Path:
    raw = str(os.getenv("RGMS_OPTIM1FULL_MI382_PRE_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_mi382_mat

    return optim1full_mdp_pre_mi382_mat()


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_OPTIM1FULL_MI382_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from tests.demo1.optim1full.optim1full_paths import optim1full_mi382_post_pkl

    return optim1full_mi382_post_pkl()


def main() -> int:
    from python_src.toolbox.DEM.spm_RDP_MI import spm_RDP_MI
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat

    pre = _pre_mat()
    if not pre.is_file():
        print(
            f"[OPTIM1FULL MI-382] missing {pre}\n"
            "Run MATLAB: DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_mi_boundaries')",
            file=sys.stderr,
        )
        return 2

    print(f"[OPTIM1FULL MI-382] input {pre}", file=sys.stderr)
    mdp_in = load_mdp_from_mat(pre, "MDP_pre_mi382")
    t0 = time.perf_counter()
    mdp_out = spm_RDP_MI(copy.deepcopy(mdp_in))
    wall_s = time.perf_counter() - t0

    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                "mdp": mdp_out,
                "boundary": "optim1full_mi382",
                "source_pre_mat": str(pre),
                "wall_s": wall_s,
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[OPTIM1FULL MI-382] wrote {out} wall_s={wall_s:.6f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
