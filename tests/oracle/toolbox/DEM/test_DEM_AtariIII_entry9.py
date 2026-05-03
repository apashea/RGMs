"""Oracle tests for DEM_AtariIII Entry 9 (basin reduction in training loop)."""

from __future__ import annotations

import copy
import os
import pickle
from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _assert_no_top_level_xp,
    _mat_int,
    _pull_mdp_from_matlab,
    _pull_o8seq_from_matlab,
)


def _mat_fieldnames(eng, expr: str) -> list[str]:
    eng.eval(f"rgms_tmp_fn = fieldnames({expr});", nargout=0)
    n = int(_mat_int(eng, "numel(rgms_tmp_fn)"))
    out: list[str] = []
    for i in range(1, n + 1):
        out.append(str(eng.eval(f"rgms_tmp_fn{{{i}}}", nargout=1)))
    return out


def _mat_path_set(eng, expr: str, prefix: str = "") -> set[str]:
    out: set[str] = set()
    is_struct = bool(int(_mat_int(eng, f"isstruct({expr})")))
    is_cell = bool(int(_mat_int(eng, f"iscell({expr})")))
    if is_struct:
        n = int(_mat_int(eng, f"numel({expr})"))
        for i in range(1, n + 1):
            base = f"{expr}({i})" if n > 1 else expr
            base_path = f"{prefix}{{{i}}}" if n > 1 else prefix
            for field in _mat_fieldnames(eng, base):
                p = f"{base_path}.{field}" if base_path else field
                out.add(p)
                out |= _mat_path_set(eng, f"{base}.{field}", p)
        return out
    if is_cell:
        n = int(_mat_int(eng, f"numel({expr})"))
        for i in range(1, n + 1):
            p = f"{prefix}{{{i}}}" if prefix else f"{{{i}}}"
            out.add(p)
            out |= _mat_path_set(eng, f"{expr}{{{i}}}", p)
        return out
    if prefix:
        out.add(prefix)
    return out


def _py_path_set(obj, prefix: str = "") -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for key in sorted(obj.keys()):
            p = f"{prefix}.{key}" if prefix else str(key)
            out.add(p)
            out |= _py_path_set(obj[key], p)
        return out
    if isinstance(obj, list):
        for i, val in enumerate(obj, start=1):
            p = f"{prefix}{{{i}}}" if prefix else f"{{{i}}}"
            out.add(p)
            out |= _py_path_set(val, p)
        return out
    if prefix:
        out.add(prefix)
    return out


def _entry9_capture_refresh_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_ENTRY9_CAPTURE_REFRESH", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _entry9_capture_tag() -> str:
    raw = str(os.getenv("RGMS_ATARI_ENTRY9_CAPTURE_TAG", "default")).strip()
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw)
    return safe or "default"


def _entry9_capture_path(training_t: int, n_outer: int) -> Path:
    repo = Path(__file__).resolve().parents[4]
    ckpt_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    tag = _entry9_capture_tag()
    return ckpt_dir / f"dem_atari_entry9_oracle_capture_t{int(training_t)}_outer{int(n_outer)}_{tag}.pkl"


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


def _matlab_build_entry9_oracle_boundary(dem_eng, training_t: int, n_outer: int) -> None:
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
        "r = find(PDP.o(GDP.id.reward,:) > 1); "
        "c = find(PDP.o(GDP.id.contraint,:) > 1); "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + Ne):(r(i) + Ne); "
        "if numel(t), "
        "for s = 1:Ne, "
        "MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP); "
        "end; "
        "end; "
        "end; "
        "rgms_mdp7 = MDP; "
        "NT = 100; "
        "OseqFlat = {}; outer_end = []; MDPseq9 = {}; dseq9 = {}; oseq9 = {}; hseq9 = {}; "
        "NS9 = []; NU9 = []; NA9 = []; NO9 = []; NH9 = []; "
        f"for ii = 1:{int(n_outer)}, "
        "t = (0:(NT + Ne)) + rem(ii,100 - 1)*NT; "
        "for s = 1:Ne, "
        "OseqFlat{end+1} = PDP.O(:,t + s); "
        "MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP); "
        "end; "
        "[MDP,d,o,h] = spm_RDP_basin(MDP,[2,3],[C,-C]); "
        "MDPseq9{end+1} = MDP; dseq9{end+1} = d; oseq9{end+1} = o; hseq9{end+1} = h; "
        "NS9(end+1) = size(MDP{Nm}.b{1},2); "
        "NU9(end+1) = size(MDP{Nm}.b{1},3); "
        "NA9(end+1) = sum(~d); "
        "NO9(end+1) = sum(~o); "
        "NH9(end+1) = numel(h); "
        "outer_end(end+1) = numel(OseqFlat); "
        "if all(d), break, end; "
        "end; "
        "rgms_mdp9 = MDP;",
        nargout=0,
    )


