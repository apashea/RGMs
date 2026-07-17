#!/usr/bin/env python3
"""One-time: MATLAB ``.mat`` → PKL for FSL backward Entry 4 input.

Reads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (``PDP_O`` slice cols 1:1000).

Writes ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl``.

Opt-in refresh: ``RGMS_FSL_BACKWARD_REFRESH_MDP_PRE4_PKL=1``
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
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"


def _refresh() -> bool:
    return str(os.getenv("RGMS_FSL_BACKWARD_REFRESH_MDP_PRE4_PKL", "")).strip().lower() in (
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


def materialize_from_mat() -> dict[str, Any]:
    from python_src.toolbox.DEM.dem_atariiii_entry4 import (
        ENTRY4_O_COLS,
        atari_S_and_Sc,
        slice_pdp_o_for_entry4,
    )

    mat_p = _mat_path().resolve()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing MATLAB fixture: {mat_p}\nRun dump_MDP_pre_entry10.m first.")

    print(f"[FSL backward materialize Entry 4] loadmat from {mat_p}", file=sys.stderr, flush=True)
    raw = loadmat(str(mat_p), simplify_cells=True)
    if "PDP_O" not in raw:
        raise KeyError(f"{mat_p} missing PDP_O — re-run dump_MDP_pre_entry10.m.")

    pdp_o = _pdp_o_from_loadmat(raw["PDP_O"])
    ncol = len(pdp_o[0]) if pdp_o else 0
    if ncol < ENTRY4_O_COLS:
        raise ValueError(f"PDP_O has {ncol} cols; Entry 4 needs {ENTRY4_O_COLS}")
    pdp_o_sl = slice_pdp_o_for_entry4(pdp_o)
    s, sc = atari_S_and_Sc()
    c_arr = raw.get("C")
    c_val = float(np.asarray(c_arr, dtype=np.float64).reshape(-1)[0]) if c_arr is not None else 32.0

    return {
        "pdp_o_sl": pdp_o_sl,
        "S": s,
        "Sc": sc,
        "C": c_val,
        "entry4_o_cols": ENTRY4_O_COLS,
        "PDP_O_cols": ncol,
        "source_mat": str(mat_p),
    }


def main() -> int:
    pkl = _pkl_path()
    if pkl.is_file() and not _refresh():
        print(f"[FSL backward materialize Entry 4] reuse {pkl}", file=sys.stderr)
        return 0

    payload = materialize_from_mat()
    pkl.parent.mkdir(parents=True, exist_ok=True)
    with pkl.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[FSL backward materialize Entry 4] wrote {pkl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
