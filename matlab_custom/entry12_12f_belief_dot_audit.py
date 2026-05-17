"""Belief/dot audit at 12F out_t1: MAT vs PY P, Qp, R, spm_dot."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from matlab_compat import full as mfull

from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _cell_get_Qj,
    _spm_induction_vb,
    _spm_log,
    spm_dot,
)
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py


def _snap(blob: dict, key: str) -> dict:
    s = blob[key]
    return s[0] if isinstance(s, list) else s


def _p_at_t(snap: dict) -> np.ndarray:
    p = snap["P"]
    # nested list or ndarray — walk to factor 0 time 0
    while isinstance(p, list):
        p = p[0]
    return np.asarray(p, dtype=np.float64).reshape(-1, 1, order="F")


def _audit(label: str, snap: dict, *, t_horizon: int) -> None:
    mdp = snap["MDP"]
    if isinstance(mdp, list):
        mdp = mdp[0]
    B = mdp["B"]
    B0 = np.asarray(B[0][0] if isinstance(B[0], list) else B[0], dtype=np.float64)
    Hraw = mdp["H"][0] if isinstance(mdp.get("H"), list) else mdp["H"]
    H0 = np.asarray(mfull(Hraw), dtype=np.float64).reshape(-1, 1, order="F")
    Pf = _p_at_t(snap)
    Qf = B0 @ Pf
    idm = mdp["id"]
    H_list = mdp["H"] if isinstance(mdp.get("H"), list) else [mdp["H"]]
    R, r = _spm_induction_vb(B, H_list, [Qf], t_horizon, idm)
    Rv = np.asarray(R, dtype=np.float64)
    if Rv.ndim == 1:
        Rv = Rv.reshape(1, -1, order="F")
    elif Rv.ndim == 2 and Rv.shape[1] == 1:
        Rv = Rv.reshape(1, -1, order="F")
    nz = np.flatnonzero(Rv.ravel() > 0)
    dot = float(np.asarray(spm_dot(Rv, _cell_get_Qj([Qf], r)), dtype=np.float64).reshape(-1)[0])
    ih = float((Qf.T @ (_spm_log(Qf) - _spm_log(H0))).reshape(-1)[0])
    g = np.asarray(mdp["G"], dtype=np.float64).ravel()
    print(f"=== {label} ===")
    print("P sum", float(np.sum(Pf)), "max", float(np.max(Pf)))
    print("Qf at R>0", Qf.ravel()[nz].tolist() if nz.size else [])
    print("R nz", nz.tolist(), "R sum", float(np.sum(Rv)))
    print("ih_term", ih, "spm_dot", dot, "ih+dot", ih + dot)
    print("MDP.G row0", float(g[0]) if g.size else "?")


def main() -> None:
    mat = mat_nested_to_py(
        load_entry12_subentry_mat(
            ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.mat"
        )
    )
    py = pickle.load(
        open(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.pkl", "rb")
    )
    ms, ps = _snap(mat, "out_t1"), py["out_t1"]
    t1 = int(np.asarray(ms.get("t", 1)).item())
    _audit("MAT out_t1", ms, t_horizon=1)
    _audit("PY out_t1", ps, t_horizon=1)
    Pf_m, Pf_p = _p_at_t(ms), _p_at_t(ps)
    print("P max abs diff", float(np.max(np.abs(Pf_m - Pf_p))))


if __name__ == "__main__":
    main()