def _capture_entry9_oracle_artifact(dem_eng, training_t: int, n_outer: int) -> dict:
    _matlab_build_entry9_oracle_boundary(dem_eng, training_t, n_outer)
    o_flat = _pull_o8seq_from_matlab(dem_eng, "OseqFlat")
    outer_end = np.asarray(dem_eng.eval("outer_end"), dtype=np.int64).ravel(order="F")
    n_iter = int(_mat_int(dem_eng, "numel(MDPseq9)"))
    if n_iter != int(outer_end.size):
        raise AssertionError(f"MDPseq9 count mismatch n_iter={n_iter} outer_end={outer_end.size}")

    mdp_seq = []
    d_seq = []
    o_seq = []
    h_seq = []
    for i in range(1, n_iter + 1):
        mdp_seq.append(_pull_mdp_from_matlab(dem_eng, f"MDPseq9{{{i}}}"))
        d_seq.append(np.asarray(dem_eng.eval(f"dseq9{{{i}}}"), dtype=bool).ravel(order="F"))
        o_seq.append(np.asarray(dem_eng.eval(f"oseq9{{{i}}}"), dtype=bool).ravel(order="F"))
        h_seq.append(np.asarray(dem_eng.eval(f"hseq9{{{i}}}"), dtype=np.int64).ravel(order="F"))

    artifact = {
        "training_t": int(training_t),
        "n_outer": int(n_outer),
        "o_flat": o_flat,
        "outer_end": outer_end,
        "n_iter": int(n_iter),
        "mdp7_mat": _pull_mdp_from_matlab(dem_eng, "rgms_mdp7"),
        "mdp_seq_mat": mdp_seq,
        "d_seq_mat": d_seq,
        "o_seq_mat": o_seq,
        "h_seq_mat": h_seq,
        "ns9": np.asarray(dem_eng.eval("NS9"), dtype=np.int64).ravel(order="F"),
        "nu9": np.asarray(dem_eng.eval("NU9"), dtype=np.int64).ravel(order="F"),
        "na9": np.asarray(dem_eng.eval("NA9"), dtype=np.int64).ravel(order="F"),
        "no9": np.asarray(dem_eng.eval("NO9"), dtype=np.int64).ravel(order="F"),
        "nh9": np.asarray(dem_eng.eval("NH9"), dtype=np.int64).ravel(order="F"),
        "mdp9_mat": _pull_mdp_from_matlab(dem_eng, "rgms_mdp9"),
    }
    return artifact


def _load_or_build_entry9_oracle_artifact(dem_eng, training_t: int, n_outer: int) -> dict:
    capture_path = _entry9_capture_path(training_t, n_outer)
    refresh = _entry9_capture_refresh_enabled()
    if capture_path.exists() and not refresh:
        with capture_path.open("rb") as f:
            return pickle.load(f)
    artifact = _capture_entry9_oracle_artifact(dem_eng, training_t, n_outer)
    with capture_path.open("wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)
    return artifact


def _ensure_entry9_matlab_workspace(dem_eng, training_t: int, n_outer: int) -> None:
    have_mdp7 = int(_mat_int(dem_eng, "exist('rgms_mdp7','var')")) == 1
    have_seq = int(_mat_int(dem_eng, "exist('MDPseq9','var')")) == 1
    if have_mdp7 and have_seq:
        return
    _matlab_build_entry9_oracle_boundary(dem_eng, training_t, n_outer)


def test_DEM_AtariIII_entries_1_to_9_python_smoke():
    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=9)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    assert "MDP" in ctx
    assert "NS" in ctx and "NU" in ctx and "NA" in ctx and "NO" in ctx and "NH" in ctx


