"""One-off: MATLAB spm_VBX on probe_child_vbx_t1.npz (Call 2 child t=1 compute lane)."""
from __future__ import annotations

import numpy as np
import matlab.engine
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    s = np.load(ROOT / "matlab_custom" / "probe_child_vbx_t1.npz", allow_pickle=True)
    eng = matlab.engine.start_matlab()
    eng.cd(str(ROOT).replace("\\", "/"), nargout=0)
    eng.addpath(str(ROOT / "matlab_src" / "toolbox" / "DEM").replace("\\", "/"), nargout=0)
    eng.addpath("C:/Users/andre/Documents/MATLAB/spm-main", nargout=0)

    ng = int(len(s["O_row"]))
    nf = int(len(s["P_row"]))
    O = eng.cell(1, ng)
    for g in range(ng):
        og = np.asarray(s["O_row"][g], dtype=np.float64).reshape(-1, 1)
        O[g] = matlab.double(og.tolist())
    P = eng.cell(1, nf)
    for f in range(nf):
        pf = np.asarray(s["P_row"][f], dtype=np.float64).reshape(-1, 1)
        P[f] = matlab.double(pf.tolist())

    eng.eval(
        "S=load('tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_atari_call2_12F.mat','out_t1');",
        nargout=0,
    )
    eng.eval("mdp=S.out_t1.MDP.MDP;", nargout=0)
    eng.eval("if iscell(mdp), mdp=mdp{1}; end", nargout=0)
    eng.eval("mdp=spm_MDP_checkX(mdp);", nargout=0)
    A = eng.eval("mdp.A", nargout=1)
    idm = eng.eval("mdp.id", nargout=1)
    _, Fm = eng.spm_VBX(O, P, A, idm, nargout=2)
    F_snap = float(eng.eval("mdp.F(1)", nargout=1))

    print(f"py_saved_F_vbx={float(np.asarray(s['F_vbx']).reshape(-1)[0]):.12g}")
    print(f"matlab_engine_F_vbx={float(Fm):.12g}")
    print(f"mat_snap_child_F_t1={F_snap:.12g}")
    eng.quit()


if __name__ == "__main__":
    main()
