"""Save Python-frozen R,Qf; run MATLAB and Python spm_dot on same arrays."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import numpy as np
import scipy.io as sio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _cell_get_Qj, spm_dot
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

MAT_PATH = ROOT / "matlab_custom" / "entry12_12f_frozen_RQf.mat"


def main() -> None:
    vb._PROBE_12F_PARENT = None
    os.environ["RGMS_PROBE_12F_PARENT_T1"] = "1"
    os.environ["RGMS_PROBE_12F_SAVE_MAT"] = "1"
    vb.spm_MDP_VB_XXX(
        spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
        {},
        monitoring=False,
        dump_subentries=False,
        reuse_matlab_draws=True,
    )
    os.environ.pop("RGMS_PROBE_12F_SAVE_MAT", None)
    d = sio.loadmat(str(MAT_PATH))
    R = np.asarray(d["R"], dtype=np.float64)
    Qf = np.asarray(d["Qf"], dtype=np.float64).reshape(-1, 1, order="F")
    r = np.asarray(d["r"], dtype=np.float64).ravel()
    py_dot = float(np.asarray(spm_dot(R, _cell_get_Qj([Qf], r)), dtype=np.float64).reshape(-1)[0])
    manual = float((R.reshape(-1, 1, order="F").T @ Qf).reshape(-1)[0])
    print("Python spm_dot on frozen:", py_dot)
    print("Python manual R'Q:", manual)
    print("R numel", R.size, "nnz", int(np.count_nonzero(R)), "max", float(np.max(R)))

    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        eng.addpath(str(ROOT / "matlab_custom"), nargout=0)
        for p in (
            r"C:\Users\andre\Documents\MATLAB\spm-main",
            r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
        ):
            eng.addpath(p, nargout=0)
        eng.eval(f"cd('{str(ROOT / 'matlab_custom').replace(chr(92), '/')}');", nargout=0)
        eng.eval("entry12_12f_frozen_dot_probe;", nargout=0)
    finally:
        eng.quit()


if __name__ == "__main__":
    main()
