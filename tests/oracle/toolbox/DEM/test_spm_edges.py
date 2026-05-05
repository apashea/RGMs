"""Oracle tests: spm_edges.m vs python_src.toolbox.DEM.spm_edges."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_edges import spm_edges
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    return eng


def test_spm_edges_state_independent_oracle(dem_eng):
    dem_eng.eval(
        "id_si = struct('A', reshape(1:9, 3, 3)); [j_si,i_si,q_si] = spm_edges(id_si, 2, 0);",
        nargout=0,
    )
    j_m = dem_eng.eval("j_si")
    i_m = float(np.asarray(dem_eng.eval("i_si"), dtype=float).ravel()[0])
    q_m = float(np.asarray(dem_eng.eval("q_si"), dtype=float).ravel()[0])
    id_py = {"A": np.arange(1, 10, dtype=np.float64).reshape(3, 3, order="F")}
    j_p, i_p, q_p = spm_edges(id_py, 2, 0.0)
    assert_matlab_match(j_m, j_p)
    assert i_m == float(i_p)
    assert q_m == float(q_p)


def test_spm_edges_ff_a_only_oracle(dem_eng):
    dem_eng.eval(
        "id = struct(); id.ff = [1 2]; id.A = {[10 11], [20 21 22]}; "
        "Q = cell(2,1); Q{1} = [0.05 0.95]; Q{2} = [0.2 0.3 0.5]; "
        "[j_m,i_m,q_m] = spm_edges(id, 2, Q);",
        nargout=0,
    )
    j_m = dem_eng.eval("j_m")
    i_m = dem_eng.eval("i_m")
    q_m = dem_eng.eval("q_m")
    Q_py = [np.array([[0.05, 0.95]]), np.array([[0.2, 0.3, 0.5]])]
    id_py = {
        "ff": np.array([1, 2], dtype=np.int64),
        "A": [np.array([[10.0, 11.0]]), np.array([[20.0, 21.0, 22.0]])],
    }
    j_p, i_p, q_p = spm_edges(id_py, 2, Q_py)
    assert_matlab_match(j_m, j_p)
    assert_matlab_match(i_m, i_p)
    assert_matlab_match(q_m, q_p)


def test_spm_edges_3d_fg_oracle(dem_eng):
    dem_eng.eval(
        "rng(0); fg = randn(2,3,4); id = struct(); id.ff = [1 2]; id.fg = fg; "
        "id.A = {{1},{2}}; Q = cell(2,1); Q{1} = [0.01 0.99]; Q{2} = [0.5 0.5]; "
        "[j_m,i_m,q_m] = spm_edges(id, 2, Q);",
        nargout=0,
    )
    fg = np.array(dem_eng.eval("fg"), dtype=float)
    j_m1 = np.asarray(dem_eng.eval("j_m{1}"), dtype=float).ravel()
    q_m = np.asarray(dem_eng.eval("q_m"), dtype=float).ravel()
    Q_py = [np.array([[0.01, 0.99]]), np.array([[0.5, 0.5]])]
    id_py = {
        "ff": np.array([1, 2], dtype=np.int64),
        "fg": fg,
        "A": [np.array([[1.0]]), np.array([[2.0]])],
    }
    j_p, i_p, q_p = spm_edges(id_py, 2, Q_py)
    np.testing.assert_allclose(np.asarray(j_p[0]).ravel(), j_m1)
    np.testing.assert_allclose(q_m, np.asarray(q_p).ravel())
