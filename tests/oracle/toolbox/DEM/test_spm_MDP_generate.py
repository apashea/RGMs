"""Oracle tests: spm_MDP_generate.m vs python_src.toolbox.DEM.spm_MDP_generate."""

import copy
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.rmpath(str(dem_path), nargout=0)


def _pull_cell_matrix(eng, expr: str) -> np.ndarray:
    eng.eval("rgms_tmp_mx = " + expr + ";", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=float)


def _matlab_rand_stream_after_reset(dem_eng, n: int = 32) -> list:
    """First `n` values of MATLAB's `rand` after `rng(0)` (column-major ravel)."""
    dem_eng.eval(f"rng(0); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(dem_eng.eval("rgms_rand_buf"), dtype=float).ravel().tolist()


def _minimal_mdp_spec() -> dict:
    return {
        "T": 2,
        "A": [np.eye(2, dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.25],
        "D": [np.ones((2, 1), dtype=np.float64) * 0.5],
        "E": [np.ones((1, 1), dtype=np.float64)],
        "U": np.array([[1.0]], dtype=np.float64),
        "s": np.array([[1.0, 1.0]], dtype=np.float64),
        "u": np.array([[1.0, 1.0]], dtype=np.float64),
    }


def test_spm_MDP_generate_minimal_single_factor_oracle(dem_eng):
    """
    One modality, one factor, T=2, Np=1, states and controls fixed.

    NumPy and MATLAB RNG streams differ; oracle aligns Python by replaying
    MATLAB's `rand` draws (after `rng(0)`) in call order inside `spm_MDP_generate`.
    """
    dem_eng.eval(
        "rng(0); "
        "rgms_mdp_in = struct; "
        "rgms_mdp_in.T = 2; "
        "rgms_mdp_in.A = {eye(2)}; "
        "rgms_mdp_in.B = {ones(2,2,1)*0.25}; "
        "rgms_mdp_in.D = {ones(2,1)*0.5}; "
        "rgms_mdp_in.E = {ones(1,1)}; "
        "rgms_mdp_in.U = [1]; "
        "rgms_mdp_in.s = [1, 1]; "
        "rgms_mdp_in.u = [1, 1]; "
        "rgms_mdp_in = spm_MDP_checkX(rgms_mdp_in); "
        "rgms_mdp_out = spm_MDP_generate(rgms_mdp_in);",
        nargout=0,
    )

    s_m = np.asarray(dem_eng.eval("rgms_mdp_out.s"), dtype=float)
    o_m = np.asarray(dem_eng.eval("rgms_mdp_out.o"), dtype=float)
    u_m = np.asarray(dem_eng.eval("rgms_mdp_out.u"), dtype=float)
    o11_m = _pull_cell_matrix(dem_eng, "full(rgms_mdp_out.O{1,1})")
    o12_m = _pull_cell_matrix(dem_eng, "full(rgms_mdp_out.O{1,2})")

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 32)

    mdp_py = copy.deepcopy(_minimal_mdp_spec())
    with patch("numpy.random.rand", side_effect=rand_seq):
        out_py = spm_MDP_generate(mdp_py)

    assert_matlab_match(s_m, out_py["s"])
    assert_matlab_match(o_m, out_py["o"])
    assert_matlab_match(u_m, out_py["u"])
    assert_matlab_match(o11_m, np.asarray(out_py["O"][0][0], dtype=float))
    assert_matlab_match(o12_m, np.asarray(out_py["O"][0][1], dtype=float))


def _two_modal_two_factor_mdp(s_init: list) -> dict:
    return {
        "T": 3,
        "A": [
            np.ones((2, 2, 2), dtype=np.float64) * 0.125,
            np.ones((2, 2, 2), dtype=np.float64) * 0.125,
        ],
        "B": [
            np.ones((2, 2, 1), dtype=np.float64) * 0.25,
            np.ones((2, 2, 1), dtype=np.float64) * 0.25,
        ],
        "D": [
            np.ones((2, 1), dtype=np.float64) * 0.5,
            np.ones((2, 1), dtype=np.float64) * 0.5,
        ],
        "E": [
            np.ones((1, 1), dtype=np.float64),
            np.ones((1, 1), dtype=np.float64),
        ],
        "U": np.array([[1.0, 0.0]], dtype=np.float64),
        "s": np.array(s_init, dtype=np.float64),
        "u": np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float64),
    }


