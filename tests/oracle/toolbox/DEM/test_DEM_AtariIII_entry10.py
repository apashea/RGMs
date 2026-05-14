"""Entry 10–isolated MATLAB boundary, capture, and driver smoke (DEM_AtariIII lane).

Isolation: no imports from other entry test modules. Uses `_pull_mdp_from_matlab` /
`_assert_mdp_full_equal` from the Entry 8 oracle helper. Capture includes sort, post-sort
`MDP`, post-goals `MDP`, `P`, and `hid` for goals/`P` parity tests.
"""

from __future__ import annotations

import copy
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import dem_atariiii_paths_to_hits_P
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _assert_mdp_full_equal,
    _mat_cell_matrix_numeric,
    _mat_cell_scalar_list,
    _mat_cell_vector_list,
    _mat_float,
    _mat_full_numeric,
    _mat_groups,
    _mat_int,
    _pull_mdp_from_matlab,
)


def _pull_nested_rdp_from_matlab(eng, expr: str) -> dict[str, Any]:
    """Pull MATLAB nested ``RDP`` / ``MDP.MDP...`` struct into nested Python ``dict``."""
    out: dict[str, Any] = {}
    if _mat_int(eng, f"isfield({expr},'L')"):
        out["L"] = _mat_int(eng, f"{expr}.L")
    if _mat_int(eng, f"isfield({expr},'T')"):
        out["T"] = _mat_float(eng, f"{expr}.T")

    for cell_name in ("A", "B", "C", "a", "b"):
        if _mat_int(eng, f"isfield({expr},'{cell_name}')"):
            nc = _mat_int(eng, f"numel({expr}.{cell_name})")
            cells: list[np.ndarray] = []
            for k in range(1, nc + 1):
                # One ndarray per MATLAB cell (not ``[array]``): Python ``spm_MDP_checkX`` / VB expect ``A[g].shape``.
                cells.append(_mat_full_numeric(eng, f"{expr}.{cell_name}{{{k}}}"))
            out[cell_name] = cells

    for vec_name in ("sA", "sB", "sC"):
        if _mat_int(eng, f"isfield({expr},'{vec_name}')"):
            arr = np.asarray(eng.eval(f"double({expr}.{vec_name}(:))"), dtype=np.int64).ravel(order="F")
            out[vec_name] = [int(x) for x in arr.tolist()]

    if _mat_int(eng, f"isfield({expr},'U')"):
        u = np.asarray(eng.eval(f"double({expr}.U)"), dtype=np.float64)
        # MATLAB ``U`` is 1×Nf row; Engine pulls can arrive as 0-D/1-D — VB uses ``MDP.U(:,f)`` (2-D).
        out["U"] = np.atleast_2d(u)

    if _mat_int(eng, f"isfield({expr},'G')"):
        out["G"] = _mat_groups(eng, f"{expr}.G")

    if _mat_int(eng, f"isfield({expr},'ss')"):
        ss_ex = f"{expr}.ss"
        out["ss"] = {
            "D": _mat_cell_matrix_numeric(eng, f"{ss_ex}.D"),
            "E": _mat_cell_matrix_numeric(eng, f"{ss_ex}.E"),
            "ID": _mat_cell_matrix_numeric(eng, f"{ss_ex}.ID"),
            "IE": _mat_cell_matrix_numeric(eng, f"{ss_ex}.IE"),
        }

    if _mat_int(eng, f"isfield({expr},'id')"):
        id_ex = f"{expr}.id"
        id_out: dict[str, Any] = {}
        if _mat_int(eng, f"isfield({id_ex},'A')"):
            id_out["A"] = [[float(v)] for v in _mat_cell_scalar_list(eng, f"{id_ex}.A")]
        if _mat_int(eng, f"isfield({id_ex},'D')"):
            id_out["D"] = _mat_cell_vector_list(eng, f"{id_ex}.D")
        if _mat_int(eng, f"isfield({id_ex},'E')"):
            id_out["E"] = _mat_cell_vector_list(eng, f"{id_ex}.E")
        out["id"] = id_out

    if _mat_int(eng, f"isfield({expr},'MDP')"):
        out["MDP"] = _pull_nested_rdp_from_matlab(eng, f"{expr}.MDP")

    return out


