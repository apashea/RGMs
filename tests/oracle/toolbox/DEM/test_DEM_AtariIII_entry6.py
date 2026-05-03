import os
from pathlib import Path
from unittest.mock import patch

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import _entry6_find_events_and_windows, run_dem_atariiii


@pytest.fixture
def dem_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


def _matlab_entry6_from_boundary(
    dem_eng, pdp_o: np.ndarray, reward_idx: float, contraint_idx: float, ne: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[np.ndarray]]:
    dem_eng.workspace["rgms_o"] = matlab.double(np.asarray(pdp_o, dtype=np.float64).tolist())
    dem_eng.workspace["rgms_reward"] = float(reward_idx)
    dem_eng.workspace["rgms_contraint"] = float(contraint_idx)
    dem_eng.workspace["rgms_ne"] = float(ne)
    dem_eng.eval(
        "r = find(rgms_o(rgms_reward,:) > 1); "
        "c = find(rgms_o(rgms_contraint,:) > 1); "
        "w_start = zeros(1,numel(r)); "
        "w_end = zeros(1,numel(r)); "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + rgms_ne):(r(i) + rgms_ne); "
        "if numel(t), w_start(i) = t(1); w_end(i) = t(end); end; "
        "end;",
        nargout=0,
    )
    r = np.asarray(dem_eng.eval("r"), dtype=np.int64).ravel(order="F")
    c = np.asarray(dem_eng.eval("c"), dtype=np.int64).ravel(order="F")
    w_start = np.asarray(dem_eng.eval("w_start"), dtype=np.int64).ravel(order="F")
    w_end = np.asarray(dem_eng.eval("w_end"), dtype=np.int64).ravel(order="F")
    dem_eng.eval("w_cells = arrayfun(@(k) w_start(k):w_end(k), 1:numel(w_start), 'UniformOutput', false);", nargout=0)
    w_cells = dem_eng.eval("w_cells")
    w_full = [np.asarray(w_cells[i], dtype=np.int64).ravel(order="F") for i in range(len(w_cells))]
    return r, c, w_start, w_end, w_full


def _matlab_boundary_inputs_entry6(dem_eng, training_t: int) -> tuple[np.ndarray, float, float, int]:
    dem_eng.eval(
        "rng(0,'twister'); "
        "Nr = 12; Nc = 9; Sc = 9; Nd = 4; C = 32; "
        "[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0); "
        "S = ones(4,3); S(1,:) = [Nr,Nc,1]; "
        f"GDP.tau = 1; GDP.T = {int(training_t)}; "
        "PDP = spm_MDP_generate(GDP); "
        "MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc); "
        "Nm = numel(MDP); Ne = max(2^(Nm - 1),1); "
        "for n = 1:Nm, "
        "for g = 1:numel(MDP{n}.a), MDP{n}.a{g} = []; end; "
        "for f = 1:numel(MDP{n}.b), MDP{n}.b{f} = []; end; "
        "end; "
        "rgms_o = PDP.o; "
        "rgms_reward = GDP.id.reward; "
        "rgms_contraint = GDP.id.contraint; "
        "rgms_ne = Ne;",
        nargout=0,
    )
    o = np.asarray(dem_eng.eval("rgms_o"), dtype=np.float64)
    reward = float(np.asarray(dem_eng.eval("rgms_reward"), dtype=np.float64).reshape(-1)[0])
    contraint = float(np.asarray(dem_eng.eval("rgms_contraint"), dtype=np.float64).reshape(-1)[0])
    ne = int(np.asarray(dem_eng.eval("rgms_ne"), dtype=np.int64).reshape(-1)[0])
    return o, reward, contraint, ne


