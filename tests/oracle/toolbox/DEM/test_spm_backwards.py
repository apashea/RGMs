"""Oracle: ``matlab_src/toolbox/DEM/spm_backwards.m`` vs ``python_src.toolbox.DEM.spm_backwards``."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_backwards import spm_backwards
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    eng.addpath(r"c:\Users\andre\Documents\MATLAB\spm-main", nargout=0)
    return eng


def _pull_cell_O(dem_eng, name: str = "O") -> list:
    """``O{Nm,Ng,T}`` → ``[m][g][t]`` 0-based."""
    nm = int(np.asarray(dem_eng.eval(f"size({name},1)"), dtype=np.int64).reshape(-1)[0])
    ng = int(np.asarray(dem_eng.eval(f"size({name},2)"), dtype=np.int64).reshape(-1)[0])
    tt = int(np.asarray(dem_eng.eval(f"size({name},3)"), dtype=np.int64).reshape(-1)[0])
    out: list = []
    for m in range(1, nm + 1):
        gm: list = []
        for g in range(1, ng + 1):
            ts: list = []
            for t in range(1, tt + 1):
                ts.append(
                    np.asarray(dem_eng.eval(f"{name}{{{m},{g},{t}}}"), dtype=np.float64).reshape(
                        -1, 1, order="F"
                    )
                )
            gm.append(ts)
        out.append(gm)
    return out


def _pull_cell_QP(dem_eng, name: str) -> list:
    """``X{Nm,Nf,T}`` → ``[m][f][t]``."""
    nm = int(np.asarray(dem_eng.eval(f"size({name},1)"), dtype=np.int64).reshape(-1)[0])
    nf = int(np.asarray(dem_eng.eval(f"size({name},2)"), dtype=np.int64).reshape(-1)[0])
    tt = int(np.asarray(dem_eng.eval(f"size({name},3)"), dtype=np.int64).reshape(-1)[0])
    out: list = []
    for m in range(1, nm + 1):
        fm: list = []
        for f in range(1, nf + 1):
            ts: list = []
            for t in range(1, tt + 1):
                ts.append(
                    np.asarray(dem_eng.eval(f"{name}{{{m},{f},{t}}}"), dtype=np.float64).reshape(
                        -1, 1, order="F"
                    )
                )
            fm.append(ts)
        out.append(fm)
    return out


def _pull_cell_DE(dem_eng, name: str) -> list:
    nm = int(np.asarray(dem_eng.eval(f"size({name},1)"), dtype=np.int64).reshape(-1)[0])
    nf = int(np.asarray(dem_eng.eval(f"size({name},2)"), dtype=np.int64).reshape(-1)[0])
    out: list = []
    for m in range(1, nm + 1):
        row: list = []
        for f in range(1, nf + 1):
            row.append(
                np.asarray(dem_eng.eval(f"{name}{{{m},{f}}}"), dtype=np.float64).reshape(-1, 1, order="F")
            )
        out.append(row)
    return out


def _pull_pa(dem_eng, name: str = "pa") -> list:
    nm = int(np.asarray(dem_eng.eval(f"size({name},1)"), dtype=np.int64).reshape(-1)[0])
    ng = int(np.asarray(dem_eng.eval(f"size({name},2)"), dtype=np.int64).reshape(-1)[0])
    out: list = []
    for m in range(1, nm + 1):
        gm: list = []
        for g in range(1, ng + 1):
            gm.append(np.asarray(dem_eng.eval(f"{name}{{{m},{g}}}"), dtype=np.float64))
        out.append(gm)
    return out


def _pull_pb(dem_eng, name: str = "pb") -> list:
    nm = int(np.asarray(dem_eng.eval(f"size({name},1)"), dtype=np.int64).reshape(-1)[0])
    nf = int(np.asarray(dem_eng.eval(f"size({name},2)"), dtype=np.int64).reshape(-1)[0])
    out: list = []
    for m in range(1, nm + 1):
        fm: list = []
        for f in range(1, nf + 1):
            fm.append(np.asarray(dem_eng.eval(f"{name}{{{m},{f}}}"), dtype=np.float64))
        out.append(fm)
    return out


def test_spm_backwards_nm1_one_factor_T2_oracle(dem_eng) -> None:
    """Minimal grid (``Nm=1``, ``Nf=1``, ``T=2``, ``Ng=1``) — dependent factors."""
    stmts = [
        "rng(1,'twister');",
        "Nm = 1; Ng = 1; Nf = 1; T = 2;",
        "O = cell(Nm,Ng,T);",
        "for t=1:T, O{1,1,t} = rand(6,1); O{1,1,t} = O{1,1,t}/sum(O{1,1,t}); end",
        "Q = cell(Nm,Nf,T);",
        "for t=1:T, Q{1,1,t} = rand(5,1); Q{1,1,t} = Q{1,1,t}/sum(Q{1,1,t}); end",
        "P = cell(Nm,Nf,T);",
        "for t=1:T, P{1,1,t} = rand(4,1); P{1,1,t} = P{1,1,t}/sum(P{1,1,t}); end",
        "D = cell(Nm,Nf); D{1,1} = rand(5,1); D{1,1} = D{1,1}/sum(D{1,1});",
        "E = cell(Nm,Nf); E{1,1} = rand(4,1); E{1,1} = E{1,1}/sum(E{1,1});",
        "pa = cell(Nm,Ng); pa{1,1} = rand(6,5)*512;",
        "pb = cell(Nm,Nf); pb{1,1} = rand(5,5,4)*512;",
        "U = cell(Nm,1); U{1} = [1];",
        "id = cell(Nm,1); id{1}.g = {1}; id{1}.A = {1};",
        "O0 = O; P0 = P; Q0 = Q; D0 = D; E0 = E; pa0 = pa; pb0 = pb;",
        "[Qm,Pm,qa_m,qb_m,Fm] = spm_backwards(O,P,Q,D,E,pa,pb,U,1,id);",
    ]
    for line in stmts:
        dem_eng.eval(line, nargout=0)

    F_mat = np.asarray(dem_eng.eval("double(Fm)"), dtype=np.float64).ravel()
    Q11_mat = np.asarray(dem_eng.eval("Qm{1,1,1}"), dtype=np.float64).reshape(-1, 1, order="F")

    O_py = _pull_cell_O(dem_eng, "O0")
    Q_py = _pull_cell_QP(dem_eng, "Q0")
    P_py = _pull_cell_QP(dem_eng, "P0")
    D_py = _pull_cell_DE(dem_eng, "D0")
    E_py = _pull_cell_DE(dem_eng, "E0")
    pa_py = _pull_pa(dem_eng, "pa0")
    pb_py = _pull_pb(dem_eng, "pb0")
    U_py = [np.asarray(dem_eng.eval("double(U{1})"), dtype=np.float64).reshape(-1)]
    id_py = [{"g": [1], "A": [1]}]

    Q_out, _P_out, _qa, _qb, F_py = spm_backwards(
        O_py, P_py, Q_py, D_py, E_py, pa_py, pb_py, U_py, 1, id_py
    )

    assert_matlab_match(F_mat, F_py, rtol=1e-5, atol=1e-8)
    assert_matlab_match(Q11_mat, Q_out[0][0][0], rtol=1e-5, atol=1e-8)


def test_spm_backwards_smoke_runs_without_matlab() -> None:
    """Lightweight shape/runtime smoke (no Engine): single factor, T=2."""
    np.random.seed(0)
    Ns, No, Nu, T = 4, 5, 3, 2
    O = [[[np.random.rand(No, 1) for _ in range(T)] for _ in range(1)] for _ in range(1)]
    for t in range(T):
        O[0][0][t] = O[0][0][t] / np.sum(O[0][0][t])
    Q = [[[np.random.rand(Ns, 1) for _ in range(T)] for _ in range(1)] for _ in range(1)]
    for t in range(T):
        Q[0][0][t] = Q[0][0][t] / np.sum(Q[0][0][t])
    P = [[[np.random.rand(Nu, 1) for _ in range(T)] for _ in range(1)] for _ in range(1)]
    for t in range(T):
        P[0][0][t] = P[0][0][t] / np.sum(P[0][0][t])
    D = [[np.random.rand(Ns, 1)]]
    D[0][0] = D[0][0] / np.sum(D[0][0])
    E = [[np.random.rand(Nu, 1)]]
    E[0][0] = E[0][0] / np.sum(E[0][0])
    pa = [[np.random.rand(No, Ns) * 512]]
    pb = [[np.random.rand(Ns, Ns, Nu) * 512]]
    U = [np.array([1.0], dtype=np.float64)]
    id_list = [{"g": [1], "A": [1]}]
    _Q, _P, _qa, _qb, F = spm_backwards(O, P, Q, D, E, pa, pb, U, 1, id_list)
    assert F.shape == (T,)
    assert np.all(np.isfinite(F))
