"""Probe per-t VBX scalar F at parent m=1 (Entry 12F MDP.F drift)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_VBX, spm_forwards
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_PROBE: dict[str, object] = {}
_ORIG = vb.spm_forwards


def _hook(*args, **kw):
    O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = args
    mi = int(m) - 1
    if vb._VB_TIMING_DEPTH != 1:
        return _ORIG(*args, **kw)
    if int(m) == 1 and int(t) in (1, 2, 3):
        O_row = [O[mi][g][t - 1] for g in range(len(O[mi]))]
        P_row = [P[mi][f][t - 1] for f in range(len(P[mi]))]
        idm = id_list[mi]
        _, f_vbx = spm_VBX(O_row, P_row, A[mi], idm)
        G, P2, f_fwd, id2, _ = _ORIG(*args, **kw)
        key = f"t{int(t)}"
        if int(t) == 2:
            from scipy.io import savemat

            def _cells_column(lst: list) -> np.ndarray:
                out = np.empty((len(lst), 1), dtype=object)
                for i, x in enumerate(lst):
                    out[i, 0] = np.asarray(x, dtype=np.float64)
                return out

            def _id_for_mat(id_dict: dict) -> dict:
                out: dict = {}
                for key, val in id_dict.items():
                    if key == "g" and isinstance(val, list):
                        gcell = np.empty((len(val), 1), dtype=object)
                        for gi, gv in enumerate(val):
                            gcell[gi, 0] = np.asarray(gv, dtype=np.float64)
                        out["g"] = gcell
                    elif isinstance(val, (list, tuple)):
                        out[key] = _cells_column(list(val))
                    else:
                        out[key] = val
                return out

            savemat(
                str(ROOT / "matlab_custom" / "entry12_12f_vbx_t2_inputs.mat"),
                {
                    "Orow": _cells_column(O_row),
                    "Prow": _cells_column(P_row),
                    "Arow": _cells_column(A[mi]),
                    "idm": _id_for_mat(idm),
                },
            )
        _PROBE[key] = {
            "depth": int(vb._VB_TIMING_DEPTH),
            "F_vbx": float(f_vbx),
            "F_forwards": float(f_fwd),
            "O_numel": [int(np.asarray(O_row[g]).size) for g in range(len(O_row))],
            "O_sum": [float(np.sum(np.asarray(O_row[g], dtype=np.float64))) for g in range(len(O_row))],
            "P_numel": [int(np.asarray(P_row[f]).size) for f in range(len(P_row))],
            "has_i": "i" in idm,
            "i_sel": int(idm["i"]) if "i" in idm else None,
            "g_partitions": len(idm.get("g", [])),
        }
        return G, P2, f_fwd, id2, _
    return _ORIG(*args, **kw)


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
    f_traj = np.asarray(pdp.get("F", []), dtype=np.float64).ravel()
    _PROBE["F_traj_head"] = f_traj[:8].tolist()
    _PROBE["F_traj_nz"] = int(np.sum(np.abs(f_traj) > 1e-6))
    out = ROOT / "matlab_custom" / "entry12_12f_vbx_F_probe.json"
    out.write_text(json.dumps(_PROBE, indent=2), encoding="utf-8")
    print(json.dumps(_PROBE, indent=2))


if __name__ == "__main__":
    main()
