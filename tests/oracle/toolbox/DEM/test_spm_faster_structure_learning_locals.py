"""Oracle tests: locals from spm_faster_structure_learning vs MATLAB reference.

MATLAB Engine cannot call subfunctions in ``spm_faster_structure_learning.m``;
verbatim copies live under ``matlab_ref/`` for comparison only.
"""

from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.spm_faster_structure_learning import (
    _spm_group,
    _spm_structure_fast,
)
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def fsl_oracle_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(repo / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    ref = Path(__file__).resolve().parent / "matlab_ref"
    eng.addpath(str(ref), nargout=0)
    return eng


def _assign_o_cell_rect(fsl_oracle_eng, matlab_name: str, o_py: list) -> None:
    """Push ``Ng × Nt`` cell ``O`` (list of rows of column vectors)."""
    ng = len(o_py)
    nt = len(o_py[0])
    fsl_oracle_eng.eval(f"{matlab_name} = cell({ng},{nt});", nargout=0)
    for g in range(ng):
        for t in range(nt):
            arr = np.asarray(o_py[g][t], dtype=np.float64)
            ns = int(arr.shape[0])
            md = matlab.double(arr.tolist(), size=(ns, 1))
            fsl_oracle_eng.workspace["O_tmp_fsl"] = md
            fsl_oracle_eng.eval(
                f"{matlab_name}{{{g + 1},{t + 1}}} = O_tmp_fsl;", nargout=0
            )


def _pull_nested_group(eng, name: str, s) -> list:
    out = []
    for ii in range(s[0]):
        row = []
        for jj in range(s[1]):
            col = []
            for kk in range(s[2]):
                v = np.asarray(
                    eng.eval(f"{name}{{{ii + 1},{jj + 1},{kk + 1}}}"),
                    dtype=np.int64,
                ).ravel()
                col.append(v)
            row.append(col)
        out.append(row)
    return out


def _b_to_3d(arr: np.ndarray) -> np.ndarray:
    """Match MATLAB ``b`` which may be scalar, 2-D, or 3-D after ``full``."""
    x = np.asarray(arr, dtype=np.float64)
    if x.ndim == 0:
        return x.reshape((1, 1, 1))
    if x.ndim == 2:
        return x[:, :, np.newaxis]
    return x


def _pull_mdp_like(eng, mdp_name: str) -> dict:
    na = int(eng.eval(f"numel({mdp_name}.a)"))
    a = []
    for g in range(na):
        ag = np.asarray(eng.eval(f"full({mdp_name}.a{{{g + 1}}})"), dtype=np.float64)
        a.append(ag)
    b1 = np.asarray(eng.eval(f"full({mdp_name}.b{{1}})"), dtype=np.float64)
    ntx = int(eng.eval(f"numel({mdp_name}.X)"))
    mdp_x = []
    for t in range(ntx):
        xt = np.asarray(eng.eval(f"{mdp_name}.X{{{t + 1}}}"), dtype=bool).ravel()
        mdp_x.append(xt)
    ntp = int(eng.eval(f"numel({mdp_name}.P)"))
    mdp_p = []
    for t in range(ntp):
        pt = eng.eval(f"{mdp_name}.P{{{t + 1}}}")
        if isinstance(pt, bool) or (isinstance(pt, (int, float)) and int(pt) in (0, 1)):
            mdp_p.append(bool(pt))
        else:
            mdp_p.append(np.asarray(pt, dtype=bool).ravel())
    return {"a": a, "b": [b1], "X": mdp_x, "P": mdp_p}


def test_spm_group_oracle_N441_d2(fsl_oracle_eng):
    N = [4, 4, 1, 1]
    d = 2
    fsl_oracle_eng.workspace["N_g"] = matlab.double([float(x) for x in N], size=(1, 4))
    fsl_oracle_eng.eval("g_or_N441 = oracle_spm_group(N_g, 2);", nargout=0)
    s = [2, 2, 1]
    g_m = _pull_nested_group(fsl_oracle_eng, "g_or_N441", s)
    g_p = _spm_group(N, d)
    assert len(g_m) == len(g_p) == s[0]
    for i in range(s[0]):
        for j in range(s[1]):
            for k in range(s[2]):
                assert_matlab_match(g_m[i][j][k], g_p[i][j][k])


def test_spm_group_oracle_default_d(fsl_oracle_eng):
    """N=[9,9,1,1] uses 3×3 tiles on x,y per MATLAB default branch."""
    N = [9, 9, 1, 1]
    fsl_oracle_eng.workspace["N_g2"] = matlab.double([float(x) for x in N], size=(1, 4))
    fsl_oracle_eng.eval("g_or_99 = oracle_spm_group(N_g2);", nargout=0)
    s = [3, 3, 1]
    g_m = _pull_nested_group(fsl_oracle_eng, "g_or_99", s)
    g_p = _spm_group(N, None)
    for i in range(s[0]):
        for j in range(s[1]):
            for k in range(s[2]):
                assert_matlab_match(g_m[i][j][k], g_p[i][j][k])


def test_spm_structure_fast_oracle_single_row(fsl_oracle_eng):
    """One outcome modality, three time steps (matches prior integration fixture)."""
    a = np.array([[2.0, 1.0], [1.0, 3.0]], dtype=np.float64)
    b = np.array([[1.0, 2.0], [4.0, 1.0]], dtype=np.float64)
    c = np.array([[2.0, 1.0], [1.0, 3.0]], dtype=np.float64)
    o_py = [[a.reshape((-1, 1), order="F"), b.reshape((-1, 1), order="F"), c.reshape((-1, 1), order="F")]]
    _assign_o_cell_rect(fsl_oracle_eng, "O_sf", o_py)
    fsl_oracle_eng.eval(
        "[mdp_or_sf, j_or_sf] = oracle_spm_structure_fast(O_sf);", nargout=0
    )
    mdp_m = _pull_mdp_like(fsl_oracle_eng, "mdp_or_sf")
    j_m = np.asarray(fsl_oracle_eng.eval("j_or_sf"), dtype=np.float64)

    mdp_p, j_p = _spm_structure_fast(o_py)
    assert_matlab_match(j_m, j_p)
    assert len(mdp_p["a"]) == len(mdp_m["a"])
    for ag_m, ag_p in zip(mdp_m["a"], mdp_p["a"]):
        assert_matlab_match(np.asarray(ag_m), np.asarray(ag_p.toarray() if hasattr(ag_p, "toarray") else ag_p))
    bm = _b_to_3d(mdp_m["b"][0])
    bp = _b_to_3d(mdp_p["b"][0])
    assert_matlab_match(bm, bp)
    assert len(mdp_m["X"]) == len(mdp_p["X"])
    for xm, xp in zip(mdp_m["X"], mdp_p["X"]):
        np.testing.assert_array_equal(np.asarray(xm).astype(bool).ravel(), xp.ravel())
    assert len(mdp_m["P"]) == len(mdp_p["P"])
    for pm, pp in zip(mdp_m["P"], mdp_p["P"]):
        if isinstance(pp, np.ndarray) and pp.shape != ():
            np.testing.assert_array_equal(
                np.asarray(pm).astype(bool).ravel(), pp.astype(bool).ravel()
            )
        else:
            assert bool(np.asarray(pm).ravel()[0]) == bool(pp)
