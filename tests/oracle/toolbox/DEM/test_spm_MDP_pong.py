"""Oracle tests: spm_MDP_pong.m vs python_src.toolbox.DEM.spm_MDP_pong."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)
        eng.rmpath(str(dem_path), nargout=0)


def _matlab_rand_stream_after_reset(dem_eng, n: int = 64) -> list:
    dem_eng.eval(f"rng(0); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(dem_eng.eval("rgms_rand_buf"), dtype=float).ravel().tolist()


def _pull_full_matrix(eng, expr: str) -> np.ndarray:
    eng.eval(f"rgms_tmp_mx = full({expr});", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=float)


def test_spm_MDP_pong_small_grid_no_extra_modalities_oracle(dem_eng):
    """Nr=Nc=4, Nd=1, Na=0, Np=0 — deterministic core (no distractor rand).

    RGB block is not asserted here; see ``test_spm_MDP_pong_rgb_visualization_oracle``
    (skipped until viz parity is scheduled).
    """
    dem_eng.eval(
        "[MDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,0,0);",
        nargout=0,
    )

    out_py = spm_MDP_pong(4, 4, 1, 0, 0)

    hid_m = np.asarray(dem_eng.eval("hid"), dtype=float)
    cid_m = np.asarray(dem_eng.eval("cid"), dtype=float)
    con_m = np.asarray(dem_eng.eval("con"), dtype=float)
    nP_m = np.asarray(dem_eng.eval("nP"), dtype=float)

    assert_matlab_match(hid_m, out_py[1])
    assert_matlab_match(cid_m, out_py[2])
    assert_matlab_match(con_m, out_py[3])
    assert_matlab_match(
        np.atleast_2d(np.asarray(nP_m, dtype=float)),
        np.atleast_2d(np.asarray(out_py[5], dtype=float)),
    )

    _assert_mdp_matches(dem_eng, out_py[0])


@pytest.mark.skip(
    reason=(
        "Deferred: PNG/imread vs MATLAB `RGB.V` parity (viz / spm_O2rgb path). "
        "See notes\\andrew Python Matlab Translation Issues.md §spm_MDP_pong."
    )
)
def test_spm_MDP_pong_rgb_visualization_oracle(dem_eng):
    """Full RGB oracle (same grid as minimal core test); enable when tightening viz."""
    dem_eng.eval(
        "[MDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,0,0);",
        nargout=0,
    )
    out_py = spm_MDP_pong(4, 4, 1, 0, 0)
    _assert_rgb_matches(dem_eng, out_py[4])


def test_spm_MDP_pong_na_true_small_grid_oracle(dem_eng):
    """Na=true (snippet-style): reward / constraint / control modalities and ``id`` fields."""
    dem_eng.eval(
        "[MDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,1,0);",
        nargout=0,
    )

    out_py = spm_MDP_pong(4, 4, 1, 1, 0)

    hid_m = np.asarray(dem_eng.eval("hid"), dtype=float)
    cid_m = np.asarray(dem_eng.eval("cid"), dtype=float)
    con_m = np.asarray(dem_eng.eval("con"), dtype=float)
    nP_m = np.asarray(dem_eng.eval("nP"), dtype=float)

    assert_matlab_match(hid_m, out_py[1])
    assert_matlab_match(cid_m, out_py[2])
    assert_matlab_match(con_m, out_py[3])
    assert_matlab_match(
        np.atleast_2d(np.asarray(nP_m, dtype=float)),
        np.atleast_2d(np.asarray(out_py[5], dtype=float)),
    )

    _assert_mdp_matches(dem_eng, out_py[0])


@pytest.mark.slow
def test_spm_MDP_pong_na_true_snippet_branch_oracle(dem_eng):
    """Exact snippet branch pre-SL closure: ``spm_MDP_pong(12,9,4,1,0)``."""
    dem_eng.eval(
        "[MDP,hid,cid,con,RGB,nP] = spm_MDP_pong(12,9,4,1,0);",
        nargout=0,
    )

    out_py = spm_MDP_pong(12, 9, 4, 1, 0)

    hid_m = np.asarray(dem_eng.eval("hid"), dtype=float)
    cid_m = np.asarray(dem_eng.eval("cid"), dtype=float)
    con_m = np.asarray(dem_eng.eval("con"), dtype=float)
    nP_m = np.asarray(dem_eng.eval("nP"), dtype=float)

    assert_matlab_match(hid_m, out_py[1])
    assert_matlab_match(cid_m, out_py[2])
    assert_matlab_match(con_m, out_py[3])
    assert_matlab_match(
        np.atleast_2d(np.asarray(nP_m, dtype=float)),
        np.atleast_2d(np.asarray(out_py[5], dtype=float)),
    )

    _assert_mdp_matches(dem_eng, out_py[0])


def test_spm_MDP_pong_distractor_rand_replay_oracle(dem_eng):
    """Np=1 exercises rand; replay MATLAB rand stream in Python."""
    dem_eng.eval(
        "rng(0); "
        "[MDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,0,1);",
        nargout=0,
    )
    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 64)
    with patch("numpy.random.rand", side_effect=rand_seq):
        out_py = spm_MDP_pong(4, 4, 1, 0, 1)

    nP_m = np.atleast_2d(np.asarray(dem_eng.eval("nP"), dtype=float))
    assert_matlab_match(nP_m, np.atleast_2d(np.asarray(out_py[5], dtype=float)))
    _assert_mdp_matches(dem_eng, out_py[0])


def _assert_mdp_matches(eng, mdp_py: dict) -> None:
    Tm = np.atleast_2d(np.asarray(eng.eval("MDP.T"), dtype=float))
    Tp = np.atleast_2d(np.asarray(mdp_py["T"], dtype=float))
    assert_matlab_match(Tm, Tp)
    N_md = np.atleast_2d(np.asarray(eng.eval("MDP.N"), dtype=float))
    N_py = np.atleast_2d(np.asarray(mdp_py["N"], dtype=float))
    assert_matlab_match(N_md, N_py)
    assert_matlab_match(np.asarray(eng.eval("MDP.U"), dtype=float), mdp_py["U"])

    n_a = int(np.asarray(eng.eval("numel(MDP.A)"), dtype=int).item())
    assert n_a == len(mdp_py["A"])
    for g in range(n_a):
        Am = np.asarray(eng.eval(f"full(MDP.A{{{g + 1}}})"), dtype=float)
        Ap = np.asarray(mdp_py["A"][g], dtype=float)
        assert_matlab_match(Am, Ap)

    n_b = int(np.asarray(eng.eval("numel(MDP.B)"), dtype=int).item())
    assert n_b == len(mdp_py["B"])
    for f in range(n_b):
        Bm = np.asarray(eng.eval(f"full(MDP.B{{{f + 1}}})"), dtype=float)
        Bp = np.asarray(mdp_py["B"][f], dtype=float)
        assert_matlab_match(Bm, Bp)

    n_c = int(np.asarray(eng.eval("numel(MDP.C)"), dtype=int).item())
    for g in range(n_c):
        Cm = np.asarray(eng.eval(f"MDP.C{{{g + 1}}}"), dtype=float)
        assert_matlab_match(Cm, mdp_py["C"][g])

    n_d = int(np.asarray(eng.eval("numel(MDP.D)"), dtype=int).item())
    for f in range(n_d):
        Dm = _pull_full_matrix(eng, f"MDP.D{{{f + 1}}}")
        Dp = mdp_py["D"][f].toarray()
        np.testing.assert_allclose(Dm, Dp, rtol=1e-7, atol=1e-12)

    n_e = int(np.asarray(eng.eval("numel(MDP.E)"), dtype=int).item())
    for f in range(n_e):
        Em = _pull_full_matrix(eng, f"MDP.E{{{f + 1}}}")
        Ep = mdp_py["E"][f].toarray()
        np.testing.assert_allclose(Em, Ep, rtol=1e-7, atol=1e-12)

    n_h = int(np.asarray(eng.eval("numel(MDP.H)"), dtype=int).item())
    for f in range(n_h):
        Hm = np.asarray(eng.eval(f"MDP.H{{{f + 1}}}"), dtype=float)
        Hp = np.asarray(mdp_py["H"][f], dtype=float)
        assert_matlab_match(Hm, Hp)

    id_m_a_num = int(np.asarray(eng.eval("numel(MDP.id.A)"), dtype=int).item())
    assert id_m_a_num == len(mdp_py["id"]["A"])
    for g in range(id_m_a_num):
        gm = np.atleast_2d(np.asarray(eng.eval(f"MDP.id.A{{{g + 1}}}"), dtype=float))
        gp = np.atleast_2d(np.asarray(mdp_py["id"]["A"][g], dtype=float))
        assert_matlab_match(gm, gp)

    for fname in ("reward", "contraint", "control"):
        flg = np.asarray(eng.eval(f"isfield(MDP.id,'{fname}')"), dtype=float).ravel()
        if flg.size == 0 or float(flg.flat[0]) == 0:
            continue
        vm = np.asarray(eng.eval(f"MDP.id.{fname}"), dtype=float)
        vp = np.asarray(mdp_py["id"][fname], dtype=float)
        assert_matlab_match(vm, vp)


def _assert_rgb_matches(eng, rgb_py: dict) -> None:
    Nm = np.asarray(eng.eval("RGB.N"), dtype=float).ravel()
    Np = np.asarray(rgb_py["N"], dtype=float).ravel()
    assert_matlab_match(Nm.reshape(1, -1), Np.reshape(1, -1))

    eng.eval("rgms_Vpull = double(RGB.V{1,1});", nargout=0)
    Vm = np.asarray(eng.eval("rgms_Vpull"), dtype=float)
    Vp = np.asarray(rgb_py["V"][0][0], dtype=float)
    np.testing.assert_allclose(Vm, Vp, rtol=0.0, atol=155.0)

    nr = int(np.asarray(eng.eval("size(RGB.G,1)"), dtype=int).item())
    nc = int(np.asarray(eng.eval("size(RGB.G,2)"), dtype=int).item())
    for i in range(nr):
        for j in range(nc):
            Gm = np.asarray(eng.eval(f"RGB.G{{{i + 1},{j + 1}}}"), dtype=float)
            Gp = np.asarray(rgb_py["G"][i][j], dtype=float)
            assert_matlab_match(Gm, Gp)
