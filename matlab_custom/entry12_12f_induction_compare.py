"""Frozen spm_induction inputs: Python vs MATLAB (entry12_dump fork)."""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _spm_induction_vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_INP = ROOT / "matlab_custom" / "entry12_12f_induction_inputs.mat"
_OUT = ROOT / "matlab_custom" / "entry12_12f_induction_compare_results.json"


def _capture_inputs() -> dict:
    """Run VB; freeze B,H,Q,N,id at parent ``t=1,m=1`` induction (probe band)."""
    captured: dict = {}
    orig_fwd = vb.spm_forwards
    orig_ind = vb._spm_induction_vb
    vb._ENTRY12_CAPTURE_INDUCTION = False

    def _ind_wrap(B, H, Q, N, id_dict):
        if vb._ENTRY12_CAPTURE_INDUCTION and "B" not in captured:
            captured["B"] = copy.deepcopy(B)
            captured["H"] = copy.deepcopy(H)
            captured["Q"] = copy.deepcopy(Q)
            captured["N"] = int(N)
            captured["id"] = copy.deepcopy(id_dict)
        return orig_ind(B, H, Q, N, id_dict)

    def _fwd_wrap(*args, **kwargs):
        O, P, A, B, C, H, K, W, I, t, T, N_hor, m, id_list, pA, qa = (
            args[0],
            args[1],
            args[2],
            args[3],
            args[4],
            args[5],
            args[6],
            args[7],
            args[8],
            args[9],
            args[10],
            args[11],
            args[12],
            args[13],
            args[14],
            kwargs.get("qa"),
        )
        mi = int(m) - 1
        vb._ENTRY12_CAPTURE_INDUCTION = (
            int(t) == 1 and int(m) == 1 and len(B[mi][0]) >= 6 and "B" not in captured
        )
        try:
            return orig_fwd(*args, **kwargs)
        finally:
            vb._ENTRY12_CAPTURE_INDUCTION = False

    vb.spm_forwards = _fwd_wrap
    vb._spm_induction_vb = _ind_wrap
    try:
        rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
        vb.spm_MDP_VB_XXX(
            rdp,
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb.spm_forwards = orig_fwd
        vb._spm_induction_vb = orig_ind
        vb._ENTRY12_CAPTURE_INDUCTION = False

    if "B" not in captured:
        raise RuntimeError("failed to capture induction inputs at parent t=1,m=1")
    return captured


def _py_induction(captured: dict) -> dict:
    R, hif = _spm_induction_vb(
        captured["B"],
        captured["H"],
        captured["Q"],
        captured["N"],
        captured["id"],
    )
    Rv = np.asarray(R, dtype=np.float64).ravel(order="F")
    nz = np.flatnonzero(Rv > 0.0)
    return {
        "R_shape": list(np.asarray(R).shape),
        "R_sum": float(np.sum(Rv)),
        "R_nz": nz.tolist(),
        "R_max": float(np.max(Rv)) if Rv.size else 0.0,
        "hif": np.atleast_1d(np.asarray(hif, dtype=np.int64)).ravel().tolist(),
    }


def _mat_induction() -> dict:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        mc = str(ROOT / "matlab_custom" / "entry12").replace("\\", "/")
        eng.addpath(mc, nargout=0)
        eng.addpath(str(ROOT / "matlab_src" / "toolbox" / "DEM"), nargout=0)
        inp = str(_INP).replace("\\", "/")
        eng.eval(f"out = entry12_induction_only_probe();", nargout=0)
        hif = np.atleast_1d(np.asarray(eng.eval("out.hif", nargout=1)).ravel()).tolist()
        rsum = float(np.asarray(eng.eval("out.R_sum", nargout=1)).reshape(-1)[0])
        rmax = float(np.asarray(eng.eval("out.R_max", nargout=1)).reshape(-1)[0])
        rnz = np.atleast_1d(np.asarray(eng.eval("out.R_nz", nargout=1)).ravel()).astype(int).tolist()
        rshape = np.atleast_1d(np.asarray(eng.eval("out.R_shape", nargout=1)).ravel()).astype(int).tolist()
        return {
            "R_shape": rshape,
            "R_sum": rsum,
            "R_nz": rnz,
            "R_max": rmax,
            "hif": [int(x) for x in hif],
        }
    finally:
        eng.quit()


def _wrap_b_matlab(bp: list) -> np.ndarray:
    nf = len(bp)
    nk = len(bp[0])
    arr = np.empty((1, nf, nk), dtype=object)
    for f in range(nf):
        for k in range(nk):
            arr[0, f, k] = np.asarray(bp[f][k], dtype=np.float64)
    return arr


def _cells_column(lst: list) -> np.ndarray:
    """MATLAB column cell (n,1); avoid np.asarray stacking (485,1) into (1,485,1)."""
    out = np.empty((len(lst), 1), dtype=object)
    for i, x in enumerate(lst):
        out[i, 0] = np.asarray(x, dtype=np.float64).reshape(-1, 1, order="F")
    return out


def main() -> None:
    cap = _capture_inputs()
    idm = cap["id"]
    save_kw: dict = {
        "B": _wrap_b_matlab(cap["B"]),
        "H": _cells_column(cap["H"]),
        "Q": _cells_column(cap["Q"]),
        "N": np.array([[float(cap["N"])]]),
    }
    if isinstance(idm, dict):
        if "hid" in idm and idm["hid"] is not None:
            save_kw["id_hid"] = np.asarray(idm["hid"], dtype=np.float64)
        if "cid" in idm and idm["cid"] is not None:
            save_kw["id_cid"] = np.asarray(idm["cid"], dtype=np.float64)
        if "D" in idm:
            save_kw["id_D"] = idm["D"]
    savemat(str(_INP), save_kw)
    py = _py_induction(cap)
    mat = _mat_induction()
    out = {"python_on_py_inputs": py, "matlab_on_py_inputs": mat}
    _OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"wrote {_OUT}")


if __name__ == "__main__":
    main()
