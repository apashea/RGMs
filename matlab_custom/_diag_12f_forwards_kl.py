"""Reproduce 12F forwards iH KL at parent t=1 from saved 12F out_t1 inputs."""
from __future__ import annotations

import copy
import os
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_forwards, _spm_log
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb


def _snap12f() -> tuple[dict, dict]:
    mat_raw = mat_nested_to_py(
        load_entry12_subentry_mat(
            ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.mat"
        )
    )
    snap_m = mat_raw["out_t1"]
    if isinstance(snap_m, list):
        snap_m = snap_m[0]
    snap_p = pickle.load(
        open(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.pkl", "rb")
    )["out_t1"]
    return snap_m, snap_p


def _kl(Qf: np.ndarray, Hf: np.ndarray) -> float:
    Qf = Qf.reshape(-1, 1, order="F")
    Hf = Hf.reshape(-1, 1, order="F")
    return float((Qf.T @ (_spm_log(Qf) - _spm_log(Hf))).reshape(-1)[0])


def main() -> None:
    snap_m, snap_p = _snap12f()
    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    models = vb._vb_models_after_checkx(rdp)
    nm = len(models)
    bundle = vb._vb_tensors_through_H(models, nm, float(models[0]["T"]))
    # after partial t=1 loop state is in py snap; use bundle + models from full re-run shortcut:
    # run only forwards at t=1 with current bundle from XXX12 is heavy — use py snap Q,P vs mat
    m_mdp = snap_m["MDP"]
    if isinstance(m_mdp, list):
        m_mdp = m_mdp[0]
    print(
        "MAT vs PY G[0][0]:",
        np.asarray(m_mdp["G"]).ravel()[0],
        np.asarray(snap_p["MDP"]["G"][0]).ravel()[0],
    )
    print("PY bundle id[0].iH", bundle["id"][0].get("iH"))
    Hf = np.asarray(bundle["H"][0][0], dtype=np.float64).reshape(-1, 1, order="F")
  # Qp at t=1 policy k=0 factor 1 from mat snap P,Q if available
    P = snap_p["P"]
    Q = snap_p["Q"]
    B = bundle["B"][0][0][0]  # factor 1, policy 0
    Pf = np.asarray(P[0][0][0], dtype=np.float64).reshape(-1, 1, order="F")
    Qf = B @ Pf
    print("PY KL(Qf,Hf) k=0", _kl(Qf, Hf))
    os.environ["RGMS_SKIP_IH"] = "1"
    G_skip, *_ = spm_forwards(
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
        bundle["qa"],
    )
    del os.environ["RGMS_SKIP_IH"]
    G_full, *_ = spm_forwards(
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
        bundle["qa"],
    )
    print("forwards G[0,0] skip_iH", float(np.asarray(G_skip).reshape(-1)[0]))
    print("forwards G[0,0] full", float(np.asarray(G_full).reshape(-1)[0]))
    print("delta", float(np.asarray(G_full).reshape(-1)[0] - np.asarray(G_skip).reshape(-1)[0]))


if __name__ == "__main__":
    main()
