from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning


@pytest.fixture
def dem_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


def _python_case_inputs():
    o = [
        [
            np.asarray([[1.0], [0.0]], dtype=np.float64),
            np.asarray([[0.0], [1.0]], dtype=np.float64),
            np.asarray([[0.0], [1.0]], dtype=np.float64),
            np.asarray([[1.0], [0.0]], dtype=np.float64),
        ]
    ]
    mdp = [
        {
            "G": {1: [np.asarray([1], dtype=np.int64)]},
            "T": 1.0,
            "a": [[np.asarray([[1.0]], dtype=np.float64)]],
            "b": [[np.asarray([[[1.0]]], dtype=np.float64)]],
            "id": {"A": [[1]], "D": [[]], "E": [[]]},
            "sA": [1],
            "sB": [1],
            "sC": [1],
            "ss": {"D": [[None]], "E": [[None]], "ID": [[None]], "IE": [[None]]},
        }
    ]
    return o, mdp


def _matlab_case_eval(dem_eng, n_calls: int) -> tuple[np.ndarray, np.ndarray]:
    dem_eng.eval(
        "O = cell(1,4); "
        "O{1,1} = [1;0]; O{1,2} = [0;1]; O{1,3} = [0;1]; O{1,4} = [1;0]; "
        "MDP = cell(1,1); "
        "MDP{1}.G = {{[1]}}; "
        "MDP{1}.T = 1; "
        "MDP{1}.a = {1}; "
        "MDP{1}.b = {ones(1,1,1)}; "
        "MDP{1}.id.A = {1}; "
        "MDP{1}.id.D = {[]}; "
        "MDP{1}.id.E = {[]}; "
        "MDP{1}.sA = [1]; "
        "MDP{1}.sB = [1]; "
        "MDP{1}.sC = [1]; "
        "MDP{1}.ss.D = {[]}; "
        "MDP{1}.ss.E = {[]}; "
        "MDP{1}.ss.ID = {[]}; "
        "MDP{1}.ss.IE = {[]}; "
        f"for k = 1:{int(n_calls)}, MDP = spm_merge_structure_learning(O,MDP); end; "
        "rgms_a = full(MDP{1}.a{1}); "
        "rgms_b = full(MDP{1}.b{1});",
        nargout=0,
    )
    a = np.asarray(dem_eng.eval("rgms_a"), dtype=np.float64)
    b = np.asarray(dem_eng.eval("rgms_b"), dtype=np.float64)
    if b.ndim == 2:
        b = b[:, :, None]
    return a, b


@pytest.mark.slow
@pytest.mark.parametrize("n_calls", [1, 2])
def test_spm_merge_structure_learning_isolated_oracle(dem_eng, n_calls: int):
    o, mdp = _python_case_inputs()
    m_a, m_b = _matlab_case_eval(dem_eng, n_calls=n_calls)

    mdp_py = mdp
    for _ in range(n_calls):
        mdp_py = spm_merge_structure_learning(o, mdp_py)

    p_a = np.asarray(mdp_py[0]["a"][0][0], dtype=np.float64)
    p_b = np.asarray(mdp_py[0]["b"][0][0], dtype=np.float64)
    if p_b.ndim == 2:
        p_b = p_b[:, :, None]

    np.testing.assert_allclose(p_a, m_a, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(p_b, m_b, rtol=0.0, atol=1e-12)
