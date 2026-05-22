"""Replay spm_VBX from paired 12E/12F fixtures (py vs mat artifact lanes)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_align_12E_snap_to_mat,
    entry12_align_12F_snap_to_mat,
    entry12_canonicalize_saved_structures_for_compare,
    load_entry12_subentry_mat,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX, spm_VBX
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

FIX = ROOT / "tests/oracle/toolbox/DEM/fixtures"
TAG = "rgms_canonical"


def _load_snaps():
    py_e = __import__("pickle").load(open(FIX / f"DEMAtariIII_entry12_{TAG}_12E.pkl", "rb"))["out_t2"]
    mat_e = mat_nested_to_py(load_entry12_subentry_mat(FIX / f"DEMAtariIII_entry12_{TAG}_12E.mat"))["out_t2"]
    py_f = __import__("pickle").load(open(FIX / f"DEMAtariIII_entry12_{TAG}_12F.pkl", "rb"))["out_t2"]
    mat_f = mat_nested_to_py(load_entry12_subentry_mat(FIX / f"DEMAtariIII_entry12_{TAG}_12F.mat"))["out_t2"]
    return py_e, mat_e, py_f, mat_f


def _lane(side: str, py_e, mat_e, py_f, mat_f):
    if side == "py":
        e = entry12_canonicalize_saved_structures_for_compare(
            entry12_align_12E_snap_to_mat(py_e, mat_e)
        )
        f = entry12_canonicalize_saved_structures_for_compare(
            entry12_align_12F_snap_to_mat(py_f, mat_f)
        )
    else:
        e = entry12_canonicalize_saved_structures_for_compare(mat_e)
        f = entry12_canonicalize_saved_structures_for_compare(mat_f)
    O_row = [np.asarray(x, dtype=np.float64) for x in e["O"][0]]
    P_row = [np.asarray(f["Q"][0], dtype=np.float64).reshape(-1, 1, order="F")]
    return O_row, P_row


def main() -> None:
    py_e, mat_e, py_f, mat_f = _load_snaps()
    O_py, P_py = _lane("py", py_e, mat_e, py_f, mat_f)
    O_ma, P_ma = _lane("mat", py_e, mat_e, py_f, mat_f)
    o_diffs = [
        float(np.max(np.abs(np.asarray(O_py[g]) - np.asarray(O_ma[g]))))
        for g in range(len(O_py))
    ]
    p_diff = float(np.max(np.abs(P_py[0] - P_ma[0])))
    # id + A from Python replay hook at t=2 only
    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb

    cap: dict = {}
    orig = vb.spm_forwards

    def hook(*args, **kw):
        O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = args
        if vb._VB_TIMING_DEPTH == 1 and int(m) == 1 and int(t) == 2:
            mi = 0
            cap["O_row"] = [O[mi][g][t - 1] for g in range(len(O[mi]))]
            cap["P_row"] = [P[mi][f][t - 1] for f in range(len(P[mi]))]
            cap["A_row"] = A[mi]
            cap["idm"] = copy.deepcopy(id_list[mi])
        return orig(*args, **kw)

    vb.spm_forwards = hook
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb.spm_forwards = orig

    idm = cap["idm"]
    A_row = cap["A_row"]
    _, f_py_inputs = spm_VBX(cap["O_row"], cap["P_row"], A_row, idm)
    _, f_fix_py = spm_VBX(O_py, P_py, A_row, idm)
    _, f_fix_ma = spm_VBX(O_ma, P_ma, A_row, idm)
    out = {
        "F_live_hook": float(f_py_inputs),
        "F_py_fixture_OQ": float(f_fix_py),
        "F_mat_fixture_OQ_same_A_id": float(f_fix_ma),
        "P_maxdiff_py_vs_mat": p_diff,
        "O_maxdiff_max": max(o_diffs) if o_diffs else None,
        "A_modalities": len(A_row),
    }
    path = ROOT / "matlab_custom" / "_tmp_vbx_fixture_parity.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
