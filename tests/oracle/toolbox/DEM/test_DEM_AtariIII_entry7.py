import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from scipy import sparse

from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from python_src.toolbox.DEM.DEM_AtariIII import _entry7_assimilate_sequences, run_dem_atariiii


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


def _matlab_rand_stream_after_reset(dem_eng, n: int) -> list[float]:
    dem_eng.eval(f"rng(0,'twister'); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(dem_eng.eval("rgms_rand_buf"), dtype=np.float64).ravel(order="F").tolist()


def _matlab_entry7_signature(dem_eng, training_t: int) -> tuple[np.ndarray, np.ndarray]:
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
        "sigA = zeros(0,6); sigB = zeros(0,6); "
        "for n = 1:numel(MDP), "
        "for g = 1:numel(MDP{n}.a), "
        "x = MDP{n}.a{g}; sz = size(x); p = 1; if numel(sz) >= 3, p = prod(sz(3:end)); end; "
        "sigA(end+1,:) = [n g sz(1) sz(2) p sum(x(:))]; "
        "end; "
        "for f = 1:numel(MDP{n}.b), "
        "x = MDP{n}.b{f}; sz = size(x); p = 1; if numel(sz) >= 3, p = prod(sz(3:end)); end; "
        "sigB(end+1,:) = [n f sz(1) sz(2) p sum(x(:))]; "
        "end; "
        "end;",
        nargout=0,
    )
    sig_a = np.asarray(dem_eng.eval("sigA"), dtype=np.float64)
    sig_b = np.asarray(dem_eng.eval("sigB"), dtype=np.float64)
    return sig_a, sig_b


def _matlab_entry7_first_merge_signature(
    dem_eng, training_t: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        "did = 0; no_first = []; "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + Ne):(r(i) + Ne); "
        "if numel(t), "
        "for s = 1:Ne, "
        "if isempty(no_first), no_first = cellfun(@(x) size(x,1), PDP.O(:,t(1) + s)); end; "
        "MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP); "
        "did = 1; break; "
        "end; "
        "if did, break; end; "
        "end; "
        "if did, break; end; "
        "end; "
        "sigA = zeros(0,6); sigB = zeros(0,6); "
        "for n = 1:numel(MDP), "
        "for g = 1:numel(MDP{n}.a), "
        "x = MDP{n}.a{g}; sz = size(x); p = 1; if numel(sz) >= 3, p = prod(sz(3:end)); end; "
        "sigA(end+1,:) = [n g sz(1) sz(2) p sum(x(:))]; "
        "end; "
        "for f = 1:numel(MDP{n}.b), "
        "x = MDP{n}.b{f}; sz = size(x); p = 1; if numel(sz) >= 3, p = prod(sz(3:end)); end; "
        "sigB(end+1,:) = [n f sz(1) sz(2) p sum(x(:))]; "
        "end; "
        "end;",
        nargout=0,
    )
    sig_a = np.asarray(dem_eng.eval("sigA"), dtype=np.float64)
    sig_b = np.asarray(dem_eng.eval("sigB"), dtype=np.float64)
    no_first = np.asarray(dem_eng.eval("no_first"), dtype=np.float64).ravel(order="F")
    return sig_a, sig_b, no_first


def _unwrap_cell_payload(x):
    if isinstance(x, list):
        if len(x) == 0:
            return np.zeros((0, 0), dtype=np.float64)
        if len(x) == 1:
            return x[0]
    return x


