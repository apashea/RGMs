"""Oracle: ``spm_O2rgb.m`` vs ``python_src.toolbox.DEM.spm_O2rgb``."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_O2rgb import spm_O2rgb


@pytest.fixture
def dem_eng_o2rgb(eng):
    """DEM cwd for ``spm_MDP_pong`` / ``spm_MDP_generate`` / ``spm_O2rgb``."""
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)
        eng.rmpath(str(dem_path), nargout=0)


def _pull_o_col(eng, pdp_name: str, t_1: int) -> list:
    no = int(np.asarray(eng.eval("size(" + pdp_name + ".O,1)"), dtype=int).item())
    col = []
    for g in range(1, no + 1):
        expr = "full(" + pdp_name + ".O{" + str(g) + "," + str(t_1) + "})"
        eng.eval("rgms_tmp_mx = " + expr + ";", nargout=0)
        col.append(np.asarray(eng.eval("rgms_tmp_mx"), dtype=np.float64))
    return col


def _pull_rgb_dict(eng, rgb_name: str = "RGB") -> dict:
    n = np.asarray(eng.eval(rgb_name + ".N"), dtype=np.float64).ravel()
    nr = int(np.asarray(eng.eval("size(" + rgb_name + ".G,1)"), dtype=int).item())
    nc = int(np.asarray(eng.eval("size(" + rgb_name + ".G,2)"), dtype=int).item())
    g_py: list = []
    v_py: list = []
    for i in range(1, nr + 1):
        gi: list = []
        vi: list = []
        for j in range(1, nc + 1):
            eng.eval(
                "rgms_tmp_mx = " + rgb_name + ".G{" + str(i) + "," + str(j) + "};",
                nargout=0,
            )
            gi.append(np.asarray(eng.eval("rgms_tmp_mx"), dtype=np.float64))
            eng.eval(
                "rgms_tmp_mx = " + rgb_name + ".V{" + str(i) + "," + str(j) + "};",
                nargout=0,
            )
            vi.append(np.asarray(eng.eval("rgms_tmp_mx"), dtype=np.float64))
        g_py.append(gi)
        v_py.append(vi)
    return {"N": n, "G": g_py, "V": v_py}


def test_spm_O2rgb_pdp_column_oracle(dem_eng_o2rgb):
    """T10 / §12.5: ``spm_O2rgb(PDP.O(:,1),RGB)`` after Pong→generate (MATLAB reference ``O``/``RGB``)."""
    eng = dem_eng_o2rgb
    eng.eval(
        "rng(0,'twister'); "
        "[GDP_o2,hid,cid,con,RGB_o2,nP] = spm_MDP_pong(4,4,1,1,0); "
        "GDP_o2.T = 1; GDP_o2.tau = 1; "
        "PDP_o2 = spm_MDP_generate(GDP_o2);",
        nargout=0,
    )
    eng.eval("I_m = spm_O2rgb(PDP_o2.O(:,1),RGB_o2);", nargout=0)
    i_m = np.asarray(eng.eval("I_m"), dtype=np.uint8)

    o_col = _pull_o_col(eng, "PDP_o2", 1)
    rgb = _pull_rgb_dict(eng, "RGB_o2")
    i_p = spm_O2rgb(o_col, rgb)
    np.testing.assert_array_equal(i_m, i_p)
