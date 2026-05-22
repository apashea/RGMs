"""spm_VBX replay using phase-log Q_f at pre_forwards (parent m=1, t=2)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    _entry12_phase_log_model_entries,
    _entry12_phase_log_parent_phase_map,
    _entry12_phase_log_qf_factor1,
    entry12_align_12E_snap_to_mat,
    entry12_canonicalize_saved_structures_for_compare,
    load_entry12_subentry_mat,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX, spm_VBX
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

FIX = ROOT / "tests/oracle/toolbox/DEM/fixtures"
TAG = "rgms_canonical"


def _qf_pre_forwards(snap: dict) -> np.ndarray | None:
    ent = _entry12_phase_log_model_entries(snap.get("entry12_phase_log"))
    mp = _entry12_phase_log_parent_phase_map(ent)
    row = mp.get("pre_forwards", {})
    return _entry12_phase_log_qf_factor1(row.get("Q_f"))


def _O_row(snap_py: dict, snap_mat: dict) -> list[np.ndarray]:
    e = entry12_canonicalize_saved_structures_for_compare(
        entry12_align_12E_snap_to_mat(snap_py, snap_mat)
    )
    return [np.asarray(x, dtype=np.float64) for x in e["O"][0]]


def main() -> None:
    import pickle

    py_f = pickle.load(open(FIX / f"DEMAtariIII_entry12_{TAG}_12F.pkl", "rb"))["out_t2"]
    mat_f = mat_nested_to_py(
        load_entry12_subentry_mat(FIX / f"DEMAtariIII_entry12_{TAG}_12F.mat")
    )["out_t2"]
    py_e = pickle.load(open(FIX / f"DEMAtariIII_entry12_{TAG}_12E.pkl", "rb"))["out_t2"]
    mat_e = mat_nested_to_py(
        load_entry12_subentry_mat(FIX / f"DEMAtariIII_entry12_{TAG}_12E.mat")
    )["out_t2"]

    q_py = _qf_pre_forwards(py_f)
    q_ma = _qf_pre_forwards(mat_f)
    if q_py is None or q_ma is None:
        raise RuntimeError("missing pre_forwards Q_f")
    P_py = [q_py.reshape(-1, 1, order="F")]
    P_ma = [q_ma.reshape(-1, 1, order="F")]
    O_row = _O_row(py_e, mat_e)

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

    A_row = cap["A_row"]
    idm = cap["idm"]
    _, f_pyq = spm_VBX(O_row, P_py, A_row, idm)
    _, f_maq = spm_VBX(O_row, P_ma, A_row, idm)
    _, f_live = spm_VBX(cap.get("O_row", O_row), cap.get("P_row", P_py), A_row, idm)

    out = {
        "Qf_maxdiff": float(np.max(np.abs(q_py - q_ma))),
        "F_py_phase_Q": float(f_pyq),
        "F_mat_phase_Q_same_O_A_id": float(f_maq),
        "F_live_hook": float(f_live) if "P_row" in cap else None,
        "F_diff_py_vs_mat_Q": float(f_pyq - f_maq),
    }
    path = ROOT / "matlab_custom" / "_tmp_vbx_phase_q_parity.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
