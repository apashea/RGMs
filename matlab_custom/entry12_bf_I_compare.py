"""Compare Bf and backwards-I column for frozen goal 20 (hid col index 20, 0-based)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.spm_kron import spm_kron

_INP = ROOT / "matlab_custom" / "entry12_12f_induction_inputs.mat"
_OUT = ROOT / "matlab_custom" / "entry12_bf_I_compare.json"
_GOAL_COL = 20  # 0-based hid column (Python picked)


def _py_goal_I() -> dict:
    S = loadmat(str(_INP), squeeze_me=False)
    B = S["B"]
    Q = S["Q"]
    bp = [[B[0, f, k] for k in range(B.shape[2])] for f in range(B.shape[1])]
    hid = np.asarray(S["id_hid"], dtype=np.float64).reshape(1, -1, order="F")
    N = int(np.asarray(S["N"]).reshape(-1)[0])
    N = min(N, 64)
    u = 1.0 / 32.0
    acc = None
    for k in range(len(bp[0])):
        thr = np.asarray(bp[0][k], dtype=np.float64) > u
        acc = thr if acc is None else (acc | thr)
    Bf = spm_kron(acc, sparse.csr_matrix([[1.0]]))
    Q0 = np.asarray(Q[0, 0], dtype=np.float64).reshape(-1, 1, order="F")
    Qf = spm_kron(sparse.csr_matrix(Q0), sparse.csr_matrix([[1.0]]))
    bf_dense = Bf.toarray(order="F")
    L = bf_dense.shape[0]
    hidx = int(hid[0, _GOAL_COL])
    hvec = np.zeros((L, 1), dtype=bool)
    hvec[hidx - 1, 0] = True
    I = spm_kron(hvec, np.array([[True]], dtype=bool)).toarray().astype(bool).ravel(order="F")
    I_big = np.zeros((L, N + 1), dtype=bool)
    I_big[:, 0] = I
    for n in range(N):
        prev = I_big[:, n]
        rows = np.flatnonzero(prev)
        if rows.size == 0:
            break
        sub = Bf[rows, :]
        I_big[:, n + 1] = np.asarray(sub.sum(axis=0) > 0).ravel()
    qf = Qf.toarray(order="F").ravel().reshape(-1, 1)
    Gcol = (I_big.astype(np.float64).T @ qf).ravel(order="F")
    Gcol[0] = 0.0
    nmx = int(np.argmax(Gcol))
    return {
        "Bf_nnz": int(Bf.nnz),
        "Qf_shape": list(Qf.shape),
        "I_nnz_by_col": [int(np.count_nonzero(I_big[:, c])) for c in range(min(8, I_big.shape[1]))],
        "Gcol_argmax": nmx,
        "P_nz_at_argmax": np.flatnonzero(I_big[:, nmx] > 0).tolist()[:12],
    }


def _mat_goal_I() -> dict:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        mc = str(ROOT / "matlab_custom" / "entry12").replace("\\", "/")
        ms = str(ROOT / "matlab_src").replace("\\", "/")
        eng.addpath(mc, nargout=0)
        eng.eval(f"addpath(genpath('{ms}'));", nargout=0)
        gc = _GOAL_COL + 1
        eng.eval(f"out = entry12_bf_I_goal_compare({gc});", nargout=0)
        out = {}
        for k in ("Bf_nnz", "Gcol_argmax"):
            out[k] = int(np.asarray(eng.eval(f"out.{k}", nargout=1)).reshape(-1)[0])
        out["Qf_shape"] = np.atleast_1d(np.asarray(eng.eval("out.Qf_shape", nargout=1))).astype(int).tolist()
        out["P_nz_at_argmax"] = np.atleast_1d(np.asarray(eng.eval("out.P_nz_at_argmax", nargout=1))).astype(int).tolist()
        return out
    finally:
        eng.quit()


def main() -> None:
    payload = {"goal_col_0based": _GOAL_COL, "python": _py_goal_I(), "matlab": _mat_goal_I()}
    _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
