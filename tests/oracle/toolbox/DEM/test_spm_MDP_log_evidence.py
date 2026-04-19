from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_log_evidence import spm_MDP_log_evidence
from tests.helpers.compare import assert_matlab_match


def test_spm_MDP_log_evidence_matrix_oracle(dem_eng):
    qA = np.array([[3.0, 1.0, 2.0], [1.0, 4.0, 2.0]])
    pA = np.array([[2.0, 2.0, 1.0], [1.0, 3.0, 2.0]])
    rA = np.array([[2.5, 1.5, 1.0], [1.0, 2.0, 3.0]])

    matlab_outputs = dem_eng.spm_MDP_log_evidence(
        matlab.double(qA.tolist()),
        matlab.double(pA.tolist()),
        matlab.double(rA.tolist()),
        nargout=3,
    )
    python_outputs = spm_MDP_log_evidence(qA, pA, rA)

    for matlab_output, python_output in zip(matlab_outputs, python_outputs):
        assert_matlab_match(matlab_output, python_output)


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)
