"""Oracle: ``matlab_src/toolbox/DEM/spm_forwards.m`` vs ``python_src.toolbox.DEM.spm_forwards``."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import python_src.toolbox.DEM.spm_forwards as forwards_mod
import python_src.spm_dot as spm_dot_mod
from python_src.toolbox.DEM.spm_forwards import spm_forwards
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    return eng


def test_spm_forwards_no_recursion_two_policies_one_factor_oracle(dem_eng) -> None:
    """
    ``t=1``, ``T=2``, ``N=1`` → no deep recursion (``t < N`` is false).

    One modality, one hidden factor, **2-D** ``A{1,1}`` (``No×Ns``), two policies on ``B``.
    ``O``, ``P``, ``A``, ``B`` are **saved in MATLAB before** ``spm_forwards`` so Python matches
    the same priors (``spm_VBX`` overwrites ``P`` in-place).
    """
    dem_eng.eval(
        "rng(4,'twister'); "
        "Nm = 1; Ng = 1; Nf = 1; Nk = 2; T = 2; "
        "O = cell(Nm,Ng,T); "
        "O{1,1,1} = rand(6,1); O{1,1,1} = O{1,1,1}/sum(O{1,1,1}); O{1,1,2} = O{1,1,1}; "
        "P = cell(Nm,Nf,T); "
        "P{1,1,1} = rand(5,1); P{1,1,1} = P{1,1,1}/sum(P{1,1,1}); P{1,1,2} = P{1,1,1}; "
        "A = cell(Nm,Ng); A{1,1} = rand(6,5); A{1,1} = A{1,1}.*(1./sum(A{1,1},1)); "
        "B = cell(Nm,Nf,Nk); "
        "B{1,1,1} = rand(5,5); B{1,1,1} = B{1,1,1}.*(1./sum(B{1,1,1},1)); "
        "B{1,1,2} = rand(5,5); B{1,1,2} = B{1,1,2}.*(1./sum(B{1,1,2},1)); "
        "C = cell(Nm,Ng); C{1,1} = []; "
        "H = cell(Nm,Nf); H{1,1} = []; "
        "K = cell(Nm,Ng); K{1,1} = []; "
        "W = cell(Nm,Ng); W{1,1} = []; "
        "I = cell(Nm,Nf,Nk); I{1,1,1} = []; I{1,1,2} = []; "
        "id = cell(Nm,1); id{1} = struct; id{1}.g = {1}; id{1}.A = {1}; "
        "id{1}.fp = []; id{1}.fu = 1; id{1}.iH = []; id{1}.iI = []; "
        "id{1}.C = cell(Ng,1); id{1}.C{1} = []; "
        "pA = cell(Nm,1); pA{1} = cell(Ng,1); pA{1}{1} = []; "
        "O_py_in = O{1,1,1}; P_py_in = P{1,1,1}; A_py_in = A{1,1}; "
        "B_py_in1 = B{1,1,1}; B_py_in2 = B{1,1,2}; "
        "[Gm,Pm,Fm,id,Pa] = spm_forwards(O,P,A,B,C,H,K,W,I,1,2,1,1,id,pA);",
        nargout=0,
    )
    Gm = np.asarray(dem_eng.eval("Gm"), dtype=np.float64)
    Fm = float(np.asarray(dem_eng.eval("Fm")).reshape(-1)[0])
    Pm_out = np.asarray(dem_eng.eval("Pm{1,1,1}"), dtype=np.float64)

    O1 = np.asarray(dem_eng.eval("O_py_in"), dtype=np.float64).reshape(-1, 1)
    P11 = np.asarray(dem_eng.eval("P_py_in"), dtype=np.float64).reshape(-1, 1)
    A11 = np.asarray(dem_eng.eval("A_py_in"), dtype=np.float64)
    assert A11.shape == (6, 5)
    B11 = np.asarray(dem_eng.eval("B_py_in1"), dtype=np.float64)
    B12 = np.asarray(dem_eng.eval("B_py_in2"), dtype=np.float64)

    O = [[ [O1.copy(), O1.copy()] ]]
    P = [[ [P11.copy(), P11.copy()] ]]
    A = [[A11]]
    B = [[ [B11, B12] ]]
    C = [[[]]]
    H = [[[]]]
    K = [[[]]]
    W = [[[]]]
    I = [[[np.zeros((0, 0)), np.zeros((0, 0))]]]
    id_py: dict = {
        "g": [1],
        "A": [1.0],
        "fp": np.array([], dtype=np.int64),
        "fu": np.array([1], dtype=np.int64),
        "iH": np.array([], dtype=np.int64),
        "iI": np.array([], dtype=np.int64),
        "C": [[]],
    }
    pA_py = [[None]]

    Gp, Pp, Fp, _, _ = spm_forwards(
        O,
        P,
        A,
        B,
        C,
        H,
        K,
        W,
        I,
        1,
        2,
        1,
        1,
        [id_py],
        pA_py,
        None,
    )

    assert_matlab_match(Gm, Gp, rtol=2e-3, atol=1e-8)
    assert abs(Fp - Fm) < 1e-6
    assert_matlab_match(Pm_out, Pp[0][0][0], rtol=1e-7, atol=1e-12)


def test_spm_induction_handles_empty_cid_without_unbound_d_flat() -> None:
    """
    Regression for Entry-12 blocker: ``id.cid = []`` must not leave ``d_flat`` unbound
    inside ``_spm_induction_vb``.
    """
    B = [[np.ones((2, 2), dtype=np.float64)]]
    H = [np.array([[0.5], [0.5]], dtype=np.float64)]
    Q = [np.array([[0.5], [0.5]], dtype=np.float64)]
    id_dict = {
        "hid": np.array([[1.0], [2.0]], dtype=np.float64),
        "cid": np.zeros((0, 0), dtype=np.float64),
    }
    R, r = forwards_mod._spm_induction_vb(B, H, Q, 2, id_dict)
    assert isinstance(r, np.ndarray)
    assert R is not None


def test_spm_forwards_accepts_vector_spm_dot_risk_term(monkeypatch) -> None:
    """Regression: ``spm_dot(R,Q(r))`` may be a vector; must not be forced through ``float(...)``."""
    O = [[[np.array([[0.5], [0.5]]), np.array([[0.5], [0.5]])]]]
    P = [[[np.array([[0.5], [0.5]]), np.array([[0.5], [0.5]])]]]
    A = [[np.eye(2, dtype=np.float64)]]
    B = [[[np.eye(2, dtype=np.float64), np.eye(2, dtype=np.float64)]]]
    C = [[[]]]
    H = [[[]]]
    K = [[[]]]
    W = [[[]]]
    I = [[[np.zeros((0, 0), dtype=np.float64), np.zeros((0, 0), dtype=np.float64)]]]
    id_py = [{
        "g": [np.array([1], dtype=np.int64), np.array([1], dtype=np.int64)],
        "A": [1],
        "fp": np.array([], dtype=np.int64),
        "fu": np.array([1], dtype=np.int64),
        "iH": np.array([], dtype=np.int64),
        "iI": np.array([], dtype=np.int64),
        "C": [[]],
    }]
    pA = [[[]]]

    monkeypatch.setattr(forwards_mod, "_spm_induction_vb", lambda *_a, **_k: (np.array([[1.0]]), np.array([1], dtype=np.int64)))
    real_dot = spm_dot_mod.spm_dot

    def _dot_proxy(X, x, i=None):
        if np.asarray(X).shape == (1, 1):
            return np.array([0.1, 0.2], dtype=np.float64)
        return real_dot(X, x, i)

    monkeypatch.setattr(forwards_mod, "spm_dot", _dot_proxy)
    G, *_ = spm_forwards(O, P, A, B, C, H, K, W, I, 1, 2, 1, 1, id_py, pA, None)
    assert np.asarray(G, dtype=np.float64).shape[0] == 2


def test_spm_induction_n_zero_returns_empty_without_index_error() -> None:
    """Regression: ``N=0`` must return empty constraints, not index into ``G[0,:]``."""
    B = [[np.eye(2, dtype=np.float64)]]
    H = [np.array([[0.5], [0.5]], dtype=np.float64)]
    Q = [np.array([[0.5], [0.5]], dtype=np.float64)]
    id_dict = {"hid": np.array([[1.0], [2.0]], dtype=np.float64)}
    R, r = forwards_mod._spm_induction_vb(B, H, Q, 0, id_dict)
    assert np.asarray(R).size == 0
    assert np.asarray(r, dtype=np.int64).size > 0
