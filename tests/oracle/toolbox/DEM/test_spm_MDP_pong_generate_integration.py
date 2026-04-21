"""Integration oracle: spm_MDP_pong → spm_MDP_generate (structure-learning chain).

``spm_MDP_generate`` calls ``spm_MDP_checkX`` internally (same as MATLAB line 48).
This test validates GDP built by Pong with ``Na=true`` through generate with small ``T``.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
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


def _pull_cell_matrix(eng, expr: str) -> np.ndarray:
    eng.eval(f"rgms_tmp_mx = {expr};", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=float)


def _matlab_rand_stream_after_reset(dem_eng, n: int) -> list:
    dem_eng.eval(f"rng(0); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(dem_eng.eval("rgms_rand_buf"), dtype=float).ravel().tolist()


def test_pong_na_true_then_generate_small_T_oracle(dem_eng):
    """
    GDP from ``spm_MDP_pong(4,4,1,1,0)``, ``T=4``, ``tau=1`` — compare PDP vs Python.

    ``Np=0`` so Pong uses no ``rand``; replay aligns ``spm_MDP_generate`` draws only.
    """
    dem_eng.eval(
        "rng(0); "
        "[GDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,1,0); "
        "GDP.T = 4; "
        "GDP.tau = 1; "
        "rgms_pdp = spm_MDP_generate(GDP);",
        nargout=0,
    )

    s_m = np.asarray(dem_eng.eval("rgms_pdp.s"), dtype=float)
    o_m = np.asarray(dem_eng.eval("rgms_pdp.o"), dtype=float)
    u_m = np.asarray(dem_eng.eval("rgms_pdp.u"), dtype=float)

    ng = int(np.asarray(dem_eng.eval("numel(rgms_pdp.A)"), dtype=int).item())
    t_steps = int(np.asarray(dem_eng.eval("rgms_pdp.T"), dtype=int).item())

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 8192)

    gdp = spm_MDP_pong(4, 4, 1, 1, 0)[0]
    gdp["T"] = 4.0
    gdp["tau"] = 1.0

    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp_py = spm_MDP_generate(gdp)

    assert_matlab_match(s_m, pdp_py["s"])
    assert_matlab_match(o_m, pdp_py["o"])
    assert_matlab_match(u_m, pdp_py["u"])

    for g in range(ng):
        for tt in range(t_steps):
            om = _pull_cell_matrix(
                dem_eng,
                f"full(rgms_pdp.O{{{int(g) + 1},{int(tt) + 1}}})",
            )
            py_col = np.asarray(pdp_py["O"][g][tt], dtype=float)
            assert_matlab_match(om, py_col)
