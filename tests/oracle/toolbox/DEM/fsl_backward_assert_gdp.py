"""FSL backward GDP / RGB / S parity helpers (Entry 2 sign-off)."""

from __future__ import annotations

from typing import Any

import numpy as np

from tests.helpers.compare import assert_matlab_match


def _pull_full_matrix(eng: Any, expr: str) -> np.ndarray:
    eng.eval(f"rgms_tmp_mx = full({expr});", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=float)


def assert_gdp_equal_eng(eng: Any, expr: str, gdp_py: dict[str, Any]) -> None:
    """Field-wise ``GDP`` compare (same contract as ``test_spm_MDP_pong._assert_mdp_matches``)."""
    Tm = np.atleast_2d(np.asarray(eng.eval(f"{expr}.T"), dtype=float))
    Tp = np.atleast_2d(np.asarray(gdp_py["T"], dtype=float))
    assert_matlab_match(Tm, Tp)
    N_md = np.atleast_2d(np.asarray(eng.eval(f"{expr}.N"), dtype=float))
    N_py = np.atleast_2d(np.asarray(gdp_py["N"], dtype=float))
    assert_matlab_match(N_md, N_py)
    assert_matlab_match(np.asarray(eng.eval(f"{expr}.U"), dtype=float), gdp_py["U"])

    n_a = int(np.asarray(eng.eval(f"numel({expr}.A)"), dtype=int).item())
    assert n_a == len(gdp_py["A"])
    for g in range(n_a):
        Am = np.asarray(eng.eval(f"full({expr}.A{{{g + 1}}})"), dtype=float)
        Ap = np.asarray(gdp_py["A"][g], dtype=float)
        assert_matlab_match(Am, Ap)

    n_b = int(np.asarray(eng.eval(f"numel({expr}.B)"), dtype=int).item())
    assert n_b == len(gdp_py["B"])
    for f in range(n_b):
        Bm = np.asarray(eng.eval(f"full({expr}.B{{{f + 1}}})"), dtype=float)
        Bp = np.asarray(gdp_py["B"][f], dtype=float)
        assert_matlab_match(Bm, Bp)

    n_c = int(np.asarray(eng.eval(f"numel({expr}.C)"), dtype=int).item())
    for g in range(n_c):
        Cm = np.asarray(eng.eval(f"{expr}.C{{{g + 1}}}"), dtype=float)
        assert_matlab_match(Cm, gdp_py["C"][g])

    n_d = int(np.asarray(eng.eval(f"numel({expr}.D)"), dtype=int).item())
    for f in range(n_d):
        Dm = _pull_full_matrix(eng, f"{expr}.D{{{f + 1}}}")
        Dp = gdp_py["D"][f]
        if hasattr(Dp, "toarray"):
            Dp = Dp.toarray()
        np.testing.assert_allclose(Dm, np.asarray(Dp, dtype=float), rtol=1e-7, atol=1e-12)

    n_e = int(np.asarray(eng.eval(f"numel({expr}.E)"), dtype=int).item())
    for f in range(n_e):
        Em = _pull_full_matrix(eng, f"{expr}.E{{{f + 1}}}")
        Ep = gdp_py["E"][f]
        if hasattr(Ep, "toarray"):
            Ep = Ep.toarray()
        np.testing.assert_allclose(Em, np.asarray(Ep, dtype=float), rtol=1e-7, atol=1e-12)

    n_h = int(np.asarray(eng.eval(f"numel({expr}.H)"), dtype=int).item())
    for f in range(n_h):
        Hm = np.asarray(eng.eval(f"{expr}.H{{{f + 1}}}"), dtype=float)
        Hp = np.asarray(gdp_py["H"][f], dtype=float)
        assert_matlab_match(Hm, Hp)

    id_m_a_num = int(np.asarray(eng.eval(f"numel({expr}.id.A)"), dtype=int).item())
    assert id_m_a_num == len(gdp_py["id"]["A"])
    for g in range(id_m_a_num):
        gm = np.atleast_2d(np.asarray(eng.eval(f"{expr}.id.A{{{g + 1}}}"), dtype=float))
        gp = np.atleast_2d(np.asarray(gdp_py["id"]["A"][g], dtype=float))
        assert_matlab_match(gm, gp)

    for fname in ("reward", "contraint", "control"):
        flg = np.asarray(eng.eval(f"isfield({expr}.id,'{fname}')"), dtype=float).ravel()
        if flg.size == 0 or float(flg.flat[0]) == 0:
            continue
        vm = np.asarray(eng.eval(f"{expr}.id.{fname}"), dtype=float)
        vp = np.asarray(gdp_py["id"][fname], dtype=float)
        assert_matlab_match(vm, vp)


def assert_rgb_g_equal_eng(eng: Any, expr: str, rgb_py: dict[str, Any]) -> None:
    """Compare ``RGB.N`` and ``RGB.G`` (skip ``RGB.V`` — viz deferred per pong oracle policy)."""
    Nm = np.asarray(eng.eval(f"{expr}.N"), dtype=float).ravel()
    Np = np.asarray(rgb_py["N"], dtype=float).ravel()
    assert_matlab_match(Nm.reshape(1, -1), Np.reshape(1, -1))
    nr = int(np.asarray(eng.eval(f"size({expr}.G,1)"), dtype=int).item())
    nc = int(np.asarray(eng.eval(f"size({expr}.G,2)"), dtype=int).item())
    for i in range(nr):
        for j in range(nc):
            Gm = np.asarray(eng.eval(f"{expr}.G{{{i + 1},{j + 1}}}"), dtype=float)
            Gp = np.asarray(rgb_py["G"][i][j], dtype=float)
            assert_matlab_match(Gm, Gp)


def assert_entry2_bundle_equal_eng(eng: Any, blob: dict[str, Any]) -> None:
    """Compare Python Entry **2** post blob vs ``GDP_post_entry2`` / ``RGB_post_entry2`` / ``S_post_entry2``."""
    assert_gdp_equal_eng(eng, "GDP_post_entry2", blob["gdp"])
    assert_rgb_g_equal_eng(eng, "RGB_post_entry2", blob["rgb"])
    assert_matlab_match(
        np.asarray(eng.eval("S_post_entry2"), dtype=np.float64),
        np.asarray(blob["S"], dtype=np.float64),
    )
    assert_matlab_match(
        np.asarray(eng.eval("hid_post_entry2"), dtype=np.float64),
        np.asarray(blob["hid"], dtype=np.float64),
    )
    assert_matlab_match(
        np.asarray(eng.eval("cid_post_entry2"), dtype=np.float64),
        np.asarray(blob["cid"], dtype=np.float64),
    )
    assert_matlab_match(
        np.asarray(eng.eval("con_post_entry2"), dtype=np.float64),
        np.asarray(blob["con"], dtype=np.float64),
    )
