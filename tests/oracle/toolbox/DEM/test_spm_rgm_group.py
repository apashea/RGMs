"""Oracle tests: spm_rgm_group.m vs python_src.toolbox.DEM.spm_rgm_group."""

from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.spm_rgm_group import spm_rgm_group
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    return eng


def _assign_O_cell(eng, matlab_name: str, o_py: list) -> None:
    """Push ``No × Nt`` cell ``O`` to MATLAB as ``(Ns, 1)`` columns per SPM usage."""
    no = len(o_py)
    nt = len(o_py[0])
    for o in range(no):
        for t in range(nt):
            arr = np.asarray(o_py[o][t], dtype=np.float64)
            ns = int(arr.shape[0])
            md = matlab.double(arr.tolist(), size=(ns, 1))
            eng.workspace["O_tmp_rgm"] = md
            eng.eval(f"{matlab_name}{{{o+1},{t+1}}} = O_tmp_rgm;", nargout=0)


def _pull_G(eng, matlab_name: str) -> list:
    ng = int(eng.eval(f"numel({matlab_name})"))
    return [
        np.asarray(eng.eval(f"{matlab_name}{{{i + 1}}}"), dtype=np.int64).ravel()
        for i in range(ng)
    ]


def test_spm_rgm_group_empty_oracle(dem_eng):
    dem_eng.eval("G_rgm_empty = spm_rgm_group({});", nargout=0)
    assert int(dem_eng.eval("numel(G_rgm_empty)")) == 0
    assert spm_rgm_group([]) == []


def test_spm_rgm_group_no_less_than_dx_single_group_oracle(dem_eng):
    no, nt, ns = 5, 2, 2
    np.random.seed(2)
    o_py = []
    for o in range(no):
        row = []
        for t in range(nt):
            v = np.random.rand(ns, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_O_cell(dem_eng, "O_rgm_small", o_py)
    dem_eng.eval("G_rgm_small = spm_rgm_group(O_rgm_small, 16);", nargout=0)
    g_m = _pull_G(dem_eng, "G_rgm_small")
    g_p = spm_rgm_group(o_py, 16, 1)
    assert len(g_m) == len(g_p) == 1
    assert_matlab_match(g_m[0], g_p[0])


def test_spm_rgm_group_clustering_oracle(dem_eng):
    no, nt, ns = 6, 4, 3
    np.random.seed(0)
    o_py = []
    for o in range(no):
        row = []
        for t in range(nt):
            v = np.random.rand(ns, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_O_cell(dem_eng, "O_rgm_clu", o_py)
    dem_eng.eval("G_rgm_clu = spm_rgm_group(O_rgm_clu, 3);", nargout=0)
    g_m = _pull_G(dem_eng, "G_rgm_clu")
    g_p = spm_rgm_group(o_py, 3, 1)
    assert len(g_m) == len(g_p)
    for a, b in zip(g_m, g_p):
        assert_matlab_match(a, b)


def test_spm_rgm_group_m2_oracle(dem_eng):
    no, nt, ns, m = 4, 3, 2, 2
    np.random.seed(1)
    o_py = []
    for o in range(no):
        row = []
        for t in range(nt):
            v = np.random.rand(ns, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_O_cell(dem_eng, "O_rgm_m2", o_py)
    dem_eng.eval("G_rgm_m2 = spm_rgm_group(O_rgm_m2, 8, 2);", nargout=0)
    g_m = _pull_G(dem_eng, "G_rgm_m2")
    g_p = spm_rgm_group(o_py, 8, 2)
    assert len(g_m) == len(g_p)
    for a, b in zip(g_m, g_p):
        assert_matlab_match(a, b)
