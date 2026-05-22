"""Save Python pre-forwards O,P at parent t=2; cross-call Python vs MATLAB spm_VBX."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_VBX
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_CAPTURE: dict[str, object] = {}
_orig_fwd = vb.spm_forwards


def _fwd(*args, **kw):
    O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = args
    if vb._VB_TIMING_DEPTH == 1 and int(m) == 1 and int(t) == 2:
        mi = 0
        O_row = [O[mi][g][t - 1] for g in range(len(O[mi]))]
        P_row = [P[mi][f][t - 1] for f in range(len(P[mi]))]

        def _cells(lst: list) -> np.ndarray:
            out = np.empty((len(lst), 1), dtype=object)
            for i, x in enumerate(lst):
                out[i, 0] = np.asarray(x, dtype=np.float64)
            return out

        _CAPTURE["Orow"] = O_row
        _CAPTURE["Prow"] = P_row
        _CAPTURE["Arow"] = A[mi]
        _CAPTURE["idm"] = copy.deepcopy(id_list[mi])
        savemat(
            str(ROOT / "matlab_custom" / "entry12_12f_vbx_t2_pre_fwd.mat"),
            {
                "Orow": _cells(O_row),
                "Prow": _cells(P_row),
                "Arow": _cells(list(A[mi])),
                "idm": id_list[mi],
            },
        )
    return _orig_fwd(*args, **kw)


def main() -> None:
    vb.spm_forwards = _fwd
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb.spm_forwards = _orig_fwd

    if not _CAPTURE:
        raise RuntimeError("capture failed")
    O_row = _CAPTURE["Orow"]
    P_row = _CAPTURE["Prow"]
    A_row = _CAPTURE["Arow"]
    idm = _CAPTURE["idm"]
    _, f_py = spm_VBX(O_row, P_row, A_row, idm)

    import matlab.engine

    eng = matlab.engine.start_matlab()
    eng.addpath(str(ROOT / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    eng.addpath(str(ROOT / "matlab_custom"), nargout=0)
    eng.eval(
        "load('entry12_12f_vbx_t2_pre_fwd.mat'); [Q,F]=spm_VBX(Orow,Prow,Arow,idm);",
        nargout=0,
    )
    f_mat = float(eng.workspace["F"])
    eng.quit()

    out = {
        "F_python_vbx": float(f_py),
        "F_matlab_vbx": f_mat,
        "P_sizes": [int(np.asarray(p).size) for p in P_row],
        "O_sums": [float(np.sum(np.asarray(o, dtype=np.float64))) for o in O_row],
    }
    path = ROOT / "matlab_custom" / "entry12_12f_vbx_t2_crosslane.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
