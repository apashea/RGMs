"""Oracle tests: spm_induction.m vs python_src.toolbox.DEM.spm_induction."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_induction import spm_induction
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    return eng


def test_spm_induction_hid_oracle(dem_eng):
    dem_eng.eval(
        "B = cell(1,2,2); "
        "B{1,1,1} = [0.8 0.2; 0.2 0.8]; B{1,1,2} = [0.6 0.4; 0.4 0.6]; "
        "B{1,2,1} = [0.9 0.1; 0.1 0.9]; B{1,2,2} = [0.7 0.3; 0.3 0.7]; "
        "Q = cell(1,2); Q{1} = [0.3;0.7]; Q{2} = [0.4;0.6]; "
        "id = struct; id.hid = [2;1]; "
        "[R_m,hif_m] = spm_induction(B,Q,3,id);",
        nargout=0,
    )
    R_m = dem_eng.eval("R_m")
    hif_m = dem_eng.eval("hif_m")
    B_py = [
        [
            np.array([[0.8, 0.2], [0.2, 0.8]], dtype=float),
            np.array([[0.6, 0.4], [0.4, 0.6]], dtype=float),
        ],
        [
            np.array([[0.9, 0.1], [0.1, 0.9]], dtype=float),
            np.array([[0.7, 0.3], [0.3, 0.7]], dtype=float),
        ],
    ]
    Q_py = [np.array([[0.3], [0.7]], dtype=float), np.array([[0.4], [0.6]], dtype=float)]
    id_py = {"hid": np.array([[2.0], [1.0]], dtype=float)}
    R_p, hif_p = spm_induction(B_py, Q_py, 3, id_py)
    assert_matlab_match(hif_m, hif_p.reshape(1, -1))
    assert_matlab_match(R_m, R_p)

