"""Replay spm_forwards at t=1 using 12F out_t1 snap Q as P (check snap timing)."""
from __future__ import annotations

import copy
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_forwards
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp
import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb


def main() -> None:
    snap = pickle.load(
        open(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.pkl", "rb")
    )["out_t1"]
    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    models = vb._vb_models_after_checkx(rdp)
    bundle = vb._vb_tensors_through_H(models, len(models), float(models[0]["T"]))
    # inject snap posteriors at t=0 (MATLAB t=1)
    Pf = np.asarray(snap["Q"][0][0][0], dtype=np.float64).reshape(-1, 1, order="F")
    bundle["Q"][0][0][0] = Pf.copy()
    bundle["P"][0][0][0] = Pf.copy()
    G, *_ = spm_forwards(
        bundle["O"],
        bundle["Q"],
        bundle["A"],
        bundle["BP"],
        bundle["C"],
        bundle["H"],
        bundle["K"],
        bundle["W"],
        bundle["IP"],
        1,
        int(bundle["T"]),
        int(bundle["N_policy_depth"]),
        1,
        bundle["id"],
        bundle["pA"],
        bundle.get("qa"),
    )
    g0 = float(np.asarray(G, dtype=np.float64).reshape(-1)[0])
    stored = float(np.asarray(snap["MDP"]["G"][0], dtype=np.float64).ravel()[0])
    print("forwards G[0,0] from snap Q as P:", g0)
    print("stored MDP.G[0]:", stored)


if __name__ == "__main__":
    main()
