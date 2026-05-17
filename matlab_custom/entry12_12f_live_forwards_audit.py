"""Live audit at parent m=1 t=1: ih_term, spm_dot, Q@R>0 (rand replay)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from matlab_compat import full as mfull
from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _cell_get_Qj,
    _spm_induction_vb,
    _spm_log,
    spm_dot,
    spm_VBX,
)
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_AUDIT: dict[str, float] = {}
_ORIG = vb.spm_forwards


def _hook(*args, **kw):
    O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = args
    mi = int(m) - 1
    nk = len(B[mi][0])
    if t == 1 and m == 1 and nk >= 6 and not _AUDIT:
        idm = id_list[mi]
        nf = len(B[mi])
        O_row = [O[mi][g][t - 1] for g in range(len(O[mi]))]
        P_row = [P[mi][f][t - 1] for f in range(len(P[mi]))]
        Q_upd, _ = spm_VBX(O_row, P_row, A[mi], idm)
        for f in range(len(Q_upd)):
            P[mi][f][t - 1] = Q_upd[f]
        P_now = [P[mi][f][t - 1] for f in range(nf)]
        B_slice = B[mi]
        H_slice = H[mi]
        R, r = _spm_induction_vb(B_slice, H_slice, P_now, int(T - t), idm)
        Rv = np.asarray(R, dtype=np.float64)
        if Rv.ndim == 1:
            Rv = Rv.reshape(1, -1, order="F")
        elif Rv.ndim == 2 and Rv.shape[1] == 1:
            Rv = Rv.reshape(1, -1, order="F")
        Qp = [None] * nf
        for f in np.asarray(idm.get("fp", []), dtype=np.int64).ravel().tolist():
            Bf1 = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
            Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Qp[int(f) - 1] = Bf1 @ Pf
        k = 0
        for f in np.asarray(idm.get("fu", []), dtype=np.int64).ravel().tolist():
            Bfk = np.asarray(B_slice[int(f) - 1][k], dtype=np.float64)
            Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Qp[int(f) - 1] = Bfk @ Pf
        Qf = np.asarray(Qp[0], dtype=np.float64).reshape(-1, 1, order="F")
        Hf = np.asarray(mfull(H_slice[0]), dtype=np.float64).reshape(-1, 1, order="F")
        nz = np.flatnonzero(Rv.ravel() > 0)
        ih = float((Qf.T @ (_spm_log(Qf) - _spm_log(Hf))).reshape(-1)[0])
        dot = float(np.asarray(spm_dot(Rv, _cell_get_Qj(Qp, r)), dtype=np.float64).reshape(-1)[0])
        Pf0 = np.asarray(P_now[0], dtype=np.float64).ravel()
        top_p = np.argsort(-Pf0)[:5].tolist()
        import scipy.io as sio

        sio.savemat(
            str(ROOT / "matlab_custom" / "entry12_12f_live_inputs.mat"),
            {
                "Bslice": B_slice,
                "Hlist": H_slice,
                "Pnow": P_now,
                "idm": idm,
                "Qf": Qf,
                "Hf": Hf,
                "Rv": Rv,
                "Nhoriz": int(T - t),
            },
        )
        _AUDIT.update(
            {
                "ih_term": ih,
                "spm_dot": dot,
                "Q_at_R_nz0": float(Qf.ravel()[nz[0]]) if nz.size else 0.0,
                "Q_at_R_nz1": float(Qf.ravel()[nz[1]]) if nz.size > 1 else 0.0,
                "iH_len": float(len(np.asarray(idm.get("iH", [])).ravel())),
                "fp_len": float(len(np.asarray(idm.get("fp", [])).ravel())),
                "fu_len": float(len(np.asarray(idm.get("fu", [])).ravel())),
                "R_nz0": float(nz[0]) if nz.size else -1.0,
                "R_nz1": float(nz[1]) if nz.size > 1 else -1.0,
                "r_len": float(np.asarray(r).size),
                "P_top5_idx": float(top_p[0]) if top_p else -1.0,
                "P_top5_mass": float(Pf0[top_p[0]]) if top_p else 0.0,
                "Qp_max": float(np.max(Qf)),
            }
        )
    G, P2, F, id2, Pa = _ORIG(*args, **kw)
    if t == 1 and m == 1 and nk >= 6 and "G00" not in _AUDIT:
        _AUDIT["G00"] = float(np.asarray(G, dtype=np.float64).reshape(-1)[0])
    return G, P2, F, id2, Pa


def main() -> None:
    vb.spm_forwards = _hook
    try:
        pdp = vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb.spm_forwards = _ORIG
    g1 = float(np.asarray(pdp["G"][0], dtype=np.float64).ravel()[0])
    print("live audit", _AUDIT)
    print("PDP G[0]", g1)


if __name__ == "__main__":
    main()
