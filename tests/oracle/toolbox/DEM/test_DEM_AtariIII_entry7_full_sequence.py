from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

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


def _mat_int(eng, expr: str) -> int:
    return int(np.asarray(eng.eval(expr), dtype=np.int64).reshape(-1)[0])


def _mat_float(eng, expr: str) -> float:
    return float(np.asarray(eng.eval(expr), dtype=np.float64).reshape(-1)[0])


def _mat_full_numeric(eng, expr: str) -> np.ndarray:
    eng.eval(f"rgms_tmp_val = {expr}; if issparse(rgms_tmp_val), rgms_tmp_val = full(rgms_tmp_val); end;", nargout=0)
    arr = np.asarray(eng.eval("rgms_tmp_val"), dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape((1, -1), order="F")
    return arr


def _mat_cell_scalar_list(eng, expr: str) -> list[int]:
    n = _mat_int(eng, f"numel({expr})")
    out = []
    for i in range(1, n + 1):
        out.append(_mat_int(eng, f"{expr}{{{i}}}(1)"))
    return out


def _mat_cell_vector_list(eng, expr: str) -> list[list[int]]:
    n = _mat_int(eng, f"numel({expr})")
    out: list[list[int]] = []
    for i in range(1, n + 1):
        v = np.asarray(eng.eval(f"{expr}{{{i}}}"), dtype=np.int64).ravel(order="F")
        out.append([int(x) for x in v.tolist()])
    return out


def _mat_cell_matrix_numeric(eng, expr: str) -> list[list[np.ndarray]]:
    nr = _mat_int(eng, f"size({expr},1)")
    nc = _mat_int(eng, f"size({expr},2)")
    out: list[list[np.ndarray]] = []
    for r in range(1, nr + 1):
        row: list[np.ndarray] = []
        for c in range(1, nc + 1):
            row.append(_mat_full_numeric(eng, f"{expr}{{{r},{c}}}"))
        out.append(row)
    return out


def _mat_groups(eng, expr: str) -> dict[int, list[np.ndarray]]:
    n_stream = _mat_int(eng, f"numel({expr})")
    out: dict[int, list[np.ndarray]] = {}
    for s in range(1, n_stream + 1):
        ng = _mat_int(eng, f"numel({expr}{{{s}}})")
        groups = []
        for g in range(1, ng + 1):
            v = np.asarray(eng.eval(f"{expr}{{{s}}}{{{g}}}"), dtype=np.int64).ravel(order="F")
            groups.append(v)
        out[s] = groups
    return out


def _pull_mdp_from_matlab(eng, mdp_expr: str) -> list[dict]:
    nm = _mat_int(eng, f"numel({mdp_expr})")
    out: list[dict] = []
    for n in range(1, nm + 1):
        na = _mat_int(eng, f"numel({mdp_expr}{{{n}}}.a)")
        nb = _mat_int(eng, f"numel({mdp_expr}{{{n}}}.b)")
        a_cells = [[_mat_full_numeric(eng, f"{mdp_expr}{{{n}}}.a{{{g}}}")] for g in range(1, na + 1)]
        b_cells = [[_mat_full_numeric(eng, f"{mdp_expr}{{{n}}}.b{{{f}}}")] for f in range(1, nb + 1)]
        mdp_n = {
            "G": _mat_groups(eng, f"{mdp_expr}{{{n}}}.G"),
            "T": _mat_float(eng, f"{mdp_expr}{{{n}}}.T"),
            "a": a_cells,
            "b": b_cells,
            "id": {
                "A": [[v] for v in _mat_cell_scalar_list(eng, f"{mdp_expr}{{{n}}}.id.A")],
                "D": _mat_cell_vector_list(eng, f"{mdp_expr}{{{n}}}.id.D"),
                "E": _mat_cell_vector_list(eng, f"{mdp_expr}{{{n}}}.id.E"),
            },
            "sA": [int(x) for x in np.asarray(eng.eval(f"{mdp_expr}{{{n}}}.sA"), dtype=np.int64).ravel(order="F").tolist()],
            "sB": [int(x) for x in np.asarray(eng.eval(f"{mdp_expr}{{{n}}}.sB"), dtype=np.int64).ravel(order="F").tolist()],
            "sC": [int(x) for x in np.asarray(eng.eval(f"{mdp_expr}{{{n}}}.sC"), dtype=np.int64).ravel(order="F").tolist()],
            "ss": {
                "D": _mat_cell_matrix_numeric(eng, f"{mdp_expr}{{{n}}}.ss.D"),
                "E": _mat_cell_matrix_numeric(eng, f"{mdp_expr}{{{n}}}.ss.E"),
                "ID": _mat_cell_matrix_numeric(eng, f"{mdp_expr}{{{n}}}.ss.ID"),
                "IE": _mat_cell_matrix_numeric(eng, f"{mdp_expr}{{{n}}}.ss.IE"),
            },
        }
        out.append(mdp_n)
    return out


def _pull_oseq_from_matlab(eng, expr: str) -> list[list[list[np.ndarray]]]:
    kmax = _mat_int(eng, f"numel({expr})")
    out: list[list[list[np.ndarray]]] = []
    for k in range(1, kmax + 1):
        nr = _mat_int(eng, f"size({expr}{{{k}}},1)")
        nc = _mat_int(eng, f"size({expr}{{{k}}},2)")
        o_k: list[list[np.ndarray]] = []
        for r in range(1, nr + 1):
            row: list[np.ndarray] = []
            for c in range(1, nc + 1):
                arr = _mat_full_numeric(eng, f"full({expr}{{{k}}}{{{r},{c}}})")
                if arr.ndim == 1:
                    arr = arr.reshape((-1, 1), order="F")
                if arr.ndim == 0:
                    arr = np.reshape(arr, (1, 1), order="F")
                row.append(arr)
            o_k.append(row)
        out.append(o_k)
    return out


def _unwrap_cell1(x):
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _to_tensor(x) -> np.ndarray:
    x = _unwrap_cell1(x)
    if sparse.issparse(x):
        x = x.toarray()
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 0:
        arr = np.reshape(arr, (1, 1), order="F")
    return arr


def _canonical_tensor_shape(arr: np.ndarray) -> np.ndarray:
    out = arr
    while out.ndim > 2 and out.shape[-1] == 1:
        out = np.reshape(out, out.shape[:-1], order="F")
    return out


def _assert_array_equal_exact(py: np.ndarray, mat: np.ndarray, label: str, k: int) -> None:
    py = _canonical_tensor_shape(py)
    mat = _canonical_tensor_shape(mat)
    if py.shape != mat.shape:
        raise AssertionError(f"call={k} {label}: shape py={py.shape} mat={mat.shape}")
    if np.allclose(py, mat, rtol=0.0, atol=1e-12):
        return
    d = np.abs(py - mat)
    idx = np.argwhere(d > 1e-12)
    i = tuple(int(v) for v in idx[0].tolist())
    raise AssertionError(f"call={k} {label}: value py={float(py[i])} mat={float(mat[i])} at {i}")


def _assert_mdp_full_equal(py_mdp: list[dict], mat_mdp: list[dict], k: int) -> None:
    if len(py_mdp) != len(mat_mdp):
        raise AssertionError(f"call={k} level-count py={len(py_mdp)} mat={len(mat_mdp)}")
    for n in range(len(py_mdp)):
        p = py_mdp[n]
        m = mat_mdp[n]
        if not np.isclose(float(p["T"]), float(m["T"]), rtol=0.0, atol=1e-12):
            raise AssertionError(f"call={k} lev={n+1} field=T py={float(p['T'])} mat={float(m['T'])}")
        for field in ("sA", "sB", "sC"):
            if list(p[field]) != list(m[field]):
                raise AssertionError(f"call={k} lev={n+1} field={field} mismatch")
        for field in ("A", "D", "E"):
            if p["id"][field] != m["id"][field]:
                raise AssertionError(f"call={k} lev={n+1} id.{field} mismatch")
        if p["G"].keys() != m["G"].keys():
            raise AssertionError(f"call={k} lev={n+1} G key mismatch")
        for sk in p["G"].keys():
            pg = p["G"][sk]
            mg = m["G"][sk]
            if len(pg) != len(mg):
                raise AssertionError(f"call={k} lev={n+1} G[{sk}] group-count mismatch")
            for gi in range(len(pg)):
                if not np.array_equal(np.asarray(pg[gi], dtype=np.int64), np.asarray(mg[gi], dtype=np.int64)):
                    raise AssertionError(f"call={k} lev={n+1} G[{sk}]{{{gi+1}}} mismatch")
        if len(p["a"]) != len(m["a"]):
            raise AssertionError(f"call={k} lev={n+1} a-count py={len(p['a'])} mat={len(m['a'])}")
        if len(p["b"]) != len(m["b"]):
            raise AssertionError(f"call={k} lev={n+1} b-count py={len(p['b'])} mat={len(m['b'])}")
        for g in range(len(p["a"])):
            pa = _to_tensor(p["a"][g])
            ma = _to_tensor(m["a"][g])
            _assert_array_equal_exact(pa, ma, f"lev={n+1} a[{g+1}]", k)
        for f in range(len(p["b"])):
            pb = _to_tensor(p["b"][f])
            mb = _to_tensor(m["b"][f])
            _assert_array_equal_exact(pb, mb, f"lev={n+1} b[{f+1}]", k)
        for ss_field in ("D", "E", "ID", "IE"):
            p_ss = p["ss"][ss_field]
            m_ss = m["ss"][ss_field]
            if len(p_ss) != len(m_ss):
                raise AssertionError(f"call={k} lev={n+1} ss.{ss_field} row-count mismatch")
            for i in range(len(p_ss)):
                if len(p_ss[i]) != len(m_ss[i]):
                    raise AssertionError(f"call={k} lev={n+1} ss.{ss_field} col-count mismatch at row={i+1}")
                for j in range(len(p_ss[i])):
                    ps = _to_tensor(p_ss[i][j])
                    ms = _to_tensor(m_ss[i][j])
                    _assert_array_equal_exact(ps, ms, f"lev={n+1} ss.{ss_field}[{i+1},{j+1}]", k)


def _assert_no_top_level_xp(py_mdp: list[dict], k: int) -> None:
    for n, mdp_n in enumerate(py_mdp, start=1):
        if "X" in mdp_n or "P" in mdp_n:
            raise AssertionError(f"call={k} lev={n} unexpected top-level X/P fields present")


def _build_matlab_entry7_sequence(eng, training_t: int) -> None:
    eng.eval(
        "rng(0,'twister'); "
        "Nr = 12; Nc = 9; Sc = 9; Nd = 4; C = 32; "
        "[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0); "
        "S = ones(4,3); S(1,:) = [Nr,Nc,1]; "
        f"GDP.tau = 1; GDP.T = {int(training_t)}; "
        "PDP = spm_MDP_generate(GDP); "
        "MDP0 = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc); "
        "Nm = numel(MDP0); Ne = max(2^(Nm - 1),1); "
        "for n = 1:Nm, "
        "for g = 1:numel(MDP0{n}.a), MDP0{n}.a{g} = []; end; "
        "for f = 1:numel(MDP0{n}.b), MDP0{n}.b{f} = []; end; "
        "end; "
        "r = find(PDP.o(GDP.id.reward,:) > 1); "
        "c = find(PDP.o(GDP.id.contraint,:) > 1); "
        "Oseq = {}; "
        "for i = 1:numel(r), "
        "s = c(find(c < r(i),1,'last')); "
        "t = (s + Ne):(r(i) + Ne); "
        "if numel(t), "
        "for s = 1:Ne, "
        "Oseq{end+1} = PDP.O(:,t + s); "
        "end; "
        "end; "
        "end; "
        "MDPm = MDP0;",
        nargout=0,
    )


@pytest.mark.slow
def test_DEM_AtariIII_entry7_full_sequence_from_matlab_boundary_oracle(dem_eng):
    _build_matlab_entry7_sequence(dem_eng, training_t=1000)
    mdp_py = _pull_mdp_from_matlab(dem_eng, "MDP0")
    o_seq = _pull_oseq_from_matlab(dem_eng, "Oseq")
    n_calls = _mat_int(dem_eng, "numel(Oseq)")
    assert n_calls == len(o_seq)
    for k in range(1, n_calls + 1):
        dem_eng.eval(f"MDPm = spm_merge_structure_learning(Oseq{{{k}}},MDPm);", nargout=0)
        mdp_py = spm_merge_structure_learning(o_seq[k - 1], mdp_py)
        mdp_mat = _pull_mdp_from_matlab(dem_eng, "MDPm")
        _assert_mdp_full_equal(mdp_py, mdp_mat, k)
        _assert_no_top_level_xp(mdp_py, k)