def _matlab_build_entry10_training_end_boundary(
    dem_eng, training_t: int, n_outer: int, rng_seed: int = 0
) -> None:
    """Reproducible MATLAB pipeline through end of Entry 9 (`rgms_mdp9`), Entry-10-owned string."""
    dem_eng.eval(
        f"rng({int(rng_seed)},'twister'); "
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


def _matlab_run_entry10_sort_goals_and_P(dem_eng) -> None:
    """MATLAB: sort → `spm_set_goals` → paths-to-hits `P` (ledger Entry 10)."""
    dem_eng.eval(
        "rgms_mdp10_pre = rgms_mdp9; "
        "rgms_B10 = spm_dir_norm(sum(rgms_mdp10_pre{end}.b{1},3) > 0); "
        "[e10,v10] = eig(rgms_B10,'nobalance'); "
        "[~,jj10] = max(real(diag(v10))); "
        "rgms_p10 = spm_dir_norm(abs(e10(:,jj10)))'; "
        "[rgms_mdp10_post, rgms_j10] = spm_RDP_sort(rgms_mdp10_pre); "
        "rgms_mdp10_goals = spm_set_goals(rgms_mdp10_post,[2,3],[C,-C]); "
        "rgms_hid10 = rgms_mdp10_goals{end}.id.hid; "
        "rgms_Bp10 = sum(rgms_mdp10_goals{end}.b{1},3) > 0; "
        "if issparse(rgms_Bp10), rgms_Bp10 = full(rgms_Bp10); end; "
        "Ns = size(rgms_Bp10,1); Nt = 32; "
        "if isempty(rgms_hid10), h = sparse(1,Ns); "
        "else, h = sparse(1,double(rgms_hid10(:))',ones(numel(rgms_hid10),1),1,Ns); end; "
        "rgms_P10 = zeros(Nt,Ns); "
        "for t = 1:Nt, rgms_P10(t,:) = full(h); h = (h + h*double(rgms_Bp10)) > 0; end;",
        nargout=0,
    )


def entry10_sort_capture_refresh_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_ENTRY10_SORT_CAPTURE_REFRESH", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def entry10_sort_capture_tag() -> str:
    raw = str(os.getenv("RGMS_ATARI_ENTRY10_SORT_CAPTURE_TAG", "default")).strip()
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw)
    return safe or "default"


def entry10_sort_capture_path(training_t: int, n_outer: int) -> Path:
    repo = Path(__file__).resolve().parents[4]
    ckpt_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    tag = entry10_sort_capture_tag()
    return (
        ckpt_dir
        / f"dem_atari_entry10_sort_capture_t{int(training_t)}_outer{int(n_outer)}_{tag}.pkl"
    )


def _capture_entry10_sort_artifact(dem_eng, training_t: int, n_outer: int) -> dict:
    _matlab_build_entry10_training_end_boundary(dem_eng, training_t, n_outer)
    _matlab_run_entry10_sort_goals_and_P(dem_eng)
    j_vec = np.asarray(dem_eng.eval("rgms_j10(:)"), dtype=np.int64).ravel(order="F")
    dem_eng.eval(
        "if issparse(rgms_B10), rgms_B10 = full(rgms_B10); end;",
        nargout=0,
    )
    b_mat = np.asarray(dem_eng.eval("rgms_B10"), dtype=np.float64)
    p_mat = np.asarray(dem_eng.eval("rgms_p10(:)"), dtype=np.float64).ravel(order="F")
    p_block = np.asarray(dem_eng.eval("rgms_P10"), dtype=np.float64)
    hid_vec = np.asarray(dem_eng.eval("double(rgms_hid10(:))"), dtype=np.int64).ravel(order="F")
    # Snapshot post-goals MDP before spm_set_costs mutates rgms_mdp10_goals in-place.
    mdp10_goals_mat = _pull_mdp_from_matlab(dem_eng, "rgms_mdp10_goals")
    dem_eng.eval(
        "rgms_mdp11_costs = spm_set_costs(rgms_mdp10_goals,[2,3],[C,-C]);",
        nargout=0,
    )
    mdp11_costs_mat = _pull_mdp_from_matlab(dem_eng, "rgms_mdp11_costs")
    dem_eng.eval(
        "rgms_rdp11 = spm_mdp2rdp(rgms_mdp11_costs); rgms_rdp11.T = 64;",
        nargout=0,
    )
    rdp11_nested_mat = _pull_nested_rdp_from_matlab(dem_eng, "rgms_rdp11")
    return {
        "entry10_capture_v": 3,
        "training_t": int(training_t),
        "n_outer": int(n_outer),
        "tag": entry10_sort_capture_tag(),
        "mdp10_pre": _pull_mdp_from_matlab(dem_eng, "rgms_mdp10_pre"),
        "mdp10_post_mat": _pull_mdp_from_matlab(dem_eng, "rgms_mdp10_post"),
        "mdp10_goals_mat": mdp10_goals_mat,
        "mdp11_costs_mat": mdp11_costs_mat,
        "rdp11_nested_mat": rdp11_nested_mat,
        "j_mat": j_vec,
        "B_mat": b_mat,
        "p_mat": p_mat,
        "P_mat": p_block,
        "hid_mat": hid_vec,
        "entry10_nt": 32,
    }


