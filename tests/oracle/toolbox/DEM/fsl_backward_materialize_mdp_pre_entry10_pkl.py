#!/usr/bin/env python3
"""One-time: MATLAB ``.mat`` → reusable PKL for FSL backward Entry 10 input.

Reads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (from
``matlab_custom/fsl_backward/dump_MDP_pre_entry10.m``) via MATLAB Engine pull.

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl``.

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE10_PKL=1``
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _mat_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def _pkl_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE10_PKL", "")).strip().lower() in (
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
    eng.eval(f"load('{str(mat_p).replace(chr(92), '/')}');", nargout=0)
    mdp = _pull_mdp_from_matlab(eng, "MDP_pre_entry10")
    c_val = float(np.asarray(eng.eval("double(C)"), dtype=np.float64).reshape(-1)[0])
    return {
        "mdp": mdp,
        "C": c_val,
        "Ne": int(np.asarray(eng.eval("double(Ne)"), dtype=np.float64).reshape(-1)[0]),
        "Nm": int(np.asarray(eng.eval("double(Nm)"), dtype=np.float64).reshape(-1)[0]),
        "source_mat": str(mat_p),
    }


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 10] reuse {pkl}", file=sys.stderr)
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
    print(f"[FSL backward materialize Entry 10] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
