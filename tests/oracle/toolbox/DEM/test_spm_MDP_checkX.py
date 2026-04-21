"""Oracle tests: spm_MDP_checkX.m vs python_src.toolbox.DEM.spm_MDP_checkX."""

import copy
from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    return eng


def _pull_cell_matrix(eng, expr: str) -> np.ndarray:
    # MATLAB identifiers must start with a letter; leading '_' is invalid.
    eng.eval("rgms_tmp_mx = " + expr + ";", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=float)


def test_spm_MDP_checkX_single_modality_two_factors_oracle(dem_eng):
    dem_eng.eval(
        "m_in = struct(); "
        "m_in.A = {ones(3,2,4)}; "
        "m_in.B = {ones(2,2,2)*0.25, ones(4,4,1)*0.25}; "
        "m_out = spm_MDP_checkX(m_in);",
        nargout=0,
    )
    m_in = {
        "A": [np.ones((3, 2, 4), dtype=np.float64)],
        "B": [
            np.ones((2, 2, 2), dtype=np.float64) * 0.25,
            np.ones((4, 4, 1), dtype=np.float64) * 0.25,
        ],
    }
    m_out = spm_MDP_checkX(copy.deepcopy(m_in))

    a_m = _pull_cell_matrix(dem_eng, "full(m_out.A{1})")
    a_p = m_out["A"][0]
    assert_matlab_match(a_m, a_p)

    b1_m = _pull_cell_matrix(dem_eng, "full(m_out.B{1})")
    b1_p = m_out["B"][0]
    assert_matlab_match(b1_m, b1_p)

    b2_m = _pull_cell_matrix(dem_eng, "full(m_out.B{2})")
    b2_p = m_out["B"][1]
    assert_matlab_match(b2_m, b2_p)

    u_m = np.asarray(dem_eng.eval("m_out.U"), dtype=float)
    assert_matlab_match(u_m, m_out["U"])

    c_m = _pull_cell_matrix(dem_eng, "full(m_out.C{1})")
    assert_matlab_match(c_m, m_out["C"][0])

    d1_m = _pull_cell_matrix(dem_eng, "full(m_out.D{1})")
    assert_matlab_match(d1_m, m_out["D"][0])
    d2_m = _pull_cell_matrix(dem_eng, "full(m_out.D{2})")
    assert_matlab_match(d2_m, m_out["D"][1])

    e1_m = _pull_cell_matrix(dem_eng, "full(m_out.E{1})")
    assert_matlab_match(e1_m, m_out["E"][0])

    g1_m = _pull_cell_matrix(dem_eng, "m_out.id.g{1}")
    g1_p = m_out["id"]["g"][0]
    # MATLAB Engine often returns a 1×1 matrix as a 0-d scalar; normalize for compare.
    assert_matlab_match(np.atleast_2d(g1_m), np.atleast_2d(g1_p))

    ida_m = _pull_cell_matrix(dem_eng, "m_out.id.A{1}")
    ida_p = m_out["id"]["A"][0]
    assert_matlab_match(ida_m, ida_p)


def test_spm_MDP_checkX_A_from_a_oracle(dem_eng):
    dem_eng.eval(
        "m2_in = struct(); m2_in.a = {ones(2,3)*0.5}; "
        "m2_in.B = {ones(3,3,1)*0.33}; "
        "m2_out = spm_MDP_checkX(m2_in);",
        nargout=0,
    )
    m2_in = {
        "a": [np.ones((2, 3), dtype=np.float64) * 0.5],
        "B": [np.ones((3, 3, 1), dtype=np.float64) * 0.33],
    }
    m2_out = spm_MDP_checkX(copy.deepcopy(m2_in))
    a_m = _pull_cell_matrix(dem_eng, "full(m2_out.A{1})")
    assert_matlab_match(a_m, m2_out["A"][0])


def test_spm_MDP_checkX_two_trial_grid_oracle(dem_eng):
    dem_eng.eval(
        "t1.A = {ones(2,2)}; t1.B = {ones(2,2,1)*0.4}; "
        "t2.A = {ones(2,2)*2}; t2.B = {ones(2,2,1)*0.6}; "
        "G_in = [t1; t2]; "
        "G_out = spm_MDP_checkX(G_in);",
        nargout=0,
    )
    t1 = {
        "A": [np.ones((2, 2), dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.4],
    }
    t2 = {
        "A": [np.ones((2, 2), dtype=np.float64) * 2.0],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.6],
    }
    g_in = [[copy.deepcopy(t1)], [copy.deepcopy(t2)]]
    g_out = spm_MDP_checkX(copy.deepcopy(g_in))

    a_top_m = _pull_cell_matrix(dem_eng, "full(G_out(1,1).A{1})")
    assert_matlab_match(a_top_m, g_out[0][0]["A"][0])
    a_bot_m = _pull_cell_matrix(dem_eng, "full(G_out(2,1).A{1})")
    assert_matlab_match(a_bot_m, g_out[1][0]["A"][0])