def _python_mdp_signature(mdp: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    sig_a_rows = []
    sig_b_rows = []
    for n, mdp_n in enumerate(mdp, start=1):
        for g, ag in enumerate(mdp_n["a"], start=1):
            x = _unwrap_cell_payload(ag)
            if sparse.issparse(x):
                x = x.toarray()
            x = np.asarray(x, dtype=np.float64)
            if x.ndim == 0:
                sz = (1, 1, 1)
            elif x.ndim == 1:
                sz = (x.shape[0], 1, 1)
            elif x.ndim == 2:
                sz = (x.shape[0], x.shape[1], 1)
            else:
                sz = (x.shape[0], x.shape[1], int(np.prod(x.shape[2:])))
            sig_a_rows.append([n, g, sz[0], sz[1], sz[2], float(np.sum(x))])
        for f, bf in enumerate(mdp_n["b"], start=1):
            x = _unwrap_cell_payload(bf)
            if sparse.issparse(x):
                x = x.toarray()
            x = np.asarray(x, dtype=np.float64)
            if x.ndim == 0:
                sz = (1, 1, 1)
            elif x.ndim == 1:
                sz = (x.shape[0], 1, 1)
            elif x.ndim == 2:
                sz = (x.shape[0], x.shape[1], 1)
            else:
                sz = (x.shape[0], x.shape[1], int(np.prod(x.shape[2:])))
            sig_b_rows.append([n, f, sz[0], sz[1], sz[2], float(np.sum(x))])
    sig_a = np.asarray(sig_a_rows, dtype=np.float64) if sig_a_rows else np.zeros((0, 6), dtype=np.float64)
    sig_b = np.asarray(sig_b_rows, dtype=np.float64) if sig_b_rows else np.zeros((0, 6), dtype=np.float64)
    return sig_a, sig_b


def _assert_sig_close(name: str, p_sig: np.ndarray, m_sig: np.ndarray, atol: float = 1e-12) -> None:
    if p_sig.shape != m_sig.shape:
        raise AssertionError(f"{name} shape mismatch: python={p_sig.shape} matlab={m_sig.shape}")
    if np.allclose(p_sig, m_sig, rtol=0.0, atol=atol):
        return
    diff = np.abs(p_sig - m_sig)
    idx = np.argwhere(diff > atol)
    rows = []
    for k in range(min(12, idx.shape[0])):
        i, j = idx[k]
        rows.append(
            f"(row={int(i)}, col={int(j)}, py={float(p_sig[i,j])}, mat={float(m_sig[i,j])}, "
            f"key_n={int(p_sig[i,0])}, key_idx={int(p_sig[i,1])})"
        )
    raise AssertionError(
        f"{name} mismatch count={int(idx.shape[0])}/{int(p_sig.size)}; "
        f"first_diffs={'; '.join(rows)}"
    )


def _matlab_eval_scalar(dem_eng, expr: str) -> int:
    return int(np.asarray(dem_eng.eval(expr), dtype=np.int64).reshape(-1)[0])


def _matlab_cell_scalar_list(dem_eng, cell_expr: str) -> list[int]:
    n = _matlab_eval_scalar(dem_eng, f"numel({cell_expr})")
    out = []
    for i in range(1, n + 1):
        out.append(_matlab_eval_scalar(dem_eng, f"{cell_expr}{{{i}}}(1)"))
    return out


def _matlab_cell_vector_list(dem_eng, cell_expr: str) -> list[tuple[int, ...]]:
    n = _matlab_eval_scalar(dem_eng, f"numel({cell_expr})")
    out: list[tuple[int, ...]] = []
    for i in range(1, n + 1):
        v = np.asarray(dem_eng.eval(f"{cell_expr}{{{i}}}"), dtype=np.int64).ravel(order="F")
        out.append(tuple(int(x) for x in v.tolist()))
    return out


def _matlab_cell_vector_cells_2d(dem_eng, cell_expr: str) -> list[list[tuple[int, ...]]]:
    nr = _matlab_eval_scalar(dem_eng, f"size({cell_expr},1)")
    nc = _matlab_eval_scalar(dem_eng, f"size({cell_expr},2)")
    out: list[list[tuple[int, ...]]] = []
    for r in range(1, nr + 1):
        row: list[tuple[int, ...]] = []
        for c in range(1, nc + 1):
            v = np.asarray(dem_eng.eval(f"{cell_expr}{{{r},{c}}}"), dtype=np.int64).ravel(order="F")
            row.append(tuple(int(x) for x in v.tolist()))
        out.append(row)
    return out


def _matlab_pull_numeric_cell(dem_eng, expr: str) -> np.ndarray:
    dem_eng.eval(
        f"rgms_tmp_cell = {expr}; if issparse(rgms_tmp_cell), rgms_tmp_cell = full(rgms_tmp_cell); end; rgms_tmp_mx = rgms_tmp_cell;",
        nargout=0,
    )
    return np.asarray(dem_eng.eval("rgms_tmp_mx"), dtype=np.float64)


def _matlab_pull_o_cell(dem_eng, expr: str) -> np.ndarray:
    dem_eng.eval(f"rgms_tmp_o = full({expr});", nargout=0)
    arr = np.asarray(dem_eng.eval("rgms_tmp_o"), dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape((-1, 1), order="F")
    if arr.ndim == 0:
        arr = np.reshape(arr, (1, 1), order="F")
    return arr


def _matlab_first_merge_dump(dem_eng, training_t: int) -> list[dict]:
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
        "did = 0; no_first = []; "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + Ne):(r(i) + Ne); "
        "if numel(t), "
        "for s = 1:Ne, "
        "if isempty(no_first), no_first = cellfun(@(x) size(x,1), PDP.O(:,t(1) + s)); end; "
        "MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP); "
        "did = 1; break; "
        "end; "
        "if did, break; end; "
        "end; "
        "if did, break; end; "
        "end;",
        nargout=0,
    )
    nm = _matlab_eval_scalar(dem_eng, "numel(MDP)")
    out: list[dict] = []
    for n in range(1, nm + 1):
        na = _matlab_eval_scalar(dem_eng, f"numel(MDP{{{n}}}.a)")
        nb = _matlab_eval_scalar(dem_eng, f"numel(MDP{{{n}}}.b)")
        a_cells = [_matlab_pull_numeric_cell(dem_eng, f"MDP{{{n}}}.a{{{g}}}") for g in range(1, na + 1)]
        b_cells = [_matlab_pull_numeric_cell(dem_eng, f"MDP{{{n}}}.b{{{f}}}") for f in range(1, nb + 1)]
        sA = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sA"), dtype=np.int64).ravel(order="F")
        sB = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sB"), dtype=np.int64).ravel(order="F")
        sC = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sC"), dtype=np.int64).ravel(order="F")
        idA = _matlab_cell_scalar_list(dem_eng, f"MDP{{{n}}}.id.A")
        idD = _matlab_cell_vector_list(dem_eng, f"MDP{{{n}}}.id.D")
        idE = _matlab_cell_vector_list(dem_eng, f"MDP{{{n}}}.id.E")
        out.append(
            {
                "a": a_cells,
                "b": b_cells,
                "sA": sA,
                "sB": sB,
                "sC": sC,
                "idA": idA,
                "idD": idD,
                "idE": idE,
            }
        )
    return out


