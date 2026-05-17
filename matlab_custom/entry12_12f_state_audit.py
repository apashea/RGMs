"""RNG/state audit: parent t=1 P, Qp, R vs MATLAB 12F canonical snap (rand replay)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _spm_induction_vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_dot, _cell_get_Qj
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_AUDIT: dict[str, object] = {}
_ORIG_FWD = vb.spm_forwards


def _audit_forwards(*args, **kw):
    O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = (
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
        kw.get("qa"),
    )
    mi = int(m) - 1
    if t == 1 and m == 1 and len(B[mi][0]) >= 6 and not _AUDIT:
        idm = id_list[mi]
        B_slice = B[mi]
        nf = len(B_slice)
        P_row = [np.asarray(P[mi][f][0], dtype=np.float64).reshape(-1, 1, order="F") for f in range(nf)]
        id_fp = np.asarray(idm.get("fp", np.int64), dtype=np.int64).ravel()
        Qp = [None] * nf
        for f in id_fp.tolist():
            Bf1 = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
            Qp[int(f) - 1] = Bf1 @ P_row[int(f) - 1]
        id_fu = np.asarray(idm.get("fu", np.int64), dtype=np.int64).ravel()
        for f in id_fu.tolist():
            Bfk = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
            Qp[int(f) - 1] = Bfk @ P_row[int(f) - 1]
        n_horiz = int(min(int(T), int(t) + int(N)))
        R, r = _spm_induction_vb(B_slice, H[mi], P_row, n_horiz - int(t), idm)
        Rv = np.asarray(R, dtype=np.float64)
        if Rv.ndim == 1:
            Rv = Rv.reshape(1, -1, order="F")
        elif Rv.ndim == 2 and Rv.shape[1] == 1:
            Rv = Rv.reshape(1, -1, order="F")
        Qf = np.asarray(Qp[0], dtype=np.float64).reshape(-1, 1, order="F")
        nz = np.flatnonzero(Rv.ravel() > 0)
        _AUDIT.update(
            {
                "P": P_row[0].copy(),
                "Qf": Qf.copy(),
                "R": Rv.copy(),
                "R_nz": nz.tolist(),
                "Q_at_R_nz": Qf.ravel()[nz].tolist() if nz.size else [],
                "dot_manual": float((Rv.reshape(-1, 1) @ Qf).reshape(-1)[0]),
                "dot_spm": float(
                    np.asarray(spm_dot(Rv, _cell_get_Qj(Qp, r)), dtype=np.float64).reshape(-1)[0]
                ),
            }
        )
    return _ORIG_FWD(*args, **kw)


def _load_mat_snap() -> dict:
    mat = mat_nested_to_py(
        load_entry12_subentry_mat(
            ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.mat"
        )
    )
    snap = mat["out_t1"]
    if isinstance(snap, list):
        snap = snap[0]
    return snap


def main() -> None:
    vb.spm_forwards = _audit_forwards
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb.spm_forwards = _ORIG_FWD

    print("=== Python replay at parent t=1 (pre-forwards audit) ===")
    for k, v in _AUDIT.items():
        if isinstance(v, np.ndarray):
            print(k, v.shape, "max", float(np.max(v)), "sum", float(np.sum(v)))
        else:
            print(k, v)

    ms = _load_mat_snap()
    print("\n=== MATLAB 12F out_t1 snap keys ===", list(ms.keys()))
    # P in snap: cell {m,f,t} or nested
    Pm = ms.get("P")
    print("MAT P type", type(Pm))
    try:
        if isinstance(Pm, list):
            Pf = np.asarray(Pm[0][0][0], dtype=np.float64).reshape(-1, 1, order="F")
        else:
            Pf = np.asarray(Pm, dtype=np.float64).reshape(-1, 1, order="F")
        print("MAT P shape", Pf.shape, "max", float(np.max(Pf)), "sum", float(np.sum(Pf)))
        if "P" in _AUDIT:
            Pp = _AUDIT["P"]
            print("P max abs diff", float(np.max(np.abs(Pp - Pf))))
    except Exception as e:
        print("MAT P access", e)


if __name__ == "__main__":
    main()