def test_spm_MDP_generate_two_modalities_two_models_oracle(dem_eng):
    """
    Two outcome modalities (Ng=2), two hidden factors, two models (Nm=2).

    No ``id.hid`` so policy sampling uses ``PK`` only (stable under MATLAB
    ``rand`` replay). Models differ only in initial ``s`` so trajectories differ.
    """
    dem_eng.eval(
        "rng(0); "
        "rgms_M1 = struct; rgms_M1.T = 3; "
        "rgms_M1.A = {ones(2,2,2)*0.125, ones(2,2,2)*0.125}; "
        "rgms_M1.B = {ones(2,2,1)*0.25, ones(2,2,1)*0.25}; "
        "rgms_M1.D = {ones(2,1)*0.5, ones(2,1)*0.5}; "
        "rgms_M1.E = {ones(1,1), ones(1,1)}; "
        "rgms_M1.U = [1, 0]; "
        "rgms_M1.s = [1,0,0; 1,0,0]; rgms_M1.u = [1,0,0; 1,0,0]; "
        "rgms_M2 = rgms_M1; "
        "rgms_M2.s = [2,0,0; 2,0,0]; "
        "rgms_Gin = spm_MDP_checkX([rgms_M1; rgms_M2]); "
        "rgms_Gout = spm_MDP_generate(rgms_Gin);",
        nargout=0,
    )

    def pull(mi: int, field: str) -> np.ndarray:
        return np.asarray(
            dem_eng.eval(f"rgms_Gout({int(mi)},1).{field}"), dtype=float
        )

    s1_m, s2_m = pull(1, "s"), pull(2, "s")
    o1_m, o2_m = pull(1, "o"), pull(2, "o")
    u1_m, u2_m = pull(1, "u"), pull(2, "u")

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 120)

    m1 = copy.deepcopy(
        _two_modal_two_factor_mdp([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    m2 = copy.deepcopy(
        _two_modal_two_factor_mdp([[2.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    )
    with patch("numpy.random.rand", side_effect=rand_seq):
        out1, out2 = spm_MDP_generate([m1, m2])

    assert_matlab_match(s1_m, out1["s"])
    assert_matlab_match(o1_m, out1["o"])
    assert_matlab_match(u1_m, out1["u"])
    assert_matlab_match(s2_m, out2["s"])
    assert_matlab_match(o2_m, out2["o"])
    assert_matlab_match(u2_m, out2["u"])

    for mi, out in enumerate((out1, out2), start=1):
        for g in range(2):
            for tt in range(3):
                om = _pull_cell_matrix(
                    dem_eng,
                    f"full(rgms_Gout({mi},1).O{{{int(g) + 1},{int(tt) + 1}}})",
                )
                py_col = np.asarray(out["O"][g][tt], dtype=float)
                assert_matlab_match(om, py_col)


def _hid_one_row_mdp() -> dict:
    """Two modalities, two factors; ``id.hid`` only marks factor 1 (``hif`` scalar)."""
    m = spm_MDP_checkX(
        copy.deepcopy(_two_modal_two_factor_mdp([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]))
    )
    m["id"]["hid"] = np.array([[2.0], [0.0]], dtype=np.float64)
    return m


def test_spm_MDP_generate_hid_single_active_factor_oracle(dem_eng):
    """
    ``id.hid`` with one active factor row exercises local ``spm_induction``.

    MATLAB ``G(k)=R*P{r,k}`` is only used when ``numel(r)==1`` in staged SPM;
    ``hid`` is shaped so ``hif`` is a single factor index.
    """
    dem_eng.eval(
        "rng(0); "
        "rgms_H1 = struct; rgms_H1.T = 3; "
        "rgms_H1.A = {ones(2,2,2)*0.125, ones(2,2,2)*0.125}; "
        "rgms_H1.B = {ones(2,2,1)*0.25, ones(2,2,1)*0.25}; "
        "rgms_H1.D = {ones(2,1)*0.5, ones(2,1)*0.5}; "
        "rgms_H1.E = {ones(1,1), ones(1,1)}; "
        "rgms_H1.U = [1, 0]; "
        "rgms_H1.s = [1,0,0; 1,0,0]; rgms_H1.u = [1,0,0; 1,0,0]; "
        "rgms_H1.id = struct('hid', [2; 0]); "
        "rgms_H1 = spm_MDP_checkX(rgms_H1); "
        "rgms_Hout = spm_MDP_generate(rgms_H1);",
        nargout=0,
    )

    s_m = np.asarray(dem_eng.eval("rgms_Hout.s"), dtype=float)
    o_m = np.asarray(dem_eng.eval("rgms_Hout.o"), dtype=float)
    u_m = np.asarray(dem_eng.eval("rgms_Hout.u"), dtype=float)

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 40)

    mdp_py = copy.deepcopy(_hid_one_row_mdp())
    with patch("numpy.random.rand", side_effect=rand_seq):
        out_py = spm_MDP_generate(mdp_py)

    assert_matlab_match(s_m, out_py["s"])
    assert_matlab_match(o_m, out_py["o"])
    assert_matlab_match(u_m, out_py["u"])
    for g in range(2):
        for tt in range(3):
            om = _pull_cell_matrix(
                dem_eng,
                f"full(rgms_Hout.O{{{int(g) + 1},{int(tt) + 1}}})",
            )
            py_col = np.asarray(out_py["O"][g][tt], dtype=float)
            assert_matlab_match(om, py_col)