def _matlab_premerge_dump(dem_eng, training_t: int) -> list[dict]:
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
        "end;",
        nargout=0,
    )
    nm = _matlab_eval_scalar(dem_eng, "numel(MDP)")
    out: list[dict] = []
    for n in range(1, nm + 1):
        na = _matlab_eval_scalar(dem_eng, f"numel(MDP{{{n}}}.a)")
        nb = _matlab_eval_scalar(dem_eng, f"numel(MDP{{{n}}}.b)")
        a_cells = [_matlab_pull_numeric_cell(dem_eng, f"MDP{{{n}}}.a{{{g}}}") for g in range(1, na + 1)]
        b_cells = [_matlab_pull_numeric_cell(dem_eng, f"MDP{{{n}}}.b{{{f}}}") for f in range(1, nb + 1)]
        sA = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sA"), dtype=np.int64).ravel(order="F")
        sB = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sB"), dtype=np.int64).ravel(order="F")
        sC = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sC"), dtype=np.int64).ravel(order="F")
        idA = _matlab_cell_scalar_list(dem_eng, f"MDP{{{n}}}.id.A")
        idD = _matlab_cell_vector_list(dem_eng, f"MDP{{{n}}}.id.D")
        idE = _matlab_cell_vector_list(dem_eng, f"MDP{{{n}}}.id.E")
        out.append(
            {
                "a": a_cells,
                "b": b_cells,
                "sA": sA,
                "sB": sB,
                "sC": sC,
                "idA": idA,
                "idD": idD,
                "idE": idE,
            }
        )
    return out


