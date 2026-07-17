#!/usr/bin/env python3
"""One-time: metadata PKL for FSL backward Entry 3 (MATLAB ``GDP`` on ``rng(2)`` ledger).

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry3.pkl`` with training horizon and
authority ``.mat`` path. Sign-off uses Engine MATLAB generate (see ``fsl_backward_run_entry3_isolated.py``).

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE3_PKL=1``
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _pkl_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry3.pkl"


def _mat_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE3_PKL", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 3] reuse {pkl}", file=sys.stderr)
        return 0

    from python_src.toolbox.DEM.dem_atariiii_entry3 import ATARI_TRAINING_T_LEDGER

    mat_p = _mat_path()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing {mat_p}")

    payload = {
        "training_t": ATARI_TRAINING_T_LEDGER,
        "tau": 1.0,
        "source_mat": str(mat_p.resolve()),
        "authority_vars": ("PDP_o", "PDP_O"),
    }
    pkl.parent.mkdir(parents=True, exist_ok=True)
    with pkl.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[FSL backward materialize Entry 3] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
