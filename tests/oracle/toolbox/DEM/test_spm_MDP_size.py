from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)


def test_spm_MDP_size_lowercase_oracle(dem_eng):
    dem_eng.eval(
        "mdp = struct();"
        "mdp.a = {zeros(4,2,3), zeros(5,2,3)};"
        "mdp.b = {zeros(2,2), zeros(3,3,2)};"
        "[Nf,Ns,Nu,Ng,No] = spm_MDP_size(mdp);",
        nargout=0,
    )
    mdp = {
        "a": [
            np.zeros((4, 2, 3)),
            np.zeros((5, 2, 3)),
        ],
        "b": [
            np.zeros((2, 2)),
            np.zeros((3, 3, 2)),
        ],
    }

    _assert_outputs_match(dem_eng, spm_MDP_size(mdp))


def test_spm_MDP_size_uppercase_oracle(dem_eng):
    dem_eng.eval(
        "mdp = struct();"
        "mdp.A = {zeros(6,2), zeros(7,2)};"
        "mdp.B = {zeros(2,2,3), zeros(4,4,1)};"
        "[Nf,Ns,Nu,Ng,No] = spm_MDP_size(mdp);",
        nargout=0,
    )
    mdp = {
        "A": [
            np.zeros((6, 2)),
            np.zeros((7, 2)),
        ],
        "B": [
            np.zeros((2, 2, 3)),
            np.zeros((4, 4, 1)),
        ],
    }

    _assert_outputs_match(dem_eng, spm_MDP_size(mdp))


def _assert_outputs_match(eng, python_outputs):
    matlab_outputs = [
        eng.eval("Nf"),
        eng.eval("Ns"),
        eng.eval("Nu"),
        eng.eval("Ng"),
        eng.eval("No"),
    ]

    for matlab_output, python_output in zip(matlab_outputs, python_outputs):
        assert_matlab_match(matlab_output, python_output)