def _matlab_entry4_meta_dump(dem_eng, training_t: int) -> list[dict]:
    dem_eng.eval(
        "rng(0,'twister'); "
        "Nr = 12; Nc = 9; Sc = 9; Nd = 4; C = 32; "
        "[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0); "
        "S = ones(4,3); S(1,:) = [Nr,Nc,1]; "
        f"GDP.tau = 1; GDP.T = {int(training_t)}; "
        "PDP = spm_MDP_generate(GDP); "
        "MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);",
        nargout=0,
    )
    nm = _matlab_eval_scalar(dem_eng, "numel(MDP)")
    out: list[dict] = []
    for n in range(1, nm + 1):
        idA = _matlab_cell_scalar_list(dem_eng, f"MDP{{{n}}}.id.A")
        sB = np.asarray(dem_eng.eval(f"MDP{{{n}}}.sB"), dtype=np.int64).ravel(order="F").tolist()
        g_streams = _matlab_eval_scalar(dem_eng, f"numel(MDP{{{n}}}.G)")
        g_rows: list[list[tuple[int, ...]]] = []
        for s in range(1, g_streams + 1):
            g_rows.append(_matlab_cell_vector_cells_2d(dem_eng, f"MDP{{{n}}}.G{{{s}}}"))
        out.append({"idA": idA, "sB": sB, "G": g_rows})
    return out


def _python_first_merge_dump(training_t: int, rand_seq: list[float]) -> list[dict]:
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = str(training_t)
    try:
        with patch("numpy.random.rand", side_effect=rand_seq):
            ctx = run_dem_atariiii(entry_stop=6)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    t = np.asarray(ctx["entry6_windows"][0]["t"], dtype=np.int64).ravel(order="F")
    cols = (t + 1).astype(np.int64)
    o_seg = [[ctx["PDP"]["O"][g][int(c) - 1] for c in cols.tolist()] for g in range(len(ctx["PDP"]["O"]))]
    mdp = spm_merge_structure_learning(o_seg, ctx["MDP"])
    out: list[dict] = []
    for mdp_n in mdp:
        a_cells = []
        for x in mdp_n["a"]:
            x = _unwrap_cell_payload(x)
            if sparse.issparse(x):
                x = x.toarray()
            a_cells.append(np.asarray(x, dtype=np.float64))
        b_cells = []
        for x in mdp_n["b"]:
            x = _unwrap_cell_payload(x)
            if sparse.issparse(x):
                x = x.toarray()
            b_cells.append(np.asarray(x, dtype=np.float64))
        idA = [int(np.asarray(v).ravel(order="F")[0]) for v in mdp_n["id"]["A"]]
        idD = [tuple(int(x) for x in np.asarray(v).ravel(order="F").tolist()) for v in mdp_n["id"]["D"]]
        idE = [tuple(int(x) for x in np.asarray(v).ravel(order="F").tolist()) for v in mdp_n["id"]["E"]]
        out.append(
            {
                "a": a_cells,
                "b": b_cells,
                "sA": np.asarray(mdp_n["sA"], dtype=np.int64).ravel(order="F"),
                "sB": np.asarray(mdp_n["sB"], dtype=np.int64).ravel(order="F"),
                "sC": np.asarray(mdp_n["sC"], dtype=np.int64).ravel(order="F"),
                "idA": idA,
                "idD": idD,
                "idE": idE,
            }
        )
    return out


