"""FSL Entry 10: numpy vs MATLAB eig on pre_entry10 boundary."""
from __future__ import annotations

import copy
import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import matlab.engine
import numpy as np
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal, _pull_mdp_from_matlab
from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig

fixtures = _REPO / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"
pre10 = pickle.load(open(fixtures / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl", "rb"))["mdp"]

eng = matlab.engine.start_matlab()
try:
    eng.addpath(str(_REPO), nargout=0)
    eng.addpath(str(_REPO / "matlab_src"), nargout=0)
    eng.addpath(str(_REPO / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    mat_p = fixtures / "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat"
    eng.eval(f"load('{str(mat_p.resolve()).replace(chr(92), '/')}');", nargout=0)
    mat11 = _pull_mdp_from_matlab(eng, "MDP_pre_entry11")
    meig = _make_matlab_spm_RDP_sort_eig(eng)
    mdp_np, _ = spm_RDP_sort(copy.deepcopy(pre10))
    mdp_ml, j_ml = spm_RDP_sort(copy.deepcopy(pre10), meig)
    print("numpy sort lev2 a", np.asarray(mdp_np[1]["a"][0]).shape)
    print("matlab eig sort lev2 a", np.asarray(mdp_ml[1]["a"][0]).shape)
    print("authority lev2 a", np.asarray(mat11[1]["a"][0]).shape)
    print("j_ml len", np.asarray(j_ml).size)
    for label, mdp in ("numpy", mdp_np), ("matlab-eig", mdp_ml):
        try:
            _assert_mdp_full_equal(mdp, mat11, 10)
            print(f"{label} vs authority: OK")
        except AssertionError as e:
            print(f"{label} vs authority: {e}")
finally:
    eng.quit()
