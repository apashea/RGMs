"""
12F G decomposition at parent t=1 (MATLAB rand replay): log induction R and iH KL once.

Read-only evidence; patches spm_MDP_VB_XXX for one run then restores.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _cell_get_Qj, _spm_induction_vb, _spm_log
from python_src.spm_dot import spm_dot
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_LOG: dict[str, object] = {}
_ORIG_FWD = vb.spm_forwards
_ORIG_IND = vb._spm_induction_vb


def _patched_ind(B, H, Q, N, id_dict):
    R, r = _ORIG_IND(B, H, Q, N, id_dict)
    nk = len(B[0]) if B and B[0] else 0
    if nk >= 6 and "ind_parent" not in _LOG:
        _LOG["ind_parent"] = {
            "hif": np.asarray(r).tolist(),
            "R_size": int(np.asarray(R).size),
            "R_head": np.asarray(R).ravel()[:5].tolist(),
            "R_max": float(np.max(np.asarray(R))) if np.asarray(R).size else None,
        }
    return R, r


def _patched_forwards(O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa=None):
    mi = int(m) - 1
    idm = id_list[mi]
    nk = len(B[mi][0])
    Ni = len(idm["g"])
    is_parent_band = t == 1 and m == 1 and nk >= 6
    if is_parent_band and "fwd_parent_t1" not in _LOG:
        hid = idm.get("hid")
        _LOG["hid_shape"] = np.asarray(hid).shape if hid is not None else None
        _LOG["id_iH"] = np.asarray(idm.get("iH", [])).tolist()
        _LOG["Ni_nk"] = [Ni, nk]
    out = _ORIG_FWD(O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa)
    if is_parent_band and "fwd_parent_t1" not in _LOG:
        G = np.asarray(out[0], dtype=np.float64)
        id_iH = np.asarray(idm.get("iH", []), dtype=np.int64).ravel()
        B_slice = B[mi]
        H_slice = H[mi]
        nf = len(B_slice)
        P_row = [P[mi][f][t - 1] for f in range(nf)]
        id_fp = np.asarray(idm.get("fp", []), dtype=np.int64).ravel()
        Qp = [None] * nf
        for f in id_fp.tolist():
            Bf1 = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
            Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Qp[int(f) - 1] = Bf1 @ Pf
        id_fu = np.asarray(idm.get("fu", []), dtype=np.int64).ravel()
        for f in id_fu.tolist():
            Bfk = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
            Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Qp[int(f) - 1] = Bfk @ Pf
        kl = None
        for f in id_iH.tolist():
            Qf = np.asarray(Qp[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Hf = np.asarray(H_slice[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            kl = float((Qf.T @ (_spm_log(Qf) - _spm_log(Hf))).reshape(-1)[0])
        n_horiz = int(min(int(T), int(t) + int(N)))
        R, r = _ORIG_IND(B_slice, H_slice, P_row, n_horiz - int(t), idm)
        q_cells = _cell_get_Qj(Qp, r)
        g_dot = float(np.asarray(spm_dot(R, q_cells), dtype=np.float64).reshape(-1)[0])
        _LOG["fwd_parent_t1"] = {
            "G_row0": G[0, :].tolist(),
            "iH_kl": kl,
            "spm_dot_R_Q": g_dot,
        }
    return out


def main() -> None:
    vb._spm_induction_vb = _patched_ind
    vb.spm_forwards = _patched_forwards
    try:
        rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
        pdp = vb.spm_MDP_VB_XXX(
            rdp, {}, monitoring=False, dump_subentries=False, reuse_matlab_draws=True
        )
        G1 = np.asarray(pdp["G"][0], dtype=np.float64).ravel()
        print("PDP G[0][:6]", G1[:6])
        for k, v in _LOG.items():
            print(k, v)
    finally:
        vb._spm_induction_vb = _ORIG_IND
        vb.spm_forwards = _ORIG_FWD


if __name__ == "__main__":
    main()