def load_or_build_entry10_sort_artifact(dem_eng, training_t: int, n_outer: int) -> dict:
    capture_path = entry10_sort_capture_path(training_t, n_outer)
    refresh = entry10_sort_capture_refresh_enabled()
    if capture_path.exists() and not refresh:
        with capture_path.open("rb") as f:
            old = pickle.load(f)
        if (
            isinstance(old, dict)
            and old.get("entry10_capture_v") == 3
            and "B_mat" in old
            and "p_mat" in old
            and "mdp10_goals_mat" in old
            and "P_mat" in old
            and "hid_mat" in old
            and "mdp11_costs_mat" in old
            and "rdp11_nested_mat" in old
        ):
            return old
        refresh = True
    if capture_path.exists() and refresh:
        capture_path.unlink(missing_ok=True)
    artifact = _capture_entry10_sort_artifact(dem_eng, training_t, n_outer)
    with capture_path.open("wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)
    return artifact


@pytest.fixture
def dem_eng_entry10(eng):
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


@pytest.mark.slow
def test_entry10_spm_RDP_sort_capture_artifact_build_or_reuse(dem_eng_entry10):
    """Entry 10–scoped artifact: pre/post `spm_RDP_sort` MDP + MATLAB `j` (for `spm_RDP_sort` oracle)."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = load_or_build_entry10_sort_artifact(dem_eng_entry10, training_t, n_outer)
    assert artifact["training_t"] == int(training_t)
    assert artifact["n_outer"] == int(n_outer)
    assert isinstance(artifact["mdp10_pre"], list) and len(artifact["mdp10_pre"]) >= 1
    assert isinstance(artifact["mdp10_post_mat"], list) and len(artifact["mdp10_post_mat"]) >= 1
    assert isinstance(artifact["j_mat"], np.ndarray)
    assert "B_mat" in artifact and isinstance(artifact["B_mat"], np.ndarray)
    assert "p_mat" in artifact and isinstance(artifact["p_mat"], np.ndarray)
    assert "mdp10_goals_mat" in artifact and isinstance(artifact["mdp10_goals_mat"], list)
    assert "P_mat" in artifact and isinstance(artifact["P_mat"], np.ndarray)
    assert "hid_mat" in artifact and isinstance(artifact["hid_mat"], np.ndarray)
    assert "mdp11_costs_mat" in artifact and isinstance(artifact["mdp11_costs_mat"], list)
    assert "rdp11_nested_mat" in artifact and isinstance(artifact["rdp11_nested_mat"], dict)
    p = entry10_sort_capture_path(training_t, n_outer)
    assert p.is_file(), f"expected capture at {p}"


@pytest.mark.slow
def test_entry10_set_goals_and_paths_to_hits_oracle(dem_eng_entry10):
    """From MATLAB post-sort `MDP`, Python `spm_set_goals` + `P` match capture."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = load_or_build_entry10_sort_artifact(dem_eng_entry10, training_t, n_outer)
    mdp = copy.deepcopy(artifact["mdp10_post_mat"])
    mdp = spm_set_goals(
        mdp,
        np.array([2, 3], dtype=np.int64),
        np.array([32.0, -32.0], dtype=np.float64),
    )
    _assert_mdp_full_equal(mdp, artifact["mdp10_goals_mat"], 1)
    nm = len(mdp)
    b1 = np.asarray(mdp[nm - 1]["b"][0][0], dtype=np.float64)
    B = (np.sum(b1, axis=2) > 0).astype(np.float64)
    hid_list = mdp[nm - 1]["id"].get("hid", [])
    hid_arr = np.asarray(hid_list, dtype=np.int64).ravel() if hid_list else np.zeros(0, dtype=np.int64)
    nt = int(artifact.get("entry10_nt", 32))
    p_py = dem_atariiii_paths_to_hits_P(B, hid_arr, nt)
    np.testing.assert_allclose(
        p_py,
        np.asarray(artifact["P_mat"], dtype=np.float64),
        rtol=0.0,
        atol=1e-12,
    )


def test_DEM_AtariIII_entry10_driver_smoke():
    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii

        ctx = run_dem_atariiii(entry_stop=10)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    assert "MDP" in ctx and isinstance(ctx["MDP"], list)
    assert "P" in ctx
    assert np.asarray(ctx["P"], dtype=np.float64).shape[0] == 32
    assert np.asarray(ctx["P"], dtype=np.float64).ndim == 2
