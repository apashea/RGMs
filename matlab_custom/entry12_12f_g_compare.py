"""Compare parent MDP.G at 12F boundary: XXX12 PKL vs canonical MAT."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

PKL = ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_pdp.pkl"
MAT_PDP = ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_pdp.mat"
MAT_12F = ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.mat"


def _g1(pdp: dict) -> float:
    g = pdp["G"]
    if isinstance(g, list):
        return float(np.asarray(g[0], dtype=np.float64).ravel()[0])
    return float(np.asarray(g, dtype=np.float64).ravel()[0])


def main() -> None:
    with open(PKL, "rb") as f:
        pkl_pdp = pickle.load(f)["PDP"]
    print("XXX12 PKL G[0]:", _g1(pkl_pdp))

    snap = mat_nested_to_py(load_entry12_subentry_mat(MAT_12F))["out_t1"]
    if isinstance(snap, list):
        snap = snap[0]
    mdp = snap["MDP"]
    g = mdp["G"]
    if isinstance(g, list):
        g0 = np.asarray(g[0], dtype=np.float64).ravel()
    else:
        g0 = np.asarray(g, dtype=np.float64).ravel()
    print("12F canonical out_t1 MDP.G:", g0[:6], "shape", g0.shape)


if __name__ == "__main__":
    main()
