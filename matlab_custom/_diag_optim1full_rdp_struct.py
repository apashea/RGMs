#!/usr/bin/env python3
"""Structural diff: MATLAB vs Python NR game-1 RDP."""
from __future__ import annotations

import sys
from pathlib import Path

import matlab.engine
import numpy as np
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
from tests.demo1.demo1_paths import demo1_repo_root
from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
from tests.demo1.optim1full.optim1full_replay import atari_c_value
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py


def _scalar(x: object) -> float:
    return float(np.asarray(x, dtype=np.float64).reshape(-1)[0])


def _summ(rdp: dict, label: str) -> None:
    print(
        f"{label}: T={_scalar(rdp.get('T', 0))} L={rdp.get('L')} "
        f"nA={len(rdp.get('A', []))} nB={len(rdp.get('B', []))} "
        f"hasMDP={'MDP' in rdp}"
    )
    if "MDP" in rdp and isinstance(rdp["MDP"], list) and rdp["MDP"]:
        c0 = rdp["MDP"][0]
        print(f"  child0 T={c0.get('T')} nA={len(c0.get('A', []))}")


def main() -> int:
    repo = demo1_repo_root()
    pre = optim1full_mdp_pre_active_inference_mat()
    tmp = repo / "matlab_custom" / "_optim1full_matlab_rdp_nr1.mat"
    pre_posix = str(pre.resolve()).replace("\\", "/")
    tmp_posix = str(tmp.resolve()).replace("\\", "/")

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        eng.eval(
            f"load('{pre_posix}','MDP_pre_active_inference','Ne'); "
            "C=32; NS=256; NT=256; "
            "RDP=spm_set_goals(MDP_pre_active_inference,[2,3],[C,-C]); "
            "RDP=spm_set_costs(RDP,[2,3],[C,-C]); "
            "RDP=spm_mdp2rdp(RDP,0,1/NS); "
            "RDP.T=fix(NT/Ne); "
            f"save('{tmp_posix}','RDP','-v7');",
            nargout=0,
        )
    finally:
        eng.quit()

    rdp_mat = mat_nested_to_py(loadmat(str(tmp))["RDP"])
    mdp_py = load_mdp_from_mat(pre, "MDP_pre_active_inference")
    ne = load_ne_from_mat(pre, "Ne")
    c_val = atari_c_value()
    rdp_py = spm_set_goals(mdp_py, [2, 3], [c_val, -c_val])
    rdp_py = spm_set_costs(rdp_py, [2, 3], [c_val, -c_val])
    rdp_py = spm_mdp2rdp(rdp_py, 0, 1.0 / 256.0)
    rdp_py["T"] = float(int(256 / ne))

    for i, m in enumerate(mdp_py):
        print(f"py_mdp[{i}] na={len(m.get('a', []))} nb={len(m.get('b', []))}")

    eng2 = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng2, repo)
        eng2.eval(f"load('{pre_posix}','MDP_pre_active_inference');", nargout=0)
        for i in range(2):
            na = int(eng2.eval(f"numel(MDP_pre_active_inference{{{i + 1}}}.a)"))
            nb = int(eng2.eval(f"numel(MDP_pre_active_inference{{{i + 1}}}.b)"))
            print(f"mat_mdp[{i}] na={na} nb={nb}")
    finally:
        eng2.quit()

    _summ(rdp_mat if isinstance(rdp_mat, dict) else rdp_mat[0], "mat")
    _summ(rdp_py if isinstance(rdp_py, dict) else rdp_py[0], "py")

    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    try:
        _assert_nested_rdp_equal(rdp_py, rdp_mat, "NR game1 RDP")
        print("RDP oracle: MATCH")
    except AssertionError as exc:
        print("RDP oracle: MISMATCH")
        print(str(exc)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
