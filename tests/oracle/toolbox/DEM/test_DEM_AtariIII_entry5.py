import os
from pathlib import Path

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


def _matlab_entry5_summary(dem_eng, training_t: int) -> tuple[int, int, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dem_eng.eval(
        "rng(0,'twister'); "
        "Nr = 12; Nc = 9; Sc = 9; Nd = 4; C = 32; "
        "[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0); "
        "S = ones(4,3); S(1,:) = [Nr,Nc,1]; "
        f"GDP.tau = 1; GDP.T = {int(training_t)}; "
        "PDP = spm_MDP_generate(GDP); "
        "MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc); "
        "Nm = numel(MDP); Ne = max(2^(Nm - 1),1); "
        "a_counts = zeros(1,Nm); b_counts = zeros(1,Nm); "
        "a_empty = zeros(1,Nm); b_empty = zeros(1,Nm); "
        "for n = 1:Nm, "
        "a_counts(n) = numel(MDP{n}.a); b_counts(n) = numel(MDP{n}.b); "
        "for g = 1:numel(MDP{n}.a), MDP{n}.a{g} = []; end; "
        "for f = 1:numel(MDP{n}.b), MDP{n}.b{f} = []; end; "
        "a_empty(n) = all(cellfun(@isempty,MDP{n}.a)); "
        "b_empty(n) = all(cellfun(@isempty,MDP{n}.b)); "
        "end;",
        nargout=0,
    )
    nm = int(np.asarray(dem_eng.eval("Nm"), dtype=np.int64).reshape(-1)[0])
    ne = int(np.asarray(dem_eng.eval("Ne"), dtype=np.int64).reshape(-1)[0])
    a_counts = np.asarray(dem_eng.eval("a_counts"), dtype=np.int64).ravel(order="F")
    b_counts = np.asarray(dem_eng.eval("b_counts"), dtype=np.int64).ravel(order="F")
    a_empty = np.asarray(dem_eng.eval("a_empty"), dtype=np.int64).ravel(order="F")
    b_empty = np.asarray(dem_eng.eval("b_empty"), dtype=np.int64).ravel(order="F")
    return nm, ne, a_counts, b_counts, a_empty, b_empty


def _python_entry5_summary(ctx: dict) -> tuple[int, int, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mdp = ctx["MDP"]
    nm = int(ctx["Nm"])
    ne = int(ctx["Ne"])
    a_counts = np.asarray([len(mdp[n]["a"]) for n in range(nm)], dtype=np.int64)
    b_counts = np.asarray([len(mdp[n]["b"]) for n in range(nm)], dtype=np.int64)
    a_empty = np.asarray(
        [int(all(len(mdp[n]["a"][g]) == 0 for g in range(len(mdp[n]["a"])))) for n in range(nm)],
        dtype=np.int64,
    )
    b_empty = np.asarray(
        [int(all(len(mdp[n]["b"][f]) == 0 for f in range(len(mdp[n]["b"])))) for n in range(nm)],
        dtype=np.int64,
    )
    return nm, ne, a_counts, b_counts, a_empty, b_empty


def _entry5_all_empty(ctx: dict) -> bool:
    nm = int(ctx["Nm"])
    mdp = ctx["MDP"]
    for n in range(nm):
        for g in range(len(mdp[n]["a"])):
            if len(mdp[n]["a"][g]) != 0:
                return False
        for f in range(len(mdp[n]["b"])):
            if len(mdp[n]["b"][f]) != 0:
                return False
    return True


@pytest.mark.slow
def test_DEM_AtariIII_entries_1_to_5_python_smoke():
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=5)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    required = {"Nr", "Nc", "Sc", "Nd", "C", "GDP", "PDP", "S", "MDP", "Nm", "Ne"}
    assert required.issubset(set(ctx.keys()))
    assert int(ctx["Nm"]) == len(ctx["MDP"])
    assert int(ctx["Ne"]) == max(2 ** (int(ctx["Nm"]) - 1), 1)
    assert _entry5_all_empty(ctx)


@pytest.mark.slow
def test_DEM_AtariIII_entry5_checkpoint_roundtrip_smoke():
    repo = Path(__file__).resolve().parents[4]
    ck_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"
    tag = "pytest_entry5_roundtrip"
    pre = ck_dir / f"dem_atari_entry5_pre_{tag}.pkl"
    post = ck_dir / f"dem_atari_entry5_post_{tag}.pkl"
    for p in (pre, post):
        if p.exists():
            p.unlink()

    old = {
        "RGMS_ATARI_TRAINING_T": os.getenv("RGMS_ATARI_TRAINING_T"),
        "RGMS_ATARI_TAG": os.getenv("RGMS_ATARI_TAG"),
        "RGMS_ATARI_CAPTURE_ENTRY5_PRE": os.getenv("RGMS_ATARI_CAPTURE_ENTRY5_PRE"),
        "RGMS_ATARI_CAPTURE_ENTRY5_POST": os.getenv("RGMS_ATARI_CAPTURE_ENTRY5_POST"),
        "RGMS_ATARI_ENTRY5_USE_CHECKPOINT": os.getenv("RGMS_ATARI_ENTRY5_USE_CHECKPOINT"),
    }
    try:
        os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
        os.environ["RGMS_ATARI_TAG"] = tag
        os.environ["RGMS_ATARI_CAPTURE_ENTRY5_PRE"] = "1"
        os.environ["RGMS_ATARI_CAPTURE_ENTRY5_POST"] = "1"
        os.environ.pop("RGMS_ATARI_ENTRY5_USE_CHECKPOINT", None)
        ctx_a = run_dem_atariiii(entry_stop=5)

        assert pre.exists(), f"expected checkpoint file: {pre}"
        assert post.exists(), f"expected checkpoint file: {post}"
        assert _entry5_all_empty(ctx_a)

        os.environ["RGMS_ATARI_ENTRY5_USE_CHECKPOINT"] = "1"
        os.environ.pop("RGMS_ATARI_CAPTURE_ENTRY5_PRE", None)
        os.environ.pop("RGMS_ATARI_CAPTURE_ENTRY5_POST", None)
        ctx_b = run_dem_atariiii(entry_stop=5)

        assert int(ctx_a["Nm"]) == int(ctx_b["Nm"])
        assert int(ctx_a["Ne"]) == int(ctx_b["Ne"])
        assert _entry5_all_empty(ctx_b)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.mark.slow
def test_DEM_AtariIII_entry5_forget_parameters_oracle(dem_eng):
    training_t = 1000
    m_nm, m_ne, m_ac, m_bc, m_ae, m_be = _matlab_entry5_summary(dem_eng, training_t)

    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = str(training_t)
    try:
        ctx = run_dem_atariiii(entry_stop=5)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    p_nm, p_ne, p_ac, p_bc, p_ae, p_be = _python_entry5_summary(ctx)

    assert p_nm == m_nm
    assert p_ne == m_ne
    np.testing.assert_array_equal(p_ac, m_ac)
    np.testing.assert_array_equal(p_bc, m_bc)
    np.testing.assert_array_equal(p_ae, m_ae)
    np.testing.assert_array_equal(p_be, m_be)

