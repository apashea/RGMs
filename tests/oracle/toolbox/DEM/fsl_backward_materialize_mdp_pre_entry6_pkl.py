#!/usr/bin/env python3
"""One-time: MATLAB ``.mat`` → PKL for FSL backward Entry 6 input.

Reads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (``PDP_o``, ``GDP_id_*``, ``Ne``).

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry6.pkl``.

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE6_PKL=1``
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _mat_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def _pkl_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry6.pkl"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE6_PKL", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def materialize_from_mat() -> dict[str, Any]:
    mat_p = _mat_path().resolve()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing MATLAB fixture: {mat_p}\nRun dump_MDP_pre_entry10.m first.")

    print(f"[FSL backward materialize Entry 6] loadmat from {mat_p}", file=sys.stderr, flush=True)
    raw = loadmat(str(mat_p), simplify_cells=True)
    for key in ("PDP_o", "GDP_id_reward", "GDP_id_contraint", "Ne"):
        if key not in raw:
            raise KeyError(f"{mat_p} missing {key}")

    reward = int(np.asarray(raw["GDP_id_reward"], dtype=np.int64).reshape(-1)[0])
    contraint = int(np.asarray(raw["GDP_id_contraint"], dtype=np.int64).reshape(-1)[0])
    ne_i = int(np.asarray(raw["Ne"], dtype=np.float64).reshape(-1)[0])
    c_arr = raw.get("C")
    c_val = float(np.asarray(c_arr, dtype=np.float64).reshape(-1)[0]) if c_arr is not None else 32.0

    return {
        "pdp_o_obs": np.asarray(raw["PDP_o"], dtype=np.float64),
        "gdp_id": {"reward": reward, "contraint": contraint},
        "Ne": ne_i,
        "C": c_val,
        "source_mat": str(mat_p),
    }


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 6] reuse {pkl}", file=sys.stderr)
        return 0

    payload = materialize_from_mat()
    pkl.parent.mkdir(parents=True, exist_ok=True)
    with pkl.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[FSL backward materialize Entry 6] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
