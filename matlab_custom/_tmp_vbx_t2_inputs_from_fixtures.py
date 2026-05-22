"""Compare O,P,A,id at t=2 from paired 12E/12F fixtures; VBX F on each side."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.spm_VBX import spm_VBX
from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

TAG = "rgms_canonical"
fix = ROOT / "tests/oracle/toolbox/DEM/fixtures"


def parent_mdp(snap: dict) -> dict:
    mdp = snap["MDP"]
    if isinstance(mdp, list):
        return mdp[0]
    return mdp


def o_row_from_12e(snap: dict) -> list:
    O = snap["O"]
    return [np.asarray(O[0][g], dtype=np.float64) for g in range(len(O[0]))]


def p_row_from_12f(snap: dict) -> list:
    Q = snap["Q"]
    return [np.asarray(Q[0][f][1], dtype=np.float64) for f in range(len(Q[0]))]


def a_row_from_12c() -> list:
    py = pickle.load(open(fix / f"DEMAtariIII_entry12_{TAG}_12C.pkl", "rb"))
    A = py["A"][0]
    out = []
    for g in range(len(A)):
        Ag = A[0][g]
        if isinstance(Ag, list):
            Ag = Ag[0]
        out.append(np.asarray(Ag, dtype=np.float64))
    return out


def run_vbx(label: str, O, P, A, idm: dict) -> float:
    _, F = spm_VBX(
        [np.asarray(x, dtype=np.float64) for x in O],
        [np.asarray(x, dtype=np.float64) for x in P],
        A,
        idm,
    )
    print(f"  {label} F = {float(F):.16g}")
    return float(F)


def main() -> None:
    py_e = pickle.load(open(fix / f"DEMAtariIII_entry12_{TAG}_12E.pkl", "rb"))["out_t2"]
    py_f = pickle.load(open(fix / f"DEMAtariIII_entry12_{TAG}_12F.pkl", "rb"))["out_t2"]
    mat_e = mat_nested_to_py(load_entry12_subentry_mat(fix / f"DEMAtariIII_entry12_{TAG}_12E.mat"))["out_t2"]
    mat_f = mat_nested_to_py(load_entry12_subentry_mat(fix / f"DEMAtariIII_entry12_{TAG}_12F.mat"))["out_t2"]

    O_py, O_mat = o_row_from_12e(py_e), o_row_from_12e(mat_e)
    P_py, P_mat = p_row_from_12f(py_f), p_row_from_12f(mat_f)
    id_py = parent_mdp(py_f).get("id") or parent_mdp(py_f)
    id_mat = parent_mdp(mat_f).get("id") or parent_mdp(mat_f)
    if isinstance(id_py, list):
        id_py = id_py[0]
    if isinstance(id_mat, list):
        id_mat = id_mat[0]
    A = a_row_from_12c()

    print("O modality max abs diffs (py vs mat fixture):")
    for g in range(min(len(O_py), len(O_mat))):
        ap, am = np.asarray(O_py[g], dtype=np.float64).ravel(), np.asarray(O_mat[g], dtype=np.float64).ravel()
        if ap.size != am.size:
            print(f"  g{g+1} size py={ap.size} mat={am.size}")
        else:
            d = float(np.max(np.abs(ap - am)))
            if d > 1e-10:
                print(f"  g{g+1} maxdiff={d:.6g}")

    print("P factor max abs diffs:")
    for f in range(min(len(P_py), len(P_mat))):
        pp, pm = np.asarray(P_py[f], dtype=np.float64).ravel(), np.asarray(P_mat[f], dtype=np.float64).ravel()
        if pp.size != pm.size:
            print(f"  f{f+1} size py={pp.size} mat={pm.size}")
        else:
            d = float(np.max(np.abs(pp - pm)))
            if d > 1e-10:
                print(f"  f{f+1} maxdiff={d:.6g} peak_py={int(np.argmax(pp)+1)} peak_mat={int(np.argmax(pm)+1)}")

    print("VBX F cross combos:")
    run_vbx("py_O py_P", O_py, P_py, A, id_py)
    run_vbx("mat_O mat_P", O_mat, P_mat, A, id_mat)
    run_vbx("py_O mat_P", O_py, P_mat, A, id_mat)
    run_vbx("mat_O py_P", O_mat, P_py, A, id_py)

    # phase log F_vbx from fixtures
    def fvbx(snap):
        from python_src.toolbox.DEM.entry12_matlab_capture import (
            _entry12_phase_log_model_entries,
        )
        for ent in _entry12_phase_log_model_entries(snap.get("entry12_phase_log"), m_1b=1):
            if ent.get("phase") == "pre_vbx" and "F_vbx" in ent:
                return float(ent["F_vbx"])
        return None

    print("phase_log F_vbx py", fvbx(py_f))
    print("phase_log F_vbx mat", fvbx(mat_f))


if __name__ == "__main__":
    main()
