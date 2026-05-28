"""MATLAB spm_VBX on Python-saved compute-time child witness (Call 2)."""
from __future__ import annotations

import pickle
from pathlib import Path

import matlab.engine
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _cell_col(eng: matlab.engine.MatlabEngine, arrays: list[np.ndarray]) -> matlab.double:
    n = len(arrays)
    c = eng.cell(1, n)
    for i, arr in enumerate(arrays):
        col = np.asarray(arr, dtype=np.float64).reshape(-1, 1)
        c[i] = matlab.double(col.tolist())
    return c


def main() -> None:
    s = np.load(ROOT / "matlab_custom" / "probe_child_vbx_t1.npz", allow_pickle=True)
    Orow = [np.asarray(x, dtype=np.float64).reshape(-1, 1) for x in s["O_row"]]
    Prow = [np.asarray(x, dtype=np.float64).reshape(-1, 1) for x in s["P_row"]]
    Arow = [np.asarray(x, dtype=np.float64) for x in s["A_row"]]

    eng = matlab.engine.start_matlab()
    eng.cd(str(ROOT).replace("\\", "/"), nargout=0)
    eng.addpath(str(ROOT / "matlab_src" / "toolbox" / "DEM").replace("\\", "/"), nargout=0)
    eng.addpath("C:/Users/andre/Documents/MATLAB/spm-main", nargout=0)

    O = _cell_col(eng, Orow)
    P = _cell_col(eng, Prow)
    A = _cell_col(eng, Arow)
    idm = pickle.loads(bytes(s["id_snapshot"]))

    eng.eval(
        "S=load('tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_atari_call2_12F.mat','out_t1');",
        nargout=0,
    )
    eng.eval("mdp=S.out_t1.MDP.MDP; if iscell(mdp), mdp=mdp{1}; end", nargout=0)
    eng.eval("mdp=spm_MDP_checkX(mdp);", nargout=0)
  # Use Python-pickled id via recreating from mat checkX for now; compare struct A too
    idm = eng.eval("mdp.id", nargout=1)
    try:
        _, F_ws = eng.spm_VBX(O, P, A, idm, nargout=2)
        f_ws = float(F_ws)
    except Exception as exc:
        f_ws = float("nan")
        print(f"matlab_VBX_workspace_A_error={exc}")
    A_snap = eng.eval("mdp.A", nargout=1)
    _, F_snap = eng.spm_VBX(O, P, A_snap, idm, nargout=2)
    F_mat_child = float(eng.eval("mdp.F(1)", nargout=1))

    print(f"py_saved_F_vbx={float(np.asarray(s['F_vbx']).reshape(-1)[0]):.12g}")
    print(f"matlab_VBX_workspace_A={f_ws:.12g}")
    print(f"matlab_VBX_snap_mdp_A={float(F_snap):.12g}")
    print(f"mat_snap_child_F1={F_mat_child:.12g}")
    eng.quit()


if __name__ == "__main__":
    main()
