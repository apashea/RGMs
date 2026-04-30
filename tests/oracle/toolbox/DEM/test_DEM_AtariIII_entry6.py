import os
from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii


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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    return r, c, w_start, w_end


def _python_entry6_summary(ctx: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    r = np.asarray(ctx["r"], dtype=np.int64).ravel(order="F")
    c = np.asarray(ctx["c"], dtype=np.int64).ravel(order="F")
    w_start = np.asarray([int(w["t"][0]) for w in ctx["entry6_windows"]], dtype=np.int64)
    w_end = np.asarray([int(w["t"][-1]) for w in ctx["entry6_windows"]], dtype=np.int64)
    return r, c, w_start, w_end


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
    m_r, m_c, m_ws, m_we = _matlab_entry6_from_boundary(
        dem_eng,
        np.asarray(ctx["PDP"]["o"], dtype=np.float64),
        float(ctx["GDP"]["id"]["reward"]),
        float(ctx["GDP"]["id"]["contraint"]),
        int(ctx["Ne"]),
    )
    p_r, p_c, p_ws, p_we = _python_entry6_summary(ctx)

    np.testing.assert_array_equal(p_r, m_r)
    np.testing.assert_array_equal(p_c, m_c)
    np.testing.assert_array_equal(p_ws, m_ws)
    np.testing.assert_array_equal(p_we, m_we)
