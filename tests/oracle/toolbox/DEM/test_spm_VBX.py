"""Oracle tests: spm_VBX.m vs python_src.toolbox.DEM.spm_VBX."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_VBX import spm_VBX
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    return eng


def test_spm_VBX_two_factors_with_ff_oracle(dem_eng):
    dem_eng.eval(
        "rng(2); O = cell(1,1); O{1} = rand(6,1); O{1} = O{1}/sum(O{1}); "
        "P = cell(1,2); P{1} = rand(2,1); P{1}=P{1}/sum(P{1}); "
        "P{2} = rand(3,1); P{2}=P{2}/sum(P{2}); "
        "A{1} = rand(6,2,3); A{1} = A{1}./sum(A{1}(:)); "
        "id = struct; id.g = {1}; id.ff = [1 2]; id.A = {[1 2]}; "
        "[Pm,Fm] = spm_VBX(O,P,A,id);",
        nargout=0,
    )
    Pm1 = dem_eng.eval("Pm{1}")
    Pm2 = dem_eng.eval("Pm{2}")
    Fm = float(np.asarray(dem_eng.eval("Fm")).reshape(-1)[0])
    O1 = np.array(dem_eng.eval("O{1}"), dtype=float)
    P1 = np.array(dem_eng.eval("P{1}"), dtype=float)
    P2 = np.array(dem_eng.eval("P{2}"), dtype=float)
    A1 = np.array(dem_eng.eval("A{1}"), dtype=float)
    id_py = {
        "g": [1],
        "ff": np.array([1, 2], dtype=np.int64),
        "A": [np.array([[1.0, 2.0]])],
    }
    Pp, Fp = spm_VBX([O1], [P1, P2], [A1], id_py)
    assert_matlab_match(Pm1, Pp[0])
    assert_matlab_match(Pm2, Pp[1])
    assert abs(float(Fp) - Fm) < 1e-8