def _python_premerge_dump(training_t: int, rand_seq: list[float]) -> list[dict]:
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = str(training_t)
    try:
        with patch("numpy.random.rand", side_effect=rand_seq):
            ctx = run_dem_atariiii(entry_stop=6)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    mdp = ctx["MDP"]
    out: list[dict] = []
    for mdp_n in mdp:
        a_cells = []
        for x in mdp_n["a"]:
            x = _unwrap_cell_payload(x)
            if sparse.issparse(x):
                x = x.toarray()
            a_cells.append(np.asarray(x, dtype=np.float64))
        b_cells = []
        for x in mdp_n["b"]:
            x = _unwrap_cell_payload(x)
            if sparse.issparse(x):
                x = x.toarray()
            b_cells.append(np.asarray(x, dtype=np.float64))
        idA = [int(np.asarray(v).ravel(order="F")[0]) for v in mdp_n["id"]["A"]]
        idD = [tuple(int(x) for x in np.asarray(v).ravel(order="F").tolist()) for v in mdp_n["id"]["D"]]
        idE = [tuple(int(x) for x in np.asarray(v).ravel(order="F").tolist()) for v in mdp_n["id"]["E"]]
        out.append(
            {
                "a": a_cells,
                "b": b_cells,
                "sA": np.asarray(mdp_n["sA"], dtype=np.int64).ravel(order="F"),
                "sB": np.asarray(mdp_n["sB"], dtype=np.int64).ravel(order="F"),
                "sC": np.asarray(mdp_n["sC"], dtype=np.int64).ravel(order="F"),
                "idA": idA,
                "idD": idD,
                "idE": idE,
            }
        )
    return out


def _python_entry4_meta_dump(training_t: int, rand_seq: list[float]) -> list[dict]:
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = str(training_t)
    try:
        with patch("numpy.random.rand", side_effect=rand_seq):
            ctx = run_dem_atariiii(entry_stop=4)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    out: list[dict] = []
    for mdp_n in ctx["MDP"]:
        idA = [int(np.asarray(v).ravel(order="F")[0]) for v in mdp_n["id"]["A"]]
        sB = [int(v) for v in np.asarray(mdp_n["sB"], dtype=np.int64).ravel(order="F").tolist()]
        g_rows: list[list[tuple[int, ...]]] = []
        g_streams = len(mdp_n["G"])
        for s in range(1, g_streams + 1):
            stream = mdp_n["G"][s]
            row: list[tuple[int, ...]] = []
            for cell in stream:
                v = np.asarray(cell, dtype=np.int64).ravel(order="F")
                row.append(tuple(int(x) for x in v.tolist()))
            g_rows.append([*row])
        out.append({"idA": idA, "sB": sB, "G": g_rows})
    return out