def _matlab_rand_stream_after_reset(dem_eng, n: int) -> list[float]:
    dem_eng.eval(f"rng(0,'twister'); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(dem_eng.eval("rgms_rand_buf"), dtype=np.float64).ravel(order="F").tolist()


def _python_entry6_summary(ctx: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    r = np.asarray(ctx["r"], dtype=np.int64).ravel(order="F")
    c = np.asarray(ctx["c"], dtype=np.int64).ravel(order="F")
    w_start = np.asarray([int(w["t"][0]) for w in ctx["entry6_windows"]], dtype=np.int64)
    w_end = np.asarray([int(w["t"][-1]) for w in ctx["entry6_windows"]], dtype=np.int64)
    return r, c, w_start, w_end


def _python_windows_full(ctx: dict) -> list[np.ndarray]:
    return [np.asarray(w["t"], dtype=np.int64).ravel(order="F") for w in ctx["entry6_windows"]]


@pytest.mark.slow
def test_DEM_AtariIII_entries_1_to_6_python_smoke():
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=6)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    required = {"GDP", "PDP", "MDP", "Nm", "Ne", "r", "c", "entry6_windows"}
    assert required.issubset(set(ctx.keys()))
    assert isinstance(ctx["entry6_windows"], list)
    assert np.asarray(ctx["r"]).ndim == 1
    assert np.asarray(ctx["c"]).ndim == 1


@pytest.mark.slow
def test_DEM_AtariIII_entry6_checkpoint_roundtrip_smoke():
    repo = Path(__file__).resolve().parents[4]
    ck_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"
    tag = "pytest_entry6_roundtrip"
    pre = ck_dir / f"dem_atari_entry6_pre_{tag}.pkl"
    post = ck_dir / f"dem_atari_entry6_post_{tag}.pkl"
    for p in (pre, post):
        if p.exists():
            p.unlink()

    old = {
        "RGMS_ATARI_TRAINING_T": os.getenv("RGMS_ATARI_TRAINING_T"),
        "RGMS_ATARI_TAG": os.getenv("RGMS_ATARI_TAG"),
        "RGMS_ATARI_CAPTURE_ENTRY6_PRE": os.getenv("RGMS_ATARI_CAPTURE_ENTRY6_PRE"),
        "RGMS_ATARI_CAPTURE_ENTRY6_POST": os.getenv("RGMS_ATARI_CAPTURE_ENTRY6_POST"),
        "RGMS_ATARI_ENTRY6_USE_CHECKPOINT": os.getenv("RGMS_ATARI_ENTRY6_USE_CHECKPOINT"),
    }
    try:
        np.random.seed(0)
        os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
        os.environ["RGMS_ATARI_TAG"] = tag
        os.environ["RGMS_ATARI_CAPTURE_ENTRY6_PRE"] = "1"
        os.environ["RGMS_ATARI_CAPTURE_ENTRY6_POST"] = "1"
        os.environ.pop("RGMS_ATARI_ENTRY6_USE_CHECKPOINT", None)
        ctx_a = run_dem_atariiii(entry_stop=6)

        assert pre.exists(), f"expected checkpoint file: {pre}"
        assert post.exists(), f"expected checkpoint file: {post}"

        os.environ["RGMS_ATARI_ENTRY6_USE_CHECKPOINT"] = "1"
        os.environ.pop("RGMS_ATARI_CAPTURE_ENTRY6_PRE", None)
        os.environ.pop("RGMS_ATARI_CAPTURE_ENTRY6_POST", None)
        ctx_b = run_dem_atariiii(entry_stop=6)

        np.testing.assert_array_equal(np.asarray(ctx_a["r"]), np.asarray(ctx_b["r"]))
        np.testing.assert_array_equal(np.asarray(ctx_a["c"]), np.asarray(ctx_b["c"]))
        assert len(ctx_a["entry6_windows"]) == len(ctx_b["entry6_windows"])
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.mark.slow
def test_DEM_AtariIII_entry6_hits_miss_windows_oracle(dem_eng):
    training_t = 1000
    np.random.seed(0)
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = str(training_t)
    try:
        ctx = run_dem_atariiii(entry_stop=6)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    m_r, m_c, m_ws, m_we, m_wfull = _matlab_entry6_from_boundary(
        dem_eng,
        np.asarray(ctx["PDP"]["o"], dtype=np.float64),
        float(ctx["GDP"]["id"]["reward"]),
        float(ctx["GDP"]["id"]["contraint"]),
        int(ctx["Ne"]),
    )
    p_r, p_c, p_ws, p_we = _python_entry6_summary(ctx)
    p_wfull = _python_windows_full(ctx)

    np.testing.assert_array_equal(p_r, m_r)
    np.testing.assert_array_equal(p_c, m_c)
    np.testing.assert_array_equal(p_ws, m_ws)
    np.testing.assert_array_equal(p_we, m_we)
    assert len(p_wfull) == len(m_wfull)
    for p_t, m_t in zip(p_wfull, m_wfull):
        np.testing.assert_array_equal(p_t, m_t)


@pytest.mark.slow
def test_DEM_AtariIII_entry6_transform_parity_on_matlab_boundary_inputs_oracle(dem_eng):
    m_o, m_reward, m_contraint, m_ne = _matlab_boundary_inputs_entry6(dem_eng, training_t=1000)
    m_r, m_c, m_ws, m_we, m_wfull = _matlab_entry6_from_boundary(
        dem_eng, m_o, m_reward, m_contraint, m_ne
    )

    p_r, p_c, windows = _entry6_find_events_and_windows(
        m_o,
        {"reward": m_reward, "contraint": m_contraint},
        m_ne,
    )
    p_r = np.asarray(p_r, dtype=np.int64).ravel(order="F")
    p_c = np.asarray(p_c, dtype=np.int64).ravel(order="F")
    p_ws = np.asarray([int(w["t"][0]) for w in windows], dtype=np.int64)
    p_we = np.asarray([int(w["t"][-1]) for w in windows], dtype=np.int64)
    p_wfull = [np.asarray(w["t"], dtype=np.int64).ravel(order="F") for w in windows]

    np.testing.assert_array_equal(p_r, m_r)
    np.testing.assert_array_equal(p_c, m_c)
    np.testing.assert_array_equal(p_ws, m_ws)
    np.testing.assert_array_equal(p_we, m_we)
    assert len(p_wfull) == len(m_wfull)
    for p_t, m_t in zip(p_wfull, m_wfull):
        np.testing.assert_array_equal(p_t, m_t)


@pytest.mark.slow
def test_DEM_AtariIII_entry6_boundary_inputs_parity_oracle(dem_eng):
    m_o, m_reward, m_contraint, m_ne = _matlab_boundary_inputs_entry6(dem_eng, training_t=1000)
    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 5_000_000)

    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        with patch("numpy.random.rand", side_effect=rand_seq):
            ctx = run_dem_atariiii(entry_stop=6)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    p_o = np.asarray(ctx["PDP"]["o"], dtype=np.float64)
    p_reward = float(ctx["GDP"]["id"]["reward"])
    p_contraint = float(ctx["GDP"]["id"]["contraint"])
    p_ne = int(ctx["Ne"])

    assert p_reward == m_reward
    assert p_contraint == m_contraint
    assert p_ne == m_ne
    if not np.array_equal(p_o, m_o):
        neq = p_o != m_o
        idx = np.argwhere(neq)
        first = idx[0]
        row_counts = np.sum(neq, axis=1)
        col_counts = np.sum(neq, axis=0)
        p_r = np.flatnonzero(p_o[int(p_reward) - 1, :] > 1.0) + 1
        m_r = np.flatnonzero(m_o[int(m_reward) - 1, :] > 1.0) + 1
        p_c = np.flatnonzero(p_o[int(p_contraint) - 1, :] > 1.0) + 1
        m_c = np.flatnonzero(m_o[int(m_contraint) - 1, :] > 1.0) + 1
        top_rows = np.argsort(-row_counts)[:8] + 1
        top_cols = np.argsort(-col_counts)[:8] + 1
        raise AssertionError(
            "Entry 6 boundary input mismatch at PDP.o. "
            f"mismatch_count={int(np.sum(neq))}/{int(p_o.size)} "
            f"({float(np.sum(neq))/float(p_o.size):.4%}); "
            f"first_mismatch=(row={int(first[0])+1}, col={int(first[1])+1}, "
            f"py={float(p_o[first[0], first[1]])}, mat={float(m_o[first[0], first[1]])}); "
            f"top_rows_1based={top_rows.tolist()} counts={[int(row_counts[r-1]) for r in top_rows]}; "
            f"top_cols_1based={top_cols.tolist()} counts={[int(col_counts[c-1]) for c in top_cols]}; "
            f"reward_row={int(p_reward)} mismatch_count={int(row_counts[int(p_reward)-1])}; "
            f"contraint_row={int(p_contraint)} mismatch_count={int(row_counts[int(p_contraint)-1])}; "
            f"py_reward_hits={p_r.tolist()} mat_reward_hits={m_r.tolist()}; "
            f"py_miss_head={p_c[:20].tolist()} mat_miss_head={m_c[:20].tolist()} "
            f"(py_miss_len={int(p_c.size)}, mat_miss_len={int(m_c.size)})"
        )
