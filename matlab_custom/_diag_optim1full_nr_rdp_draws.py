#!/usr/bin/env python3
"""Diagnostic: NR game-1 RDP assembly + draw budget vs ledger segment."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

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


def _summ_rdp(rdp: object, label: str) -> None:
    m0 = rdp[0] if isinstance(rdp, list) else rdp
    nchild = len(m0.get("MDP", [])) if isinstance(m0.get("MDP"), list) else 0
    print(
        f"{label}: nm={len(rdp) if isinstance(rdp, list) else 1} "
        f"T={m0.get('T')} nchild={nchild}"
    )


def _vb_draws(rdp: object, buf: np.ndarray, start: int, allow: int) -> int:
    seq = buf[start : start + allow]
    ctr = [0]

    def shim(*_a: object, **_k: object) -> float:
        if ctr[0] >= len(seq):
            raise RuntimeError(f"exhausted at {ctr[0]}")
        v = float(seq[ctr[0]])
        ctr[0] += 1
        return v

    with patch("numpy.random.rand", side_effect=shim):
        spm_MDP_VB_XXX(rdp)
    return int(ctr[0])


def main() -> int:
    pre_mat = optim1full_mdp_pre_active_inference_mat()
    buf, manifest = load_validated_optim1full_ledger()
    seg1 = manifest.segment("nr_game_01")

    with optim1full_signoff_env(deadline_minutes="60"):
        mdp_in = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
        ne = load_ne_from_mat(pre_mat, "Ne")
        c_val = atari_c_value()
        rdp_py = spm_set_goals(mdp_in, [2, 3], [c_val, -c_val])
        rdp_py = spm_set_costs(rdp_py, [2, 3], [c_val, -c_val])
        rdp_py = spm_mdp2rdp(rdp_py, 0, 1.0 / 256.0)
        rdp_py["T"] = float(int(256 / ne))
        _summ_rdp(rdp_py, "py_asm")

        import matlab.engine

        repo = demo1_repo_root()
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, repo)
            p = str(pre_mat.resolve()).replace("\\", "/")
            eng.eval(f"load('{p}');", nargout=0)
            eng.eval(
                "C=32; NS=256; NT=256; "
                "RDP = spm_set_goals(MDP_pre_active_inference,[2,3],[C,-C]); "
                "RDP = spm_set_costs(RDP,[2,3],[C,-C]); "
                "RDP = spm_mdp2rdp(RDP,0,1/NS); "
                "RDP{1}.T = fix(NT/Ne);",
                nargout=0,
            )
            t_mat = float(np.asarray(eng.eval("RDP{1}.T")).reshape(-1)[0])
            nm = int(eng.eval("numel(RDP)"))
            nchild = int(eng.eval("numel(RDP{1}.MDP)"))
            print(f"mat_asm: nm={nm} T={t_mat} nchild={nchild}")
        finally:
            eng.quit()

        used = _vb_draws(rdp_py, buf, seg1.start, 65536)
        print(
            f"py_asm VB draws used={used} manifest_k={seg1.k} "
            f"ratio={used / seg1.k:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
