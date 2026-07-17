#!/usr/bin/env python3
"""One-time: MATLAB ``.mat`` → PKL for FSL backward Entry 5 input.

Reads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (``MDP_pre_entry5``).

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry5.pkl``.

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE5_PKL=1``
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
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry5.pkl"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE5_PKL", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def materialize_with_engine(eng: Any) -> dict[str, Any]:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    mat_p = _mat_path().resolve()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing MATLAB fixture: {mat_p}\nRun dump_MDP_pre_entry10.m first.")

    print(f"[FSL backward materialize Entry 5] loadmat from {mat_p}", file=sys.stderr, flush=True)
    raw = loadmat(str(mat_p), simplify_cells=True)
    if "MDP_pre_entry5" not in raw:
        raise KeyError(
            f"{mat_p} missing MDP_pre_entry5 — run patch_mdp_pre_entry5_to_pre_entry10_mat.m "
            "or re-run dump_MDP_pre_entry10.m."
        )

    eng.eval(f"load('{str(mat_p).replace(chr(92), '/')}');", nargout=0)
    print("[FSL backward materialize Entry 5] Engine pull MDP_pre_entry5", file=sys.stderr, flush=True)
    mdp = _pull_mdp_from_matlab(eng, "MDP_pre_entry5")

    c_arr = np.asarray(raw.get("C", eng.eval("double(C)")), dtype=np.float64).reshape(-1)
    nm = len(mdp)
    ne = max(2 ** (nm - 1), 1)

    return {
        "mdp": mdp,
        "Nm": nm,
        "Ne": ne,
        "C": float(c_arr[0]),
        "source_mat": str(mat_p),
    }


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 5] reuse {pkl}", file=sys.stderr)
        return 0

    import matlab.engine

    repo = _REPO
    eng = matlab.engine.start_matlab()
    try:
        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

        dem_path = configure_dem_matlab_engine(eng, repo)
        payload = materialize_with_engine(eng)
    finally:
        eng.quit()

    pkl.parent.mkdir(parents=True, exist_ok=True)
    with pkl.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[FSL backward materialize Entry 5] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
