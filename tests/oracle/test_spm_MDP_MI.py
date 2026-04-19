import numpy as np

from python_src.spm_MDP_MI import spm_MDP_MI
from tests.helpers.compare import assert_matlab_match


def test_spm_MDP_MI_numeric_no_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = [2 1 3; 1 4 2];"
        "[E_spm_MDP_MI,dEda_spm_MDP_MI,dEdA_spm_MDP_MI] = "
        "spm_MDP_MI(a_spm_MDP_MI);",
        nargout=0,
    )
    a = np.array([[2.0, 1.0, 3.0], [1.0, 4.0, 2.0]])

    _assert_mdp_mi_outputs_match(eng, spm_MDP_MI(a))


def test_spm_MDP_MI_numeric_with_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = [2 1 3; 1 4 2];"
        "c_spm_MDP_MI = [1; 2];"
        "h_spm_MDP_MI = [3; 1; 2];"
        "[E_spm_MDP_MI,dEda_spm_MDP_MI,dEdA_spm_MDP_MI] = "
        "spm_MDP_MI(a_spm_MDP_MI,c_spm_MDP_MI,h_spm_MDP_MI);",
        nargout=0,
    )
    a = np.array([[2.0, 1.0, 3.0], [1.0, 4.0, 2.0]])
    c = np.array([[1.0], [2.0]])
    h = np.array([[3.0], [1.0], [2.0]])

    _assert_mdp_mi_outputs_match(eng, spm_MDP_MI(a, c, h))


def test_spm_MDP_MI_empty_outcome_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = [2 1 3; 1 4 2];"
        "[E_spm_MDP_MI,dEda_spm_MDP_MI,dEdA_spm_MDP_MI] = "
        "spm_MDP_MI(a_spm_MDP_MI,[]);",
        nargout=0,
    )
    a = np.array([[2.0, 1.0, 3.0], [1.0, 4.0, 2.0]])
    c = np.empty((0, 0))

    _assert_mdp_mi_outputs_match(eng, spm_MDP_MI(a, c))


def test_spm_MDP_MI_cell_with_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = {[2 1; 1 3], [1 2; 4 1]};"
        "c_spm_MDP_MI = {[1; 2], [3; 1]};"
        "E_spm_MDP_MI = spm_MDP_MI(a_spm_MDP_MI,c_spm_MDP_MI);",
        nargout=0,
    )
    a = [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]
    c = [np.array([[1.0], [2.0]]), np.array([[3.0], [1.0]])]

    E_matlab = eng.eval("E_spm_MDP_MI")
    E_python = spm_MDP_MI(a, c)

    assert_matlab_match(E_matlab, E_python)


def _assert_mdp_mi_outputs_match(eng, python_outputs):
    matlab_outputs = [
        eng.eval("E_spm_MDP_MI"),
        eng.eval("dEda_spm_MDP_MI"),
        eng.eval("dEdA_spm_MDP_MI"),
    ]

    for matlab_output, python_output in zip(matlab_outputs, python_outputs):
        assert_matlab_match(matlab_output, python_output)
