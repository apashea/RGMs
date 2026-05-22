"""Debug frozen induction: Pf support, goal pick, P column nnz (Python vs MATLAB)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from matlab_custom import entry12_12f_induction_compare as cmp
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _spm_induction_vb

_INP = ROOT / "matlab_custom" / "entry12_12f_induction_inputs.mat"
_OUT = ROOT / "matlab_custom" / "entry12_12f_induction_internals.json"


def _py_internals(cap: dict) -> dict:
    import os

    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb

    os.environ["RGMS_INDUCTION_DBG"] = "1"
    try:
        R, hif = _spm_induction_vb(cap["B"], cap["H"], cap["Q"], cap["N"], cap["id"])
    finally:
        os.environ.pop("RGMS_INDUCTION_DBG", None)
    Rv = np.asarray(R, dtype=np.float64).ravel(order="F")
    dbg = getattr(vb, "_INDUCTION_DBG", {})
    return {
        "R_sum": float(Rv.sum()),
        "R_nz": np.flatnonzero(Rv > 0).tolist(),
        "hif": np.atleast_1d(hif).tolist(),
        **dbg,
    }


def _mat_internals() -> dict:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        mc = str(ROOT / "matlab_custom" / "entry12").replace("\\", "/")
        eng.addpath(mc, nargout=0)
        ms = str(ROOT / "matlab_src").replace("\\", "/")
        eng.eval(f"addpath(genpath('{ms}'));", nargout=0)
        p = str(_INP).replace("\\", "/")
        eng.eval("out = entry12_induction_internals_from_mat();", nargout=0)
        keys = ["R_sum", "R_nz", "goal_i", "n_col", "P_nnz", "Pf_col1_nnz", "G_max_row"]
        out = {}
        for k in keys:
            v = eng.eval(f"out.{k}", nargout=1)
            if k == "R_nz":
                out[k] = np.atleast_1d(np.asarray(v)).astype(int).tolist()
            elif k in ("goal_i", "n_col", "P_nnz", "Pf_col1_nnz", "G_max_row"):
                out[k] = int(np.asarray(v).reshape(-1)[0])
            else:
                out[k] = float(np.asarray(v).reshape(-1)[0])
        return out
    finally:
        eng.quit()


def main() -> None:
    if not _INP.is_file():
        cap = cmp._capture_inputs()
        cmp.main()
    else:
        cap = None
    py = _py_internals(cap) if cap else _py_internals_from_mat()
    mat = _mat_internals()
    payload = {"python": py, "matlab": mat}
    _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


def _py_internals_from_mat() -> dict:
    S = loadmat(str(_INP), squeeze_me=False)

    def uncell_col(X: np.ndarray) -> list:
        out = []
        for i in range(X.shape[0]):
            out.append(X[i, 0])
        return out

    B = S["B"]
    bp = [[B[0, f, k] for k in range(B.shape[2])] for f in range(B.shape[1])]
    cap = {
        "B": bp,
        "H": uncell_col(S["H"]),
        "Q": uncell_col(S["Q"]),
        "N": int(S["N"].reshape(-1)[0]),
        "id": {},
    }
    if "id_hid" in S:
        cap["id"]["hid"] = S["id_hid"]
    if "id_cid" in S:
        cap["id"]["cid"] = S["id_cid"]
    if "id_D" in S:
        cap["id"]["D"] = S["id_D"]
    return _py_internals(cap)


if __name__ == "__main__":
    main()
