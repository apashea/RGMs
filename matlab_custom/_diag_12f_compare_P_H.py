"""Compare MAT vs PY 12F out_t1 P/H and implied iH KL at parent t=1."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _spm_log
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py


def _kl(Qf: np.ndarray, Hf: np.ndarray) -> float:
    Qf = np.asarray(Qf, dtype=np.float64).reshape(-1, 1, order="F")
    Hf = np.asarray(Hf, dtype=np.float64).reshape(-1, 1, order="F")
    return float((Qf.T @ (_spm_log(Qf) - _spm_log(Hf))).reshape(-1)[0])


def main() -> None:
    mat_raw = mat_nested_to_py(
        load_entry12_subentry_mat(
            ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.mat"
        )
    )
    py_raw = pickle.load(
        open(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.pkl", "rb")
    )
    ms = mat_raw["out_t1"][0] if isinstance(mat_raw["out_t1"], list) else mat_raw["out_t1"]
    ps = py_raw["out_t1"]
    m_mdp = ms["MDP"][0] if isinstance(ms["MDP"], list) else ms["MDP"]
    p_mdp = ps["MDP"]

    # P{1,1,1} and H{1} at t=1 (0-based t_idx=0)
    mp = np.asarray(ms["P"][0][0][0], dtype=np.float64).reshape(-1, 1, order="F")
    pp = np.asarray(ps["P"][0][0][0], dtype=np.float64).reshape(-1, 1, order="F")
    print("P t=1 max abs diff", float(np.max(np.abs(mp - pp))))

    mh = m_mdp["H"][0] if isinstance(m_mdp.get("H"), list) else m_mdp.get("H")
    ph = p_mdp["H"][0] if isinstance(p_mdp.get("H"), list) else p_mdp.get("H")
    mh = np.asarray(mh, dtype=np.float64).reshape(-1, 1, order="F")
    ph = np.asarray(ph, dtype=np.float64).reshape(-1, 1, order="F")
    print("H max abs diff", float(np.max(np.abs(mh - ph))))

    # B at policy k=0 factor 0 — use parent B from MDP if present
    mb = np.asarray(m_mdp["B"][0][0], dtype=np.float64)  # B{f}(:,:,k) mat cell layout
    pb = np.asarray(p_mdp["B"][0][0], dtype=np.float64)
    print("B[0] shape mat", mb.shape, "py", pb.shape)
    mq = mb @ mp
    pq = pb @ pp
    print("KL mat Qf,Hf", _kl(mq, mh))
    print("KL py Qf,Hf", _kl(pq, ph))
    print("KL mat Qf,py Hf", _kl(mq, ph))
    print("KL py Qf,mat Hf", _kl(pq, mh))


if __name__ == "__main__":
    main()
