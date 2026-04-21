"""Integration oracle: spm_MDP_pong → spm_MDP_generate (structure-learning chain).

``spm_MDP_generate`` calls ``spm_MDP_checkX`` internally (same as MATLAB line 48).
This test validates GDP built by Pong with ``Na=true`` through generate with small ``T``.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from tests.helpers.compare import assert_matlab_match


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)
        eng.rmpath(str(dem_path), nargout=0)


def _pull_cell_matrix(eng, expr: str) -> np.ndarray:
    eng.eval(f"rgms_tmp_mx = {expr};", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=float)


def _matlab_rand_stream_after_reset(dem_eng, n: int) -> list:
    """Match MATLAB ``spm_MDP_generate`` script: explicit ``twister`` stream."""
    dem_eng.eval(f"rng(0,'twister'); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(dem_eng.eval("rgms_rand_buf"), dtype=float).ravel().tolist()


def _py_hits_miss_from_o_id(o_mat: np.ndarray, id_dict: dict) -> tuple[np.ndarray, np.ndarray]:
    """Mirror snippet helpers on Python arrays: find(o(id.reward,:)>1), find(o(id.contraint,:)>1)."""
    o2 = np.asarray(o_mat, dtype=float)
    reward_idx = np.asarray(id_dict["reward"], dtype=int).ravel(order="F") - 1
    miss_idx = np.asarray(id_dict["contraint"], dtype=int).ravel(order="F") - 1
    hits = np.flatnonzero(np.any(o2[reward_idx, :] > 1.0, axis=0)) + 1
    miss = np.flatnonzero(np.any(o2[miss_idx, :] > 1.0, axis=0)) + 1
    return hits.astype(float), miss.astype(float)


def _assert_fsl_input_slice_exact(
    dem_eng,
    pdp_name: str,
    pdp_py: dict,
    k: int,
    s_mat: np.ndarray,
) -> None:
    """Step-5 closure: exact ``PDP.O(:,1:k)`` and stream slice boundaries for SL input."""
    dem_eng.eval(
        f"O_fsl_step5 = {pdp_name}.O(:,1:{int(k)}); "
        "S_fsl_step5 = ones(4,3); "
        f"S_fsl_step5(1,:) = [{int(s_mat[0,0])},{int(s_mat[0,1])},{int(s_mat[0,2])}]; "
        "S_fsl_step5(2,:) = [1,1,1]; "
        "S_fsl_step5(3,:) = [1,1,1]; "
        "S_fsl_step5(4,:) = [1,1,1]; "
        "S_fsl_step5(:,end+1:4) = 1;",
        nargout=0,
    )

    n_rows_m = int(np.asarray(dem_eng.eval("size(O_fsl_step5,1)"), dtype=int).item())
    n_cols_m = int(np.asarray(dem_eng.eval("size(O_fsl_step5,2)"), dtype=int).item())
    assert n_cols_m == int(k)
    assert n_rows_m == len(pdp_py["O"])

    # Exact row-by-row O(:,1:k) parity as fed to SL, comparing all time columns.
    for r in range(1, n_rows_m + 1):
        dem_eng.eval(f"rgms_row_block = cell2mat(O_fsl_step5({r},:));", nargout=0)
        row_m = np.asarray(dem_eng.eval("rgms_row_block"), dtype=float)
        row_p = np.column_stack(
            [np.asarray(pdp_py["O"][r - 1][t], dtype=float).ravel(order="F") for t in range(k)]
        )
        assert_matlab_match(row_m, row_p)

    # Verify stream boundary indexing implied by S and used by O(o,:) slicing in SL.
    s3 = np.asarray(s_mat[:, :3], dtype=np.int64)
    stream_sizes = np.prod(s3, axis=1).astype(np.int64)
    offsets = np.concatenate(([0], np.cumsum(stream_sizes[:-1])))
    for s_idx, (off, n_sz) in enumerate(zip(offsets, stream_sizes), start=1):
        lo = int(off + 1)
        hi = int(off + n_sz)
        no_m = int(
            np.asarray(
                dem_eng.eval(f"numel(O_fsl_step5({lo}:{hi},1))"),
                dtype=int,
            ).item()
        )
        assert no_m == int(n_sz), f"Stream {s_idx} O(o,:) row count mismatch"


def test_pong_na_true_then_generate_small_T_oracle(dem_eng):
    """
    GDP from ``spm_MDP_pong(4,4,1,1,0)``, ``T=4``, ``tau=1`` — compare PDP vs Python.

    ``Np=0`` so Pong uses no ``rand``; replay aligns ``spm_MDP_generate`` draws only.
    """
    dem_eng.eval(
        "rng(0,'twister'); "
        "[GDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,1,0); "
        "GDP.T = 4; "
        "GDP.tau = 1; "
        "rgms_pdp = spm_MDP_generate(GDP);",
        nargout=0,
    )

    s_m = np.asarray(dem_eng.eval("rgms_pdp.s"), dtype=float)
    o_m = np.asarray(dem_eng.eval("rgms_pdp.o"), dtype=float)
    u_m = np.asarray(dem_eng.eval("rgms_pdp.u"), dtype=float)

    ng = int(np.asarray(dem_eng.eval("numel(rgms_pdp.A)"), dtype=int).item())
    t_steps = int(np.asarray(dem_eng.eval("rgms_pdp.T"), dtype=int).item())

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 8192)

    gdp = spm_MDP_pong(4, 4, 1, 1, 0)[0]
    gdp["T"] = 4.0
    gdp["tau"] = 1.0

    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp_py = spm_MDP_generate(gdp)

    assert_matlab_match(s_m, pdp_py["s"])
    assert_matlab_match(o_m, pdp_py["o"])
    assert_matlab_match(u_m, pdp_py["u"])

    for g in range(ng):
        for tt in range(t_steps):
            om = _pull_cell_matrix(
                dem_eng,
                f"full(rgms_pdp.O{{{int(g) + 1},{int(tt) + 1}}})",
            )
            py_col = np.asarray(pdp_py["O"][g][tt], dtype=float)
            assert_matlab_match(om, py_col)


@pytest.mark.slow
def test_pong_na_true_then_generate_snippet_branch_oracle(dem_eng):
    """
    Exact snippet branch pre-SL closure for generate:
    ``spm_MDP_pong(12,9,4,1,0)``, ``GDP.T=1000``, ``tau=1`` under replay.
    """
    nr, nc, nd, na, npix = 12, 9, 4, 1, 0
    t_roll = 1000
    buf_n = 5_000_000

    dem_eng.eval(
        "rng(0,'twister'); "
        f"[GDP_s,hid,cid,con,RGB_s,nP] = spm_MDP_pong({nr},{nc},{nd},{na},{npix}); "
        f"GDP_s.T = {int(t_roll)}; GDP_s.tau = 1; "
        "rgms_pdp_s = spm_MDP_generate(GDP_s);",
        nargout=0,
    )

    s_m = np.asarray(dem_eng.eval("rgms_pdp_s.s"), dtype=float)
    o_m = np.asarray(dem_eng.eval("rgms_pdp_s.o"), dtype=float)
    u_m = np.asarray(dem_eng.eval("rgms_pdp_s.u"), dtype=float)
    ng = int(np.asarray(dem_eng.eval("numel(rgms_pdp_s.A)"), dtype=int).item())
    t_steps = int(np.asarray(dem_eng.eval("rgms_pdp_s.T"), dtype=int).item())

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, buf_n)
    gdp = spm_MDP_pong(nr, nc, nd, na, npix)[0]
    gdp["T"] = float(t_roll)
    gdp["tau"] = 1.0
    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp_py = spm_MDP_generate(gdp)

    assert_matlab_match(s_m, pdp_py["s"])
    assert_matlab_match(o_m, pdp_py["o"])
    assert_matlab_match(u_m, pdp_py["u"])

    # Representative time checkpoints to keep runtime tractable on exact branch.
    t_check = sorted({1, t_steps // 2, t_steps})
    for g in range(ng):
        for tt in t_check:
            om = _pull_cell_matrix(
                dem_eng,
                f"full(rgms_pdp_s.O{{{int(g) + 1},{int(tt)}}})",
            )
            py_col = np.asarray(pdp_py["O"][g][tt - 1], dtype=float)
            assert_matlab_match(om, py_col)


@pytest.mark.slow
def test_snippet_helper_semantics_hits_miss_oracle(dem_eng):
    """
    Step-4 closure: snippet helper semantics parity on exact branch outputs.

    MATLAB helpers:
      spm_get_hits = @(o,id) find(o(id.reward,:)    > 1);
      spm_get_miss = @(o,id) find(o(id.contraint,:) > 1);
    """
    nr, nc, nd, na, npix = 12, 9, 4, 1, 0
    t_roll = 1000
    buf_n = 5_000_000

    dem_eng.eval(
        "rng(0,'twister'); "
        f"[GDP_s,hid,cid,con,RGB_s,nP] = spm_MDP_pong({nr},{nc},{nd},{na},{npix}); "
        f"GDP_s.T = {int(t_roll)}; GDP_s.tau = 1; "
        "rgms_pdp_s = spm_MDP_generate(GDP_s); "
        "rgms_hits = find(rgms_pdp_s.o(rgms_pdp_s.id.reward,:) > 1); "
        "rgms_miss = find(rgms_pdp_s.o(rgms_pdp_s.id.contraint,:) > 1);",
        nargout=0,
    )
    hits_m = np.asarray(dem_eng.eval("rgms_hits"), dtype=float).ravel(order="F")
    miss_m = np.asarray(dem_eng.eval("rgms_miss"), dtype=float).ravel(order="F")

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, buf_n)
    gdp = spm_MDP_pong(nr, nc, nd, na, npix)[0]
    gdp["T"] = float(t_roll)
    gdp["tau"] = 1.0
    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp_py = spm_MDP_generate(gdp)

    hits_p, miss_p = _py_hits_miss_from_o_id(pdp_py["o"], pdp_py["id"])
    assert_matlab_match(hits_m, hits_p)
    assert_matlab_match(miss_m, miss_p)


@pytest.mark.slow
def test_snippet_sl_input_slice_boundary_oracle(dem_eng):
    """
    Step-5 closure: exact SL input parity for snippet branch.

    Validates ``PDP.O(:,1:1000)`` (all rows, all time columns) and stream slice
    boundaries used by `O(o,:)` in `spm_faster_structure_learning`.
    """
    nr, nc, nd, na, npix = 12, 9, 4, 1, 0
    t_roll = 1000
    k = 1000
    buf_n = 5_000_000
    s_mat = np.array(
        [
            [nr, nc, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
        ],
        dtype=np.float64,
    )

    dem_eng.eval(
        "rng(0,'twister'); "
        f"[GDP_s,hid,cid,con,RGB_s,nP] = spm_MDP_pong({nr},{nc},{nd},{na},{npix}); "
        f"GDP_s.T = {int(t_roll)}; GDP_s.tau = 1; "
        "rgms_pdp_s = spm_MDP_generate(GDP_s);",
        nargout=0,
    )

    rand_seq = _matlab_rand_stream_after_reset(dem_eng, buf_n)
    gdp = spm_MDP_pong(nr, nc, nd, na, npix)[0]
    gdp["T"] = float(t_roll)
    gdp["tau"] = 1.0
    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp_py = spm_MDP_generate(gdp)

    _assert_fsl_input_slice_exact(dem_eng, "rgms_pdp_s", pdp_py, k, s_mat)
