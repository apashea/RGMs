"""Oracle: ``spm_MDP_BMR.m`` / ``spm_MDP_log_evidence.m`` vs Python."""

from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_BMR import spm_MDP_BMR
from python_src.toolbox.DEM.spm_MDP_log_evidence import spm_MDP_log_evidence
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    root = Path(__file__).resolve().parents[4]
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(root / "matlab_src" / "toolbox" / "DEM"), nargout=0)
    return eng


def test_spm_MDP_log_evidence_oracle(dem_eng):
    dem_eng.eval(
        "qA = [4; 3]; pA = [1; 1]; rA = pA; [Fm, sAm] = spm_MDP_log_evidence(qA,pA,rA);",
        nargout=0,
    )
    Fm = np.asarray(dem_eng.eval("Fm"), dtype=np.float64)
    sAm = np.asarray(dem_eng.eval("sAm"), dtype=np.float64)
    qA = np.array([[4.0], [3.0]], dtype=np.float64)
    pA = np.array([[1.0], [1.0]], dtype=np.float64)
    Fp, sAp = spm_MDP_log_evidence(qA, pA, pA)
    assert_matlab_match(Fm, Fp)
    assert_matlab_match(sAm, sAp)


def test_spm_MDP_BMR_oracle(dem_eng):
    dem_eng.eval(
        "qp = [4; 3]; rp = cell(1,1); rp{1} = [1; 1]; Lm = spm_MDP_BMR(qp,rp);",
        nargout=0,
    )
    Lm = np.asarray(dem_eng.eval("Lm"), dtype=np.float64).reshape(-1)
    qp = np.array([[4.0], [3.0]], dtype=np.float64)
    rp = [np.array([[1.0], [1.0]], dtype=np.float64)]
    Lp = np.asarray(spm_MDP_BMR(qp, rp), dtype=np.float64).reshape(-1)
    assert_matlab_match(Lm, Lp)