@pytest.mark.slow
def test_DEM_AtariIII_entry9_deep_parity_matlab_boundary_oracle(dem_eng):
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = _load_or_build_entry9_oracle_artifact(dem_eng, training_t, n_outer)
    o_flat = artifact["o_flat"]
    outer_end = np.asarray(artifact["outer_end"], dtype=np.int64).ravel(order="F")
    n_iter = int(artifact["n_iter"])
    assert n_iter == int(outer_end.size)

    ns9 = np.asarray(artifact["ns9"], dtype=np.int64).ravel(order="F")
    nu9 = np.asarray(artifact["nu9"], dtype=np.int64).ravel(order="F")
    na9 = np.asarray(artifact["na9"], dtype=np.int64).ravel(order="F")
    no9 = np.asarray(artifact["no9"], dtype=np.int64).ravel(order="F")
    nh9 = np.asarray(artifact["nh9"], dtype=np.int64).ravel(order="F")

    mdp_py = copy.deepcopy(artifact["mdp7_mat"])
    ns_hist, nu_hist, na_hist, no_hist, nh_hist = [], [], [], [], []
    k0 = 0
    for i in range(1, n_iter + 1):
        kend = int(outer_end[i - 1])
        for k in range(k0 + 1, kend + 1):
            mdp_py = spm_merge_structure_learning(o_flat[k - 1], mdp_py)
        k0 = kend
        mdp_py, d_py, o_py, h_py, _ = spm_RDP_basin(mdp_py, [2, 3], [32, -32])
        mdp_mat_i = artifact["mdp_seq_mat"][i - 1]
        d_mat_i = np.asarray(artifact["d_seq_mat"][i - 1], dtype=bool).ravel(order="F")
        o_mat_i = np.asarray(artifact["o_seq_mat"][i - 1], dtype=bool).ravel(order="F")
        h_mat_i = np.asarray(artifact["h_seq_mat"][i - 1], dtype=np.int64).ravel(order="F")

        _assert_mdp_full_equal(mdp_py, mdp_mat_i, i)
        _assert_no_top_level_xp(mdp_py, i)
        assert np.array_equal(np.asarray(d_py, dtype=bool).ravel(order="F"), d_mat_i)
        assert np.array_equal(np.asarray(o_py, dtype=bool).ravel(order="F"), o_mat_i)
        assert np.array_equal(np.asarray(h_py, dtype=np.int64).ravel(order="F"), h_mat_i)

        b1 = np.asarray(mdp_py[len(mdp_py) - 1]["b"][0][0], dtype=np.float64)
        ns_hist.append(int(b1.shape[1]) if b1.ndim >= 2 else 1)
        nu_hist.append(int(b1.shape[2]) if b1.ndim >= 3 else 1)
        na_hist.append(int(np.sum(~np.asarray(d_py, dtype=bool).ravel(order="F"))))
        no_hist.append(int(np.sum(~np.asarray(o_py, dtype=bool).ravel(order="F"))))
        nh_hist.append(int(np.asarray(h_py, dtype=np.int64).ravel(order="F").size))

    assert ns_hist == [int(v) for v in ns9.tolist()]
    assert nu_hist == [int(v) for v in nu9.tolist()]
    assert na_hist == [int(v) for v in na9.tolist()]
    assert no_hist == [int(v) for v in no9.tolist()]
    assert nh_hist == [int(v) for v in nh9.tolist()]

    mdp9_mat = artifact["mdp9_mat"]
    _assert_mdp_full_equal(mdp_py, mdp9_mat, n_iter + 1)


@pytest.mark.slow
@pytest.mark.xfail(
    reason=(
        "Full field-path parity currently fails due to unresolved MATLAB-vs-Python "
        "container-path canonicalization differences (cell/list wrapper depth), "
        "and remains a tracked strict-scope sentinel."
    ),
    strict=True,
)
def test_DEM_AtariIII_entry9_outer4_full_field_path_parity_oracle(dem_eng):
    training_t = 10000
    n_outer = 4
    artifact = _load_or_build_entry9_oracle_artifact(dem_eng, training_t, n_outer)
    _ensure_entry9_matlab_workspace(dem_eng, training_t, n_outer)
    o_flat = artifact["o_flat"]
    outer_end = np.asarray(artifact["outer_end"], dtype=np.int64).ravel(order="F")
    n_iter = int(artifact["n_iter"])
    assert n_iter >= 1

    mdp_py = copy.deepcopy(artifact["mdp7_mat"])
    mat_paths_7 = _mat_path_set(dem_eng, "rgms_mdp7")
    py_paths_7 = _py_path_set(mdp_py)
    assert py_paths_7 == mat_paths_7

    k0 = 0
    for i in range(1, n_iter + 1):
        kend = int(outer_end[i - 1])
        for k in range(k0 + 1, kend + 1):
            mdp_py = spm_merge_structure_learning(o_flat[k - 1], mdp_py)
        k0 = kend
        mdp_py, _, _, _, _ = spm_RDP_basin(mdp_py, [2, 3], [32, -32])
        py_paths_i = _py_path_set(mdp_py)
        mat_paths_i = _mat_path_set(dem_eng, f"MDPseq9{{{i}}}")
        assert py_paths_i == mat_paths_i
