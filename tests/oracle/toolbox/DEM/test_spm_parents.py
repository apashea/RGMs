"""Oracle tests: spm_parents.m vs python_src.toolbox.DEM.spm_parents."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_parents import spm_parents
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    return eng


def test_spm_parents_state_independent_oracle(dem_eng):
    dem_eng.eval(
        "id_si = struct('A',{{[7 8 9]}}); [j_si,i_si] = spm_parents(id_si, 1, 0);",
        nargout=0,
    )
    j_m = dem_eng.eval("j_si")
    i_m = dem_eng.eval("i_si")
    id_py = {"A": [np.array([[7.0, 8.0, 9.0]])]}
    j_p, i_p = spm_parents(id_py, 1, 0.0)
    assert_matlab_match(j_m, j_p)
    assert float(np.asarray(i_m, dtype=float).ravel()[0]) == float(i_p)


def test_spm_parents_ff_numeric_fg_gg_matrix_oracle(dem_eng):
    dem_eng.eval(
        "id_m = struct(); id_m.ff = [1 2]; id_m.fg = reshape(1:15, 3, 5); "
        "id_m.gg = reshape(101:115, 3, 5); id_m.A = {{[0 0]}}; "
        "Q_m = [2 3 0 0 0]; [j_m,i_m] = spm_parents(id_m, 2, Q_m);",
        nargout=0,
    )
    j_m = dem_eng.eval("j_m")
    i_m = dem_eng.eval("i_m")
    id_py = {
        "ff": np.array([1, 2], dtype=np.int64),
        "fg": np.arange(1, 16, dtype=np.float64).reshape(3, 5, order="F"),
        "gg": np.arange(101, 116, dtype=np.float64).reshape(3, 5, order="F"),
        "A": [np.array([[0.0, 0.0]])],
    }
    j_p, i_p = spm_parents(id_py, 2, np.array([2, 3, 0, 0, 0], dtype=float))
    assert_matlab_match(j_m, np.asarray(j_p, dtype=float).reshape(1, -1))
    assert_matlab_match(i_m, np.asarray(i_p, dtype=float).reshape(1, -1))


def test_spm_parents_ff_cell_q_nested_fg_gg_oracle(dem_eng):
    dem_eng.eval(
        "id_c = struct(); id_c.ff = [1 2]; "
        "Q_c = {[0.1 0.9]; [0.5 0.5]}; "
        "inner = cell(2,2); inner{1,1}=10; inner{1,2}=11; inner{2,1}=12; inner{2,2}=13; "
        "fgc = cell(3,1); fgc{2}=inner; id_c.fg = fgc; "
        "ggc = cell(3,1); ggc{2}=inner; id_c.gg = ggc; "
        "id_c.A = {{[0]}}; "
        "[j_c,i_c] = spm_parents(id_c, 2, Q_c);",
        nargout=0,
    )
    j_m = float(np.asarray(dem_eng.eval("j_c")).ravel()[0])
    i_m = float(np.asarray(dem_eng.eval("i_c")).ravel()[0])
    fg_py = [
        None,
        [[10.0, 11.0], [12.0, 13.0]],
        None,
    ]
    gg_py = [
        None,
        [[10.0, 11.0], [12.0, 13.0]],
        None,
    ]
    id_py = {
        "ff": np.array([1, 2], dtype=np.int64),
        "fg": fg_py,
        "gg": gg_py,
        "A": [np.array([[0.0]])],
    }
    q_py = [np.array([[0.1, 0.9]]), np.array([[0.5, 0.5]])]
    j_p, i_p = spm_parents(id_py, 2, q_py)
    assert abs(float(j_p) - j_m) < 1e-12
    assert abs(float(i_p) - i_m) < 1e-12


def test_spm_parents_ff_no_fg_gg_uses_a_and_g_oracle(dem_eng):
    dem_eng.eval(
        "id_n = struct('ff',[1],'A',{{[5 6 7]}}); Q_n = 3; "
        "[j_n,i_n] = spm_parents(id_n, 1, Q_n);",
        nargout=0,
    )
    j_m = dem_eng.eval("j_n")
    i_m = dem_eng.eval("i_n")
    id_py = {"ff": np.array([1], dtype=np.int64), "A": [np.array([[5.0, 6.0, 7.0]])]}
    j_p, i_p = spm_parents(id_py, 1, np.array([3.0]))
    assert_matlab_match(j_m, j_p)
    assert float(np.asarray(i_m, dtype=float).ravel()[0]) == float(i_p)
