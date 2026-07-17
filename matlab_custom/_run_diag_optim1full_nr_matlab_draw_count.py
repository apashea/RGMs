#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import matlab.engine

from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine


def main() -> int:
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        eng.cd(str(_REPO), nargout=0)
        fsl = str((_REPO / "matlab_custom" / "fsl_backward").resolve()).replace("\\", "/")
        fix = str((_REPO / "tests" / "demo1" / "optim1" / "fixtures").resolve()).replace("\\", "/")
        pre = str((_REPO / "tests" / "demo1" / "optim1" / "fixtures" / "DEMAtariIII_optim1full_MDP_pre_active_inference.mat").resolve()).replace("\\", "/")
        eng.addpath(fsl, nargout=0)
        eng.eval(
            f"load('{pre}','MDP_pre_active_inference','Ne'); "
            "C=32; NS=256; NT=256; "
            "rgms_fsl_rand_log_begin(); "
            "i0=rgms_fsl_rand_log_count(); "
            "RDP=spm_set_goals(MDP_pre_active_inference,[2,3],[C,-C]); "
            "RDP=spm_set_costs(RDP,[2,3],[C,-C]); "
            "RDP=spm_mdp2rdp(RDP,0,1/NS); "
            "RDP.T=fix(NT/Ne); "
            "OPTIONS=struct('O',1,'Y',1); "
            "PDP=spm_MDP_VB_XXX(RDP,OPTIONS,false,false); "
            "k=rgms_fsl_rand_log_count()-i0; "
            "fprintf('[diag] MATLAB NR game1 VB scalar rand count k=%d T=%d Ne=%d\\n',k,RDP.T,Ne);",
            nargout=0,
        )
    finally:
        eng.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