def _matlab_entry7_level1_boundary_and_post(dem_eng, training_t: int) -> tuple[list[list[np.ndarray]], dict, list[dict]]:
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
        "did = 0; "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + Ne):(r(i) + Ne); "
        "if numel(t), "
        "for s = 1:Ne, "
        "Oseg = PDP.O(:,t + s); "
        "MDP1 = {MDP{1}}; "
        "MDP1_post = spm_merge_structure_learning(Oseg,MDP1); "
        "did = 1; break; "
        "end; "
        "if did, break; end; "
        "end; "
        "if did, break; end; "
        "end;",
        nargout=0,
    )

    nr = _matlab_eval_scalar(dem_eng, "size(Oseg,1)")
    nc = _matlab_eval_scalar(dem_eng, "size(Oseg,2)")
    o_seg: list[list[np.ndarray]] = []
    for r in range(1, nr + 1):
        row: list[np.ndarray] = []
        for c in range(1, nc + 1):
            row.append(_matlab_pull_o_cell(dem_eng, f"Oseg{{{r},{c}}}"))
        o_seg.append(row)

    g_streams = _matlab_eval_scalar(dem_eng, "numel(MDP1{1}.G)")
    g_map: dict[int, list[np.ndarray]] = {}
    for s in range(1, g_streams + 1):
        ng = _matlab_eval_scalar(dem_eng, f"numel(MDP1{{1}}.G{{{s}}})")
        g_map[s] = []
        for g in range(1, ng + 1):
            v = np.asarray(dem_eng.eval(f"MDP1{{1}}.G{{{s}}}{{{g}}}"), dtype=np.int64).ravel(order="F")
            g_map[s].append(v)

    na = _matlab_eval_scalar(dem_eng, "numel(MDP1{1}.a)")
    nb = _matlab_eval_scalar(dem_eng, "numel(MDP1{1}.b)")
    a_cells = [_matlab_pull_numeric_cell(dem_eng, f"MDP1{{1}}.a{{{g}}}") for g in range(1, na + 1)]
    b_cells = [_matlab_pull_numeric_cell(dem_eng, f"MDP1{{1}}.b{{{f}}}") for f in range(1, nb + 1)]
    idA = _matlab_cell_scalar_list(dem_eng, "MDP1{1}.id.A")
    idD = _matlab_cell_vector_list(dem_eng, "MDP1{1}.id.D")
    idE = _matlab_cell_vector_list(dem_eng, "MDP1{1}.id.E")
    mdp1_pre = {
        "G": g_map,
        "T": float(np.asarray(dem_eng.eval("MDP1{1}.T"), dtype=np.float64).reshape(-1)[0]),
        "a": [[a_cells[g]] for g in range(len(a_cells))],
        "b": [[b_cells[f]] for f in range(len(b_cells))],
        "id": {"A": [[int(v)] for v in idA], "D": [list(v) for v in idD], "E": [list(v) for v in idE]},
        "sA": np.asarray(dem_eng.eval("MDP1{1}.sA"), dtype=np.int64).ravel(order="F").tolist(),
        "sB": np.asarray(dem_eng.eval("MDP1{1}.sB"), dtype=np.int64).ravel(order="F").tolist(),
        "sC": np.asarray(dem_eng.eval("MDP1{1}.sC"), dtype=np.int64).ravel(order="F").tolist(),
        "ss": {"D": [[None]], "E": [[None]], "ID": [[None]], "IE": [[None]]},
    }

    m_post = [
        {
            "a": [_matlab_pull_numeric_cell(dem_eng, f"MDP1_post{{1}}.a{{{g}}}") for g in range(1, na + 1)],
            "b": [_matlab_pull_numeric_cell(dem_eng, f"MDP1_post{{1}}.b{{{f}}}") for f in range(1, nb + 1)],
            "sA": np.asarray(dem_eng.eval("MDP1_post{1}.sA"), dtype=np.int64).ravel(order="F"),
            "sB": np.asarray(dem_eng.eval("MDP1_post{1}.sB"), dtype=np.int64).ravel(order="F"),
            "sC": np.asarray(dem_eng.eval("MDP1_post{1}.sC"), dtype=np.int64).ravel(order="F"),
            "idA": _matlab_cell_scalar_list(dem_eng, "MDP1_post{1}.id.A"),
            "idD": _matlab_cell_vector_list(dem_eng, "MDP1_post{1}.id.D"),
            "idE": _matlab_cell_vector_list(dem_eng, "MDP1_post{1}.id.E"),
        }
    ]
    return o_seg, mdp1_pre, m_post


