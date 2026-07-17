#!/usr/bin/env python3
"""Compare Python VB draw count on MATLAB-assembled vs Python-assembled NR RDP."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import matlab.engine
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
from tests.demo1.demo1_paths import demo1_repo_root
from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
from tests.demo1.optim1full.optim1full_replay import atari_c_value
from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env
from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py


def _coerce_rdp_t_scalar(rdp: object) -> None:
    import numpy as np

    models = rdp if isinstance(rdp, list) else [rdp]
    for m in models:
        if isinstance(m, dict) and "T" in m:
            m["T"] = float(np.asarray(m["T"]).reshape(-1)[0])


def _vb_draws(rdp: object, buf, start: int, allow: int) -> int | str:
    seq = buf[start : start + allow]
    ctr = [0]

    def shim(*_a: object, **_k: object) -> float:
        if ctr[0] >= len(seq):
            raise RuntimeError(f"exhausted at {ctr[0]}")
        v = float(seq[ctr[0]])
        ctr[0] += 1
        return v

    try:
        with patch("numpy.random.rand", side_effect=shim):
            spm_MDP_VB_XXX(rdp, {})
        return int(ctr[0])
    except RuntimeError as exc:
        return f"fail@{ctr[0]}: {exc}"


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
    _coerce_rdp_t_scalar(rdp_mat)
    buf, manifest = load_validated_optim1full_ledger()
    seg1 = manifest.segment("nr_game_01")

    with optim1full_signoff_env(deadline_minutes="30"):
        mdp_py = load_mdp_from_mat(pre, "MDP_pre_active_inference")
        ne = load_ne_from_mat(pre, "Ne")
        c_val = atari_c_value()
        rdp_py = spm_set_goals(mdp_py, [2, 3], [c_val, -c_val])
        rdp_py = spm_set_costs(rdp_py, [2, 3], [c_val, -c_val])
        rdp_py = spm_mdp2rdp(rdp_py, 0, 1.0 / 256.0)
        rdp_py["T"] = float(int(256 / ne))
        _coerce_rdp_t_scalar(rdp_py)

        print("manifest nr_game_01 k=", seg1.k)
        py_draws = _vb_draws(rdp_py, buf, seg1.start, 65536)
        print("Python-assembled RDP:", py_draws)
        try:
            print("MATLAB-assembled RDP:", _vb_draws(rdp_mat, buf, seg1.start, 65536))
        except Exception as exc:
            print("MATLAB-assembled RDP: ERROR", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
