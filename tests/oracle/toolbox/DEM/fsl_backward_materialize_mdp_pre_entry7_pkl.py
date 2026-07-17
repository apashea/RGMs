#!/usr/bin/env python3
"""One-time: MATLAB ``.mat`` → PKL for FSL backward Entry 7 input.

Reads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (from
``matlab_custom/fsl_backward/dump_MDP_pre_entry10.m``) — must include ``MDP_pre_entry7``,
``PDP_O``, ``PDP_o``, ``GDP_id_reward``, ``GDP_id_contraint``.

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl``.

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE7_PKL=1``
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
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE7_PKL", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _pdp_o_from_loadmat(pdp_o_raw: Any) -> list[list[Any]]:
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    pdp = mat_nested_to_py(pdp_o_raw)
    if not isinstance(pdp, list):
        raise TypeError(f"PDP_O expected list rows, got {type(pdp).__name__}")
    out: list[list[Any]] = []
    for row in pdp:
        if not isinstance(row, list):
            raise TypeError("PDP_O row must be list of time columns")
        py_row: list[Any] = []
        for cell in row:
            arr = np.asarray(cell, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape((-1, 1), order="F")
            if arr.ndim == 0:
                arr = np.reshape(arr, (1, 1), order="F")
            py_row.append(arr)
        out.append(py_row)
    return out


def materialize_with_engine(eng: Any) -> dict[str, Any]:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    mat_p = _mat_path().resolve()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing MATLAB fixture: {mat_p}\nRun dump_MDP_pre_entry10.m first.")

    print(f"[FSL backward materialize Entry 7] loadmat from {mat_p}", file=sys.stderr, flush=True)
    raw = loadmat(str(mat_p), simplify_cells=True)
    for key in (
        "MDP_pre_entry7",
        "PDP_O",
        "PDP_o",
        "GDP_id_reward",
        "GDP_id_contraint",
    ):
        if key not in raw:
            raise KeyError(
                f"{mat_p} missing {key} — re-run dump_MDP_pre_entry10.m (Entry 7 lane extension)."
            )

    from python_src.toolbox.DEM.dem_atariiii_entry6 import find_events_and_windows
    from python_src.toolbox.DEM.dem_atariiii_pdp_o import assert_pdp_o_columns_sufficient

    pdp_o = _pdp_o_from_loadmat(raw["PDP_O"])
    pdp_o_obs = np.asarray(raw["PDP_o"], dtype=np.float64)
    eng.eval(f"load('{str(mat_p).replace(chr(92), '/')}');", nargout=0)
    print("[FSL backward materialize Entry 7] Engine pull MDP_pre_entry7", file=sys.stderr, flush=True)
    mdp = _pull_mdp_from_matlab(eng, "MDP_pre_entry7")

    c_arr = np.asarray(raw.get("C", eng.eval("double(C)")), dtype=np.float64).reshape(-1)
    ne_arr = np.asarray(raw.get("Ne", eng.eval("double(Ne)")), dtype=np.float64).reshape(-1)
    ne_i = int(ne_arr[0])
    reward = int(np.asarray(raw["GDP_id_reward"], dtype=np.int64).reshape(-1)[0])
    contraint = int(np.asarray(raw["GDP_id_contraint"], dtype=np.int64).reshape(-1)[0])
    gdp_id = {"reward": reward, "contraint": contraint}
    _r, _c, windows = find_events_and_windows(pdp_o_obs, gdp_id, ne_i)
    pdp_max_col = assert_pdp_o_columns_sufficient(
        pdp_o, ne=ne_i, entry6_windows=windows, n_outer=128
    )

    meta = raw.get("meta")
    pdp_max = None
    if isinstance(meta, dict):
        pdp_max = meta.get("PDP_O_maxCol")

    return {
        "mdp": mdp,
        "pdp_o": pdp_o,
        "pdp_o_obs": pdp_o_obs,
        "gdp_id": gdp_id,
        "C": float(c_arr[0]),
        "Ne": int(ne_arr[0]),
        "Nm": int(len(mdp)),
        "PDP_O_cols": len(pdp_o[0]) if pdp_o else 0,
        "PDP_O_maxCol_required": pdp_max_col,
        "PDP_O_maxCol_meta": pdp_max,
        "n_entry6_windows": len(windows),
        "source_mat": str(mat_p),
    }


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 7] reuse {pkl}", file=sys.stderr)
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
    print(f"[FSL backward materialize Entry 7] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