def _assert_first_merge_dump_match(p_dump: list[dict], m_dump: list[dict]) -> None:
    issues: list[str] = []
    if len(p_dump) != len(m_dump):
        raise AssertionError(f"level count mismatch: py={len(p_dump)} mat={len(m_dump)}")
    for n in range(len(p_dump)):
        p = p_dump[n]
        m = m_dump[n]
        for field in ("sA", "sB", "sC"):
            if not np.array_equal(p[field], m[field]):
                issues.append(f"lev={n+1} field={field} mismatch")
        for field in ("idA", "idD", "idE"):
            if p[field] != m[field]:
                issues.append(f"lev={n+1} field={field} mismatch")
        if len(p["a"]) != len(m["a"]):
            issues.append(f"lev={n+1} a-count py={len(p['a'])} mat={len(m['a'])}")
        if len(p["b"]) != len(m["b"]):
            issues.append(f"lev={n+1} b-count py={len(p['b'])} mat={len(m['b'])}")
        for g in range(min(len(p["a"]), len(m["a"]))):
            pa = p["a"][g]
            ma = m["a"][g]
            if pa.size == 1 and ma.size == 1:
                if not np.allclose(pa.reshape(-1), ma.reshape(-1), rtol=0.0, atol=1e-12):
                    issues.append(
                        f"lev={n+1} a[{g+1}] scalar py={float(pa.reshape(-1)[0])} mat={float(ma.reshape(-1)[0])}"
                    )
                continue
            if pa.shape != ma.shape:
                issues.append(
                    f"lev={n+1} a[{g+1}] shape py={pa.shape} mat={ma.shape} sum_py={float(np.sum(pa))} sum_mat={float(np.sum(ma))}"
                )
            if pa.shape == ma.shape and not np.allclose(pa, ma, rtol=0.0, atol=1e-12):
                d = np.abs(pa - ma)
                idx = np.argwhere(d > 1e-12)
                if idx.size:
                    i0, j0 = idx[0]
                    issues.append(
                        f"lev={n+1} a[{g+1}] value py={float(pa[i0,j0])} mat={float(ma[i0,j0])} at ({int(i0)},{int(j0)})"
                    )
        for f in range(min(len(p["b"]), len(m["b"]))):
            pb = p["b"][f]
            mb = m["b"][f]
            if pb.size == 1 and mb.size == 1:
                if not np.allclose(pb.reshape(-1), mb.reshape(-1), rtol=0.0, atol=1e-12):
                    issues.append(
                        f"lev={n+1} b[{f+1}] scalar py={float(pb.reshape(-1)[0])} mat={float(mb.reshape(-1)[0])}"
                    )
                continue
            if pb.shape != mb.shape:
                issues.append(
                    f"lev={n+1} b[{f+1}] shape py={pb.shape} mat={mb.shape} sum_py={float(np.sum(pb))} sum_mat={float(np.sum(mb))}"
                )
            if pb.shape == mb.shape and not np.allclose(pb, mb, rtol=0.0, atol=1e-12):
                d = np.abs(pb - mb)
                idx = np.argwhere(d > 1e-12)
                if idx.size:
                    loc = tuple(int(x) for x in idx[0].tolist())
                    issues.append(
                        f"lev={n+1} b[{f+1}] value py={float(pb[loc])} mat={float(mb[loc])} at {loc}"
                    )
    if issues:
        raise AssertionError("first-merge dump mismatch: " + "; ".join(issues[:40]))


@pytest.mark.slow
def test_DEM_AtariIII_entry7_premerge_boundary_dump_oracle(dem_eng):
    training_t = 1000
    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 5_000_000)
    m_dump = _matlab_premerge_dump(dem_eng, training_t)
    p_dump = _python_premerge_dump(training_t, rand_seq)
    _assert_first_merge_dump_match(p_dump, m_dump)


@pytest.mark.slow
def test_DEM_AtariIII_entry7_entry4_meta_parity_oracle(dem_eng):
    training_t = 1000
    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 5_000_000)
    m_meta = _matlab_entry4_meta_dump(dem_eng, training_t)
    p_meta = _python_entry4_meta_dump(training_t, rand_seq)
    assert len(p_meta) == len(m_meta)
    issues: list[str] = []
    for n in range(len(p_meta)):
        if p_meta[n]["idA"] != m_meta[n]["idA"]:
            issues.append(f"lev={n+1} idA mismatch")
        if p_meta[n]["sB"] != m_meta[n]["sB"]:
            issues.append(f"lev={n+1} sB mismatch")
        if p_meta[n]["G"] != m_meta[n]["G"]:
            issues.append(f"lev={n+1} G mismatch")
    if issues:
        raise AssertionError("entry4 meta mismatch: " + "; ".join(issues))


