#!/usr/bin/env python3
"""One-time: metadata PKL for FSL backward Entry 2 (snippet constants on ``rng(2)`` ledger).

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry2.pkl``.

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE2_PKL=1``
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
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry2.pkl"


def _mat_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE2_PKL", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 2] reuse {pkl}", file=sys.stderr)
        return 0

    mat_p = _mat_path()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing {mat_p}")

    payload = {
        "nr": 12,
        "nc": 9,
        "nd": 4,
        "na": True,
        "np_dist": 0,
        "source_mat": str(mat_p.resolve()),
        "authority_vars": (
            "GDP_post_entry2",
            "RGB_post_entry2",
            "S_post_entry2",
            "hid_post_entry2",
            "cid_post_entry2",
            "con_post_entry2",
        ),
    }
    pkl.parent.mkdir(parents=True, exist_ok=True)
    with pkl.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[FSL backward materialize Entry 2] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