@pytest.mark.slow
def test_DEM_AtariIII_entry7_level1_isolated_boundary_oracle(dem_eng):
    o_seg, mdp1_pre, m_post = _matlab_entry7_level1_boundary_and_post(dem_eng, training_t=1000)
    p_post = spm_merge_structure_learning(o_seg, [mdp1_pre])
    p_dump = [
        {
            "a": [np.asarray(_unwrap_cell_payload(x), dtype=np.float64) for x in p_post[0]["a"]],
            "b": [np.asarray(_unwrap_cell_payload(x), dtype=np.float64) for x in p_post[0]["b"]],
            "sA": np.asarray(p_post[0]["sA"], dtype=np.int64).ravel(order="F"),
            "sB": np.asarray(p_post[0]["sB"], dtype=np.int64).ravel(order="F"),
            "sC": np.asarray(p_post[0]["sC"], dtype=np.int64).ravel(order="F"),
            "idA": [int(np.asarray(v).ravel(order="F")[0]) for v in p_post[0]["id"]["A"]],
            "idD": [tuple(int(x) for x in np.asarray(v).ravel(order="F").tolist()) for v in p_post[0]["id"]["D"]],
            "idE": [tuple(int(x) for x in np.asarray(v).ravel(order="F").tolist()) for v in p_post[0]["id"]["E"]],
        }
    ]
    _assert_first_merge_dump_match(p_dump, m_post)


@pytest.mark.slow
def test_DEM_AtariIII_entries_1_to_7_python_smoke():
    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx = run_dem_atariiii(entry_stop=7)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t
    required = {"GDP", "PDP", "MDP", "Nm", "Ne", "r", "c", "entry6_windows"}
    assert required.issubset(set(ctx.keys()))
    assert isinstance(ctx["MDP"], list)
    assert len(ctx["MDP"]) >= 1


@pytest.mark.slow
def test_DEM_AtariIII_entry7_merge_oracle_signature(dem_eng):
    training_t = 1000
    m_sig_a, m_sig_b = _matlab_entry7_signature(dem_eng, training_t)
    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 5_000_000)

    old_t = os.getenv("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_TRAINING_T"] = str(training_t)
    try:
        with patch("numpy.random.rand", side_effect=rand_seq):
            ctx = run_dem_atariiii(entry_stop=7)
    finally:
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    p_sig_a, p_sig_b = _python_mdp_signature(ctx["MDP"])
    _assert_sig_close("sigA", p_sig_a, m_sig_a)
    _assert_sig_close("sigB", p_sig_b, m_sig_b)


@pytest.mark.slow
def test_DEM_AtariIII_entry7_first_merge_oracle_signature(dem_eng):
    training_t = 1000
    m_sig_a, m_sig_b, _m_no_first = _matlab_entry7_first_merge_signature(dem_eng, training_t)
    rand_seq = _matlab_rand_stream_after_reset(dem_eng, 5_000_000)
    m_dump = _matlab_first_merge_dump(dem_eng, training_t)
    p_dump = _python_first_merge_dump(training_t, rand_seq)
    _assert_first_merge_dump_match(p_dump, m_dump)
    p_sig_a, p_sig_b = _python_mdp_signature(
        [
            {
                "a": p_dump[i]["a"],
                "b": p_dump[i]["b"],
            }
            for i in range(len(p_dump))
        ]
    )
    _assert_sig_close("first_merge_sigA", p_sig_a, m_sig_a)
    _assert_sig_close("first_merge_sigB", p_sig_b, m_sig_b)
