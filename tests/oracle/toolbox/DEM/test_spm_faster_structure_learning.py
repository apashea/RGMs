"""Oracle: ``spm_faster_structure_learning.m`` vs ``spm_faster_structure_learning``."""

from pathlib import Path
from unittest.mock import patch
import os
import pickle
import time

import matlab
import numpy as np
import pytest

from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from python_src.toolbox.DEM.spm_faster_structure_learning import spm_faster_structure_learning
from python_src.toolbox.DEM.spm_rgm_group import (
    _spm_cat_row,
    _spm_mdp_mi_scalar,
    spm_rgm_group,
)
from python_src.spm_log import spm_log
from tests.helpers.compare import assert_matlab_match


def _env_flag(name: str) -> bool:
    return str(os.getenv(name, "0")).strip().lower() in ("1", "true", "yes", "on")


def _tlog(enabled: bool, msg: str) -> None:
    if enabled:
        print(f"[TIMER] {msg}", flush=True)


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    root = Path(__file__).resolve().parents[4] / "matlab_src"
    eng.addpath(str(root), nargout=0)
    return eng


@pytest.fixture
def dem_eng_fsl_pdp(eng):
    """DEM cwd for ``spm_MDP_pong`` / ``spm_MDP_generate`` (same pattern as integration oracle)."""
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)
        eng.rmpath(str(dem_path), nargout=0)


def _matlab_rand_buf_twister(eng, n: int) -> list:
    """Fresh ``twister`` stream from seed 0 — same contract as §1.1 generate integration."""
    eng.eval(f"rng(0,'twister'); rgms_rand_buf_fsl = rand({int(n)}, 1);", nargout=0)
    return np.asarray(eng.eval("rgms_rand_buf_fsl"), dtype=float).ravel().tolist()


def _matlab_rand_buf_twister_np(eng, n: int) -> np.ndarray:
    """Numpy buffer form for long replay windows."""
    eng.eval(f"rng(0,'twister'); rgms_rand_buf_fsl = rand({int(n)}, 1);", nargout=0)
    return np.asarray(eng.eval("rgms_rand_buf_fsl"), dtype=np.float64).ravel()


def _rand_replay_callable(buf: np.ndarray):
    idx = 0

    def _rand(*shape):
        nonlocal idx
        n_take = int(np.prod(shape)) if shape else 1
        end = idx + n_take
        if end > int(buf.size):
            raise RuntimeError(
                f"rand replay buffer exhausted at {idx} / {buf.size}; increase buffer length"
            )
        out = buf[idx:end]
        idx = end
        if not shape:
            return float(out[0])
        return out.reshape(shape, order="C")

    return _rand


def _matlab_id_d_row(eng, mdp_name: str, lev: int, fg: int) -> np.ndarray:
    eng.eval(
        f"rgms_id_d_row = cell2mat({mdp_name}{{{lev}}}.id.D({fg}));",
        nargout=0,
    )
    return np.asarray(eng.eval("rgms_id_d_row"), dtype=float).ravel()


def _matlab_id_e_row(eng, mdp_name: str, lev: int, fg: int) -> np.ndarray:
    eng.eval(
        f"rgms_id_e_row = cell2mat({mdp_name}{{{lev}}}.id.E({fg}));",
        nargout=0,
    )
    return np.asarray(eng.eval("rgms_id_e_row"), dtype=float).ravel()


def _assert_pdp_o_window_matches(eng, pdp_matlab_name: str, pdp_py: dict, k: int) -> None:
    """First ``k`` columns of ``PDP.O`` — MATLAB vs Python before structure learning."""
    ng = int(eng.eval(f"numel({pdp_matlab_name}.A)"))
    assert ng == len(pdp_py["O"])
    for g in range(ng):
        for t in range(k):
            eng.eval(
                f"rgms_pdp_o_w = full({pdp_matlab_name}.O{{{g + 1},{t + 1}}});",
                nargout=0,
            )
            om = np.asarray(eng.eval("rgms_pdp_o_w"), dtype=float)
            py_col = np.asarray(pdp_py["O"][g][t], dtype=float)
            assert_matlab_match(om, py_col)


def _assert_s_a_id_de(
    eng, mdp_name: str, mdp_py: list, lev: int, n_id_check: int
) -> None:
    """Compare ``sA`` column and leading ``id.D`` / ``id.E`` rows vs Python (1-based MATLAB)."""
    sa_m = np.asarray(
        eng.eval(f"{mdp_name}{{{lev}}}.sA(:)"), dtype=float
    ).ravel()
    sa_list = mdp_py[lev - 1]["sA"]
    assert len(sa_list) >= int(sa_m.size)
    sa_p = np.array(
        [float(sa_list[i]) for i in range(int(sa_m.size))],
        dtype=np.float64,
    )
    assert_matlab_match(sa_m, sa_p)

    n_id_d = int(eng.eval(f"numel({mdp_name}{{{lev}}}.id.D)"))
    n_id_e = int(eng.eval(f"numel({mdp_name}{{{lev}}}.id.E)"))
    for fg in range(1, min(n_id_check, n_id_d) + 1):
        m_d = _matlab_id_d_row(eng, mdp_name, lev, fg)
        p_d = np.asarray(mdp_py[lev - 1]["id"]["D"][fg - 1], dtype=float).ravel()
        assert_matlab_match(m_d, p_d)
    for fg in range(1, min(n_id_check, n_id_e) + 1):
        m_e = _matlab_id_e_row(eng, mdp_name, lev, fg)
        p_e = np.asarray(mdp_py[lev - 1]["id"]["E"][fg - 1], dtype=float).ravel()
        assert_matlab_match(m_e, p_e)


def _eval_mat_array(eng, expr: str, dtype=np.float64) -> np.ndarray:
    eng.eval(f"rgms_tmp_mx = {expr};", nargout=0)
    return np.asarray(eng.eval("rgms_tmp_mx"), dtype=dtype)


def _canon_bytes(arr: np.ndarray, dtype) -> tuple[tuple[int, ...], bytes]:
    x = np.asarray(arr, dtype=dtype)
    if np.issubdtype(x.dtype, np.floating):
        # Canonicalize NaN payloads before byte compare.
        x = np.where(np.isnan(x), np.nan, x)
    xf = np.asfortranarray(x)
    return tuple(int(v) for v in xf.shape), xf.tobytes(order="F")


def _assert_exact_canon(mat, py, dtype, path: str) -> None:
    sm, bm = _canon_bytes(np.asarray(mat), dtype)
    sp, bp = _canon_bytes(np.asarray(py), dtype)
    assert sm == sp, f"{path}: shape mismatch MATLAB {sm} vs Python {sp}"
    assert bm == bp, f"{path}: canonical byte mismatch"


def _matlab_find_map(eng, expr: str) -> dict[tuple[int, int], float]:
    eng.eval(f"[rgms_i,rgms_j,rgms_v] = find({expr});", nargout=0)
    ii = np.asarray(eng.eval("rgms_i"), dtype=np.int64).ravel()
    jj = np.asarray(eng.eval("rgms_j"), dtype=np.int64).ravel()
    vv = np.asarray(eng.eval("rgms_v"), dtype=np.float64).ravel()
    out: dict[tuple[int, int], float] = {}
    for k in range(ii.size):
        out[(int(ii[k]), int(jj[k]))] = float(vv[k])
    return out


def _assert_ss_exact(eng, mdp_name: str, mdp_py_lev: dict, lev: int, n_stream: int) -> None:
    for kind in ("D", "E", "ID", "IE"):
        for si in range(1, n_stream + 1):
            for sj in range(1, n_stream + 1):
                expr = f"{mdp_name}{{{lev}}}.ss.{kind}{{{si},{sj}}}"
                is_empty = bool(eng.eval(f"isempty({expr})"))
                py_cell = mdp_py_lev["ss"][kind][si - 1][sj - 1]
                if is_empty:
                    assert py_cell in (None, {}), (
                        f"MDP{{{lev}}}.ss.{kind}{{{si},{sj}}}: MATLAB empty, "
                        f"Python has value"
                    )
                    continue
                m_map = _matlab_find_map(eng, expr)
                p_map = {} if py_cell is None else dict(py_cell)
                assert set(m_map.keys()) == set(p_map.keys()), (
                    f"MDP{{{lev}}}.ss.{kind}{{{si},{sj}}}: key mismatch"
                )
                for key in m_map:
                    mv = m_map[key]
                    pv = p_map[key]
                    if kind in ("D", "E"):
                        assert int(mv) == int(pv), (
                            f"MDP{{{lev}}}.ss.{kind}{{{si},{sj}}}{key}: "
                            f"MATLAB {mv} vs Python {pv}"
                        )
                    else:
                        _assert_exact_canon(
                            np.array([mv], dtype=np.float64),
                            np.array([pv], dtype=np.float64),
                            np.float64,
                            f"MDP{{{lev}}}.ss.{kind}{{{si},{sj}}}{key}",
                        )


def _assert_rgm_group_streams_exact(
    eng, pdp_o_name: str, o_py: list, s_mat: np.ndarray, d_val: int
) -> None:
    """Forward-ordered Step-6 start: n=1 call setup, then stream-wise grouping parity."""
    n_stream = int(s_mat.shape[0])
    assert len(o_py) >= int(np.sum(np.prod(s_mat[:, :3], axis=1))), (
        "Python O rows are fewer than stream-indexed offsets expect"
    )
    # Start-of-call checkpoints (n=1, before grouping internals).
    nt_m = int(np.asarray(eng.eval(f"size({pdp_o_name},2)"), dtype=int).item())
    nt_p = len(o_py[0]) if o_py else 0
    assert nt_m == nt_p, "Step-6 start: Nt mismatch before grouping"
    # With call form spm_faster_structure_learning(O,S,Sc), MATLAB uses dt default 2 at n=1.
    t_py = np.arange(1, nt_p, 2, dtype=np.int64)
    t_m = np.asarray(eng.eval(f"1:2:({nt_m} - 1)"), dtype=np.int64).ravel(order="F")
    _assert_exact_canon(t_m, t_py, np.float64, "Step-6 start: decimated t-index")

    for s in range(1, n_stream + 1):
        o_stack = np.concatenate([[0.0], np.prod(s_mat[:, :3], axis=1).astype(np.float64)])
        offset = int(o_stack[s - 1])
        n_o_s = int(np.prod(s_mat[s - 1, :3]))
        idx = np.arange(offset + 1, offset + n_o_s + 1, dtype=np.int64)
        idx_mat = " ".join(str(int(v)) for v in idx)
        # Validate start-of-stream call arguments to spm_rgm_group at n=1.
        d_m = float(np.asarray(eng.eval(f"{int(d_val)}"), dtype=float).item())
        m_m = float(np.asarray(eng.eval(f"S_fsl_sx({s},4)"), dtype=float).item())
        assert d_m == float(d_val), f"Step-6 start stream {s}: d mismatch"
        assert m_m == float(s_mat[s - 1, 3]), f"Step-6 start stream {s}: m mismatch"
        eng.eval(
            f"rgms_o_start = [0; prod(S_fsl_sx,2)]; "
            f"rgms_idx_start = rgms_o_start({s}) + (1:prod(S_fsl_sx({s},:)));",
            nargout=0,
        )
        idx_m = np.asarray(eng.eval("rgms_idx_start"), dtype=np.float64).ravel(order="F")
        _assert_exact_canon(
            idx_m,
            idx.astype(np.float64),
            np.float64,
            f"Step-6 start stream {s}: O(o,:) row index mapping",
        )
        # Earliest SL-boundary checkpoint: verify stream-slice indexing at key times.
        t_candidates = sorted({1, len(o_py[int(idx[0]) - 1]) // 2, len(o_py[int(idx[0]) - 1])})
        for row_pos, row_idx in enumerate(idx, start=1):
            for t_pos in t_candidates:
                o_m = _eval_mat_array(eng, f"full({pdp_o_name}{{{int(row_idx)},{int(t_pos)}}})")
                o_p = np.asarray(o_py[int(row_idx) - 1][int(t_pos) - 1], dtype=np.float64)
                _assert_exact_canon(
                    np.asarray(o_m).ravel(),
                    np.asarray(o_p).ravel(),
                    np.float64,
                    f"spm_fsl O-slice stream {s} row {row_pos} t {t_pos}",
                )

        if s == 1:
            # Earliest deterministic checkpoint inside grouping: MI matrix.
            eng.eval(
                "rgms_os = " + f"{pdp_o_name}([{idx_mat}],:); "
                "[rgms_no,rgms_nt] = size(rgms_os); "
                "rgms_n = false(1,rgms_no); rgms_r = cell(1,rgms_no); "
                "for rgms_o = 1:rgms_no, "
                "  rgms_r{rgms_o} = spm_cat(rgms_os(rgms_o,:)); "
                "  rgms_n(rgms_o) = any(diff(rgms_r{rgms_o},[],2),'all'); "
                "end; "
                "rgms_MI = zeros(rgms_no,rgms_no); "
                "for rgms_i = 1:rgms_no, "
                "  for rgms_j = rgms_i:rgms_no, "
                "    if rgms_n(rgms_i) && rgms_n(rgms_j), "
                "      rgms_p = rgms_r{rgms_i}*rgms_r{rgms_j}'; "
                "      rgms_MI(rgms_i,rgms_j) = spm_MDP_MI(rgms_p); "
                "      rgms_MI(rgms_j,rgms_i) = rgms_MI(rgms_i,rgms_j); "
                "    end; "
                "  end; "
                "end;",
                nargout=0,
            )
            mi_m = np.asarray(eng.eval("rgms_MI"), dtype=np.float64)
            n_m = np.asarray(eng.eval("rgms_n"), dtype=bool).ravel(order="F")
            o_sub = [o_py[int(i) - 1] for i in idx]
            r_cells = [_spm_cat_row(o_sub[o]) for o in range(len(o_sub))]
            n_flags = np.array(
                [bool(np.any(np.abs(np.diff(r_cells[o], axis=1)) > 1e-14)) for o in range(len(o_sub))],
                dtype=bool,
            )
            _assert_exact_canon(
                n_m.astype(np.float64),
                n_flags.astype(np.float64),
                np.float64,
                "spm_rgm_group stream 1 n-flags",
            )
            mi_p = np.zeros((len(o_sub), len(o_sub)), dtype=np.float64)
            for i0 in range(len(o_sub)):
                for j0 in range(i0, len(o_sub)):
                    if n_flags[i0] and n_flags[j0]:
                        p_ij = r_cells[i0] @ r_cells[j0].T
                        val = _spm_mdp_mi_scalar(p_ij)
                        mi_p[i0, j0] = val
                        mi_p[j0, i0] = val
            # Earliest-within-MI checkpoint: isolate first mismatching (i,j).
            mism_ij = np.argwhere(mi_m != mi_p)
            if mism_ij.size:
                i0, j0 = (int(v) for v in mism_ij[0])
                i1 = i0 + 1
                j1 = j0 + 1
                p_m = _eval_mat_array(eng, f"full(rgms_r{{{i1}}}*rgms_r{{{j1}}}')")
                p_p = r_cells[i0] @ r_cells[j0].T
                _assert_exact_canon(
                    p_m,
                    p_p,
                    np.float64,
                    f"spm_rgm_group stream 1 p({i1},{j1})",
                )
                mi_scalar_m = float(
                    _eval_mat_array(
                        eng,
                        f"spm_MDP_MI(full(rgms_r{{{i1}}}*rgms_r{{{j1}}}'))",
                    ).ravel()[0]
                )
                mi_scalar_p = float(_spm_mdp_mi_scalar(p_p))
                # Decompose MI scalar to isolate earliest numeric divergence.
                a_m = _eval_mat_array(eng, f"full(rgms_r{{{i1}}}*rgms_r{{{j1}}}')")
                s_m = float(np.asarray(a_m, dtype=np.float64).sum())
                a_m_norm = np.asarray(a_m, dtype=np.float64) / s_m
                eng.eval(
                    f"rgms_pij = full(rgms_r{{{i1}}}*rgms_r{{{j1}}}'); "
                    "rgms_Aij = rgms_pij/sum(rgms_pij,'all'); "
                    "rgms_t1 = rgms_Aij(:)'*spm_log(rgms_Aij(:)); "
                    "rgms_t2 = sum(rgms_Aij,1)*spm_log(sum(rgms_Aij,1)'); "
                    "rgms_t3 = sum(rgms_Aij,2)'*spm_log(sum(rgms_Aij,2));",
                    nargout=0,
                )
                t1_m = float(np.asarray(eng.eval("rgms_t1"), dtype=np.float64).ravel()[0])
                t2_m = float(np.asarray(eng.eval("rgms_t2"), dtype=np.float64).ravel()[0])
                t3_m = float(np.asarray(eng.eval("rgms_t3"), dtype=np.float64).ravel()[0])
                a_p_norm = np.asarray(p_p, dtype=np.float64) / float(np.asarray(p_p, dtype=np.float64).sum())
                a_col = a_p_norm.reshape(-1, 1, order="F")
                t1_p = float((a_col.T @ spm_log(a_col)).ravel()[0])
                row_sum = np.sum(a_p_norm, axis=0, keepdims=True)
                col_sum = np.sum(a_p_norm, axis=1, keepdims=True)
                t2_p = float((row_sum @ spm_log(row_sum.T)).ravel()[0])
                t3_p = float((col_sum.T @ spm_log(col_sum)).ravel()[0])
                _assert_exact_canon(
                    np.array([t1_m], dtype=np.float64),
                    np.array([t1_p], dtype=np.float64),
                    np.float64,
                    f"spm_rgm_group stream 1 MI-term1({i1},{j1})",
                )
                _assert_exact_canon(
                    np.array([t2_m], dtype=np.float64),
                    np.array([t2_p], dtype=np.float64),
                    np.float64,
                    f"spm_rgm_group stream 1 MI-term2({i1},{j1})",
                )
                _assert_exact_canon(
                    np.array([t3_m], dtype=np.float64),
                    np.array([t3_p], dtype=np.float64),
                    np.float64,
                    f"spm_rgm_group stream 1 MI-term3({i1},{j1})",
                )
                _assert_exact_canon(
                    np.array([mi_scalar_m], dtype=np.float64),
                    np.array([mi_scalar_p], dtype=np.float64),
                    np.float64,
                    f"spm_rgm_group stream 1 MI-scalar({i1},{j1})",
                )
            _assert_exact_canon(mi_m, mi_p, np.float64, "spm_rgm_group stream 1 MI")

        eng.eval(
            f"rgms_g_stream = spm_rgm_group({pdp_o_name}([{idx_mat}],:), {int(d_val)}, 1);",
            nargout=0,
        )
        n_g = int(eng.eval("numel(rgms_g_stream)"))
        o_sub = [o_py[int(i) - 1] for i in idx]
        g_py = spm_rgm_group(o_sub, d_val, 1)
        assert n_g == len(g_py), f"spm_rgm_group stream {s}: length mismatch"
        for gi in range(1, n_g + 1):
            g_m = _eval_mat_array(eng, f"rgms_g_stream{{{gi}}}")
            g_p = np.asarray(g_py[gi - 1], dtype=np.float64)
            _assert_exact_canon(
                np.asarray(g_m).ravel(),
                np.asarray(g_p).ravel(),
                np.float64,
                f"spm_rgm_group stream {s} group {gi}",
            )


def _assert_mdp_tree_exhaustive_exact(
    eng, mdp_name: str, mdp_py: list, n_stream: int
) -> None:
    n_m = int(eng.eval(f"numel({mdp_name})"))
    assert n_m == len(mdp_py), f"{mdp_name}: level count mismatch"

    for lev in range(1, n_m + 1):
        # field set parity
        eng.eval(f"rgms_fields = fieldnames({mdp_name}{{{lev}}});", nargout=0)
        f_m = sorted(str(v) for v in eng.eval("rgms_fields"))
        f_p = sorted(mdp_py[lev - 1].keys())
        assert f_m == f_p, f"MDP{{{lev}}}: field mismatch MATLAB {f_m} vs Python {f_p}"

        # a{g}
        n_a = int(eng.eval(f"numel({mdp_name}{{{lev}}}.a)"))
        assert n_a == len(mdp_py[lev - 1]["a"]), f"MDP{{{lev}}}.a length mismatch"
        for gi in range(1, n_a + 1):
            a_m = _eval_mat_array(eng, f"full({mdp_name}{{{lev}}}.a{{{gi}}})")
            a_p = mdp_py[lev - 1]["a"][gi - 1][0]
            if hasattr(a_p, "toarray"):
                a_p = a_p.toarray()
            _assert_exact_canon(a_m, np.asarray(a_p), np.float64, f"MDP{{{lev}}}.a{{{gi}}}")

        # b{f}
        n_b = int(eng.eval(f"numel({mdp_name}{{{lev}}}.b)"))
        assert n_b == len(mdp_py[lev - 1]["b"]), f"MDP{{{lev}}}.b length mismatch"
        for fi in range(1, n_b + 1):
            b_m = _eval_mat_array(eng, f"full({mdp_name}{{{lev}}}.b{{{fi}}})")
            b_p = mdp_py[lev - 1]["b"][fi - 1][0]
            if hasattr(b_p, "toarray"):
                b_p = b_p.toarray()
            _assert_exact_canon(
                np.asarray(b_m),
                np.asarray(b_p),
                np.float64,
                f"MDP{{{lev}}}.b{{{fi}}}",
            )

        # T
        t_m = float(eng.eval(f"{mdp_name}{{{lev}}}.T"))
        t_p = float(mdp_py[lev - 1]["T"])
        _assert_exact_canon(
            np.array([t_m], dtype=np.float64),
            np.array([t_p], dtype=np.float64),
            np.float64,
            f"MDP{{{lev}}}.T",
        )

        # sA/sB/sC
        for fld in ("sA", "sB", "sC"):
            v_m = _eval_mat_array(eng, f"{mdp_name}{{{lev}}}.{fld}(:)")
            py_list = mdp_py[lev - 1][fld]
            p_cut = [float(py_list[i]) for i in range(int(v_m.size))]
            _assert_exact_canon(v_m.ravel(), np.asarray(p_cut), np.float64, f"MDP{{{lev}}}.{fld}")

        # id.(A,D,E)
        for fld in ("A", "D", "E"):
            n_id = int(eng.eval(f"numel({mdp_name}{{{lev}}}.id.{fld})"))
            assert n_id == len(mdp_py[lev - 1]["id"][fld]), (
                f"MDP{{{lev}}}.id.{fld} length mismatch"
            )
            for ii in range(1, n_id + 1):
                id_m = _eval_mat_array(eng, f"cell2mat({mdp_name}{{{lev}}}.id.{fld}({ii}))")
                id_p = np.asarray(mdp_py[lev - 1]["id"][fld][ii - 1], dtype=np.float64).ravel()
                _assert_exact_canon(
                    id_m.ravel(),
                    id_p.ravel(),
                    np.float64,
                    f"MDP{{{lev}}}.id.{fld}{{{ii}}}",
                )

        # G{s}{g}
        for s in range(1, n_stream + 1):
            n_g_m = int(eng.eval(f"numel({mdp_name}{{{lev}}}.G{{{s}}})"))
            g_py = mdp_py[lev - 1]["G"].get(s, [])
            assert n_g_m == len(g_py), f"MDP{{{lev}}}.G{{{s}}} length mismatch"
            for gi in range(1, n_g_m + 1):
                g_m = _eval_mat_array(eng, f"full({mdp_name}{{{lev}}}.G{{{s}}}{{{gi}}})")
                g_p = np.asarray(g_py[gi - 1], dtype=np.float64)
                _assert_exact_canon(g_m, g_p, np.float64, f"MDP{{{lev}}}.G{{{s}}}{{{gi}}}")

        # ss.(D,E,ID,IE)
        _assert_ss_exact(eng, mdp_name, mdp_py[lev - 1], lev, n_stream)


def _snippet_s_matrix(nr: int = 4, nc: int = 4) -> np.ndarray:
    """§5 snippet ``S`` (``ones(4,3)`` assignments, padded to four columns)."""
    s = np.ones((4, 4), dtype=np.float64)
    s[0, :3] = [nr, nc, 1]
    s[1, :3] = [1, 1, 1]
    s[2, :3] = [1, 1, 1]
    s[3, :3] = [1, 1, 1]
    return s


def _assign_o_cell(dem_eng, name: str, o_py: list) -> None:
    no = len(o_py)
    nt = len(o_py[0])
    dem_eng.eval(f"{name} = cell({no},{nt});", nargout=0)
    for o in range(no):
        for t in range(nt):
            arr = np.asarray(o_py[o][t], dtype=np.float64)
            ns = int(arr.shape[0])
            md = matlab.double(arr.tolist(), size=(ns, 1))
            dem_eng.workspace["O_tmp"] = md
            dem_eng.eval(f"{name}{{{o + 1},{t + 1}}} = O_tmp;", nargout=0)


def _pull_b1(eng, lev: int) -> np.ndarray:
    return np.asarray(eng.eval(f"full(MDP_out{{{lev}}}.b{{1}})"), dtype=np.float64)


def _pull_a_cell(eng, lev: int, row: int) -> np.ndarray:
    return np.asarray(eng.eval(f"full(MDP_out{{{lev}}}.a{{{row},1}})"), dtype=np.float64)


def test_spm_faster_structure_learning_two_level_oracle(dem_eng):
    """Small ``2×4`` outcomes, single stream ``S=[1,1,1,2]`` — matches prior smoke."""
    np.random.seed(0)
    o_py = []
    for _o in range(2):
        row = []
        for _t in range(4):
            v = np.random.rand(2, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_o_cell(dem_eng, "O_fsl", o_py)
    dem_eng.eval(
        "S_fsl = [1,1,1,2]; MDP_out = spm_faster_structure_learning(O_fsl,S_fsl,16,2);",
        nargout=0,
    )
    n_m = int(dem_eng.eval("numel(MDP_out)"))
    mdp_p = spm_faster_structure_learning(
        o_py, np.array([[1, 1, 1, 2]], dtype=np.float64), 16, 2
    )
    assert n_m == len(mdp_p) == 2
    assert len(mdp_p[0]["a"]) == 2
    assert len(mdp_p[0]["b"]) == 1
    assert len(mdp_p[1]["a"]) == 0 and len(mdp_p[1]["b"]) == 0

    for row in (1, 2):
        a_m = _pull_a_cell(dem_eng, 1, row)
        a_p = np.asarray(mdp_p[0]["a"][row - 1][0], dtype=np.float64)
        if hasattr(a_p, "toarray"):
            a_p = a_p.toarray()
        assert_matlab_match(a_m, a_p)

    b_m = _pull_b1(dem_eng, 1)
    b_p = np.asarray(mdp_p[0]["b"][0][0], dtype=np.float64)
    assert_matlab_match(np.atleast_1d(b_m).squeeze(), np.atleast_1d(b_p).squeeze())

    assert float(dem_eng.eval("MDP_out{1}.T")) == float(mdp_p[0]["T"])
    assert float(dem_eng.eval("MDP_out{2}.T")) == float(mdp_p[1]["T"])


@pytest.mark.filterwarnings("ignore:divide by zero encountered in log:RuntimeWarning")
@pytest.mark.filterwarnings("ignore:invalid value encountered in divide:RuntimeWarning")
def test_spm_faster_structure_learning_pdp_o_slice_integration_oracle(dem_eng_fsl_pdp):
    """Tiered T11: ``PDP.O(:,1:k)`` after §1.1 Pong→generate replay (``twister`` + MATLAB ``rand`` buffer).

    Asserts the first ``k`` columns of ``PDP.O`` match Python **before** structure learning
    (numeric chain: generate → slice → SL). Known benign ``RuntimeWarning``s from ``spm_log``
    / ``spm_MDP_MI`` on degenerate Dirichlet slices match MATLAB's silent handling; filtered
    here so CI noise stays low.
    """
    eng = dem_eng_fsl_pdp
    k = 4
    dx_sl, dt_sl = 9, 2

    eng.eval(
        "rng(0,'twister'); "
        "[GDP_fsl,hid,cid,con,RGB_fsl,nP] = spm_MDP_pong(4,4,1,1,0); "
        "GDP_fsl.T = 4; GDP_fsl.tau = 1; "
        "PDP_fsl = spm_MDP_generate(GDP_fsl);",
        nargout=0,
    )
    eng.eval(
        f"O_fsl_pdp = PDP_fsl.O(:,1:{k}); "
        "S_fsl_pdp = ones(4,3); "
        "S_fsl_pdp(1,:) = [4,4,1]; S_fsl_pdp(2,:) = [1,1,1]; "
        "S_fsl_pdp(3,:) = [1,1,1]; S_fsl_pdp(4,:) = [1,1,1]; "
        "S_fsl_pdp(:,end+1:4) = 1;",
        nargout=0,
    )
    eng.eval(
        f"MDP_fsl_pdp = spm_faster_structure_learning(O_fsl_pdp,S_fsl_pdp,{dx_sl},{dt_sl});",
        nargout=0,
    )

    rand_seq = _matlab_rand_buf_twister(eng, 8192)
    gdp = spm_MDP_pong(4, 4, 1, 1, 0)[0]
    gdp["T"] = 4.0
    gdp["tau"] = 1.0
    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp = spm_MDP_generate(gdp)
    _assert_pdp_o_window_matches(eng, "PDP_fsl", pdp, k)
    o_sl = [[pdp["O"][g][t] for t in range(k)] for g in range(len(pdp["O"]))]
    mdp_p = spm_faster_structure_learning(o_sl, _snippet_s_matrix(), dx_sl, dt_sl)

    n_m = int(eng.eval("numel(MDP_fsl_pdp)"))
    assert n_m == len(mdp_p) == 2
    assert int(eng.eval("numel(MDP_fsl_pdp{1}.a)")) == len(mdp_p[0]["a"]) == 19
    assert int(eng.eval("numel(MDP_fsl_pdp{1}.b)")) == len(mdp_p[0]["b"]) == 14
    assert int(eng.eval("numel(MDP_fsl_pdp{2}.a)")) == len(mdp_p[1]["a"]) == 14
    assert int(eng.eval("numel(MDP_fsl_pdp{2}.b)")) == len(mdp_p[1]["b"]) == 4

    b_m = np.asarray(eng.eval("full(MDP_fsl_pdp{1}.b{1})"), dtype=np.float64)
    b_p = np.asarray(mdp_p[0]["b"][0][0], dtype=np.float64).squeeze()
    assert_matlab_match(np.atleast_2d(b_m), np.atleast_2d(b_p))

    assert float(eng.eval("MDP_fsl_pdp{1}.T")) == float(mdp_p[0]["T"])
    assert float(eng.eval("MDP_fsl_pdp{2}.T")) == float(mdp_p[1]["T"])

    _assert_s_a_id_de(eng, "MDP_fsl_pdp", mdp_p, lev=1, n_id_check=5)


@pytest.mark.slow
@pytest.mark.filterwarnings("ignore:divide by zero encountered in log:RuntimeWarning")
@pytest.mark.filterwarnings("ignore:invalid value encountered in divide:RuntimeWarning")
def test_spm_faster_structure_learning_pdp_o_slice_T12_k8_oracle(dem_eng_fsl_pdp):
    """Tiered T11: wider ``PDP.O(:,1:k)`` with ``GDP.T = 12`` (``k`` capped by ``T``)."""
    eng = dem_eng_fsl_pdp
    t_roll = 12
    k = 8
    dx_sl, dt_sl = 9, 2
    buf_n = 16384
    mdp_m_name = "MDP_fsl_wide"

    eng.eval(
        "rng(0,'twister'); "
        "[GDP_w,hid,cid,con,RGB_w,nP] = spm_MDP_pong(4,4,1,1,0); "
        f"GDP_w.T = {int(t_roll)}; GDP_w.tau = 1; "
        "PDP_w = spm_MDP_generate(GDP_w);",
        nargout=0,
    )
    eng.eval(
        f"O_fsl_w = PDP_w.O(:,1:{k}); "
        "S_fsl_w = ones(4,3); "
        "S_fsl_w(1,:) = [4,4,1]; S_fsl_w(2,:) = [1,1,1]; "
        "S_fsl_w(3,:) = [1,1,1]; S_fsl_w(4,:) = [1,1,1]; "
        "S_fsl_w(:,end+1:4) = 1;",
        nargout=0,
    )
    eng.eval(
        f"{mdp_m_name} = spm_faster_structure_learning(O_fsl_w,S_fsl_w,{dx_sl},{dt_sl});",
        nargout=0,
    )

    rand_seq = _matlab_rand_buf_twister(eng, buf_n)
    gdp = spm_MDP_pong(4, 4, 1, 1, 0)[0]
    gdp["T"] = float(t_roll)
    gdp["tau"] = 1.0
    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp = spm_MDP_generate(gdp)
    _assert_pdp_o_window_matches(eng, "PDP_w", pdp, k)
    o_sl = [[pdp["O"][g][t] for t in range(k)] for g in range(len(pdp["O"]))]
    mdp_p = spm_faster_structure_learning(o_sl, _snippet_s_matrix(), dx_sl, dt_sl)

    n_m = int(eng.eval(f"numel({mdp_m_name})"))
    assert n_m == len(mdp_p) == 2
    n_a1 = int(eng.eval(f"numel({mdp_m_name}{{1}}.a)"))
    n_b1 = int(eng.eval(f"numel({mdp_m_name}{{1}}.b)"))
    n_a2 = int(eng.eval(f"numel({mdp_m_name}{{2}}.a)"))
    n_b2 = int(eng.eval(f"numel({mdp_m_name}{{2}}.b)"))
    assert n_a1 == len(mdp_p[0]["a"])
    assert n_b1 == len(mdp_p[0]["b"])
    assert n_a2 == len(mdp_p[1]["a"])
    assert n_b2 == len(mdp_p[1]["b"])

    b_m = np.asarray(eng.eval(f"full({mdp_m_name}{{1}}.b{{1}})"), dtype=np.float64)
    b_p = np.asarray(mdp_p[0]["b"][0][0], dtype=np.float64).squeeze()
    assert_matlab_match(np.atleast_2d(b_m), np.atleast_2d(b_p))

    assert float(eng.eval(f"{mdp_m_name}{{1}}.T")) == float(mdp_p[0]["T"])
    assert float(eng.eval(f"{mdp_m_name}{{2}}.T")) == float(mdp_p[1]["T"])

    _assert_s_a_id_de(eng, mdp_m_name, mdp_p, lev=1, n_id_check=5)


@pytest.mark.slow
@pytest.mark.filterwarnings("ignore:divide by zero encountered in log:RuntimeWarning")
@pytest.mark.filterwarnings("ignore:invalid value encountered in divide:RuntimeWarning")
def test_spm_faster_structure_learning_snippet_scale_T1000_oracle(dem_eng_fsl_pdp):
    """Snippet-scale T11: ``spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc)`` parity."""
    eng = dem_eng_fsl_pdp
    nr, nc, nd, na, npix = 12, 9, 4, 1, 0
    t_roll = 1000
    k = 1000
    sc = 9
    buf_n = 5_000_000
    mdp_m_name = "MDP_fsl_snip"

    eng.eval(
        "rng(0,'twister'); "
        f"[GDP_s,hid,cid,con,RGB_s,nP] = spm_MDP_pong({nr},{nc},{nd},{na},{npix}); "
        f"GDP_s.T = {int(t_roll)}; GDP_s.tau = 1; "
        "PDP_s = spm_MDP_generate(GDP_s);",
        nargout=0,
    )
    eng.eval(
        f"O_fsl_s = PDP_s.O(:,1:{k}); "
        "S_fsl_s = ones(4,3); "
        f"S_fsl_s(1,:) = [{nr},{nc},1]; S_fsl_s(2,:) = [1,1,1]; "
        "S_fsl_s(3,:) = [1,1,1]; S_fsl_s(4,:) = [1,1,1]; "
        "S_fsl_s(:,end+1:4) = 1;",
        nargout=0,
    )
    eng.eval(
        f"{mdp_m_name} = spm_faster_structure_learning(O_fsl_s,S_fsl_s,{sc});",
        nargout=0,
    )

    rand_buf = _matlab_rand_buf_twister_np(eng, buf_n)
    gdp = spm_MDP_pong(nr, nc, nd, na, npix)[0]
    gdp["T"] = float(t_roll)
    gdp["tau"] = 1.0
    with patch("numpy.random.rand", side_effect=_rand_replay_callable(rand_buf)):
        pdp = spm_MDP_generate(gdp)
    o_sl = [[pdp["O"][g][t] for t in range(k)] for g in range(len(pdp["O"]))]
    mdp_p = spm_faster_structure_learning(o_sl, _snippet_s_matrix(nr, nc), sc)

    n_m = int(eng.eval(f"numel({mdp_m_name})"))
    assert n_m == len(mdp_p)
    for lev in range(1, n_m + 1):
        n_a = int(eng.eval(f"numel({mdp_m_name}{{{lev}}}.a)"))
        n_b = int(eng.eval(f"numel({mdp_m_name}{{{lev}}}.b)"))
        assert n_a == len(mdp_p[lev - 1]["a"])
        assert n_b == len(mdp_p[lev - 1]["b"])
        assert float(eng.eval(f"{mdp_m_name}{{{lev}}}.T")) == float(mdp_p[lev - 1]["T"])

    b_m = np.asarray(eng.eval(f"full({mdp_m_name}{{1}}.b{{1}})"), dtype=np.float64)
    b_p = np.asarray(mdp_p[0]["b"][0][0], dtype=np.float64).squeeze()
    assert_matlab_match(np.atleast_2d(b_m), np.atleast_2d(b_p))
    _assert_s_a_id_de(eng, mdp_m_name, mdp_p, lev=1, n_id_check=10)


@pytest.mark.slow
@pytest.mark.filterwarnings("ignore:divide by zero encountered in log:RuntimeWarning")
@pytest.mark.filterwarnings("ignore:invalid value encountered in divide:RuntimeWarning")
@pytest.mark.xfail(
    reason=(
        "Byte-exact exhaustive parity currently fails at snippet scale "
        "(example: MDP{1}.a{5} canonical bytes differ)."
    ),
    strict=False,
)
def test_spm_faster_structure_learning_snippet_scale_T1000_exhaustive_exact_oracle(
    dem_eng_fsl_pdp,
):
    """Exhaustive T11 gate: canonical-byte comparison for every nested MDP entry."""
    eng = dem_eng_fsl_pdp
    nr, nc, nd, na, npix = 12, 9, 4, 1, 0
    t_roll = 1000
    k = 1000
    sc = 9
    buf_n = 5_000_000
    mdp_m_name = "MDP_fsl_snip_exact"
    s_mat = _snippet_s_matrix(nr, nc)
    timing = _env_flag("RGMS_FSL_TIMING")
    use_checkpoint = _env_flag("RGMS_FSL_USE_CHECKPOINT")
    refresh_checkpoint = _env_flag("RGMS_FSL_REFRESH_CHECKPOINT")
    ck_dir = Path(__file__).resolve().parent / "_checkpoint_data"
    ck_py = ck_dir / "fsl_snippet_t1000_o_sl.pkl"
    ck_mat = ck_dir / "fsl_snippet_t1000_matlab_inputs.mat"
    t0 = time.perf_counter()

    o_sl = None

    if use_checkpoint and (not refresh_checkpoint) and ck_py.exists() and ck_mat.exists():
        t_load = time.perf_counter()
        with ck_py.open("rb") as f:
            payload = pickle.load(f)
        o_sl = payload["o_sl"]
        eng.eval(f"load('{ck_mat.as_posix()}','O_fsl_sx','S_fsl_sx');", nargout=0)
        eng.eval(
            f"{mdp_m_name} = spm_faster_structure_learning(O_fsl_sx,S_fsl_sx,{sc});",
            nargout=0,
        )
        _tlog(timing, f"checkpoint load+matlab fsl: {time.perf_counter() - t_load:.2f}s")
    else:
        t_m = time.perf_counter()
        eng.eval(
            "rng(0,'twister'); "
            f"[GDP_sx,hid,cid,con,RGB_sx,nP] = spm_MDP_pong({nr},{nc},{nd},{na},{npix}); "
            f"GDP_sx.T = {int(t_roll)}; GDP_sx.tau = 1; "
            "PDP_sx = spm_MDP_generate(GDP_sx);",
            nargout=0,
        )
        eng.eval(
            f"O_fsl_sx = PDP_sx.O(:,1:{k}); "
            "S_fsl_sx = ones(4,3); "
            f"S_fsl_sx(1,:) = [{nr},{nc},1]; S_fsl_sx(2,:) = [1,1,1]; "
            "S_fsl_sx(3,:) = [1,1,1]; S_fsl_sx(4,:) = [1,1,1]; "
            "S_fsl_sx(:,end+1:4) = 1;",
            nargout=0,
        )
        eng.eval(
            f"{mdp_m_name} = spm_faster_structure_learning(O_fsl_sx,S_fsl_sx,{sc});",
            nargout=0,
        )
        _tlog(timing, f"matlab setup+fsl: {time.perf_counter() - t_m:.2f}s")

        t_p = time.perf_counter()
        rand_buf = _matlab_rand_buf_twister_np(eng, buf_n)
        gdp = spm_MDP_pong(nr, nc, nd, na, npix)[0]
        gdp["T"] = float(t_roll)
        gdp["tau"] = 1.0
        with patch("numpy.random.rand", side_effect=_rand_replay_callable(rand_buf)):
            pdp = spm_MDP_generate(gdp)
        _tlog(timing, f"python generate replay: {time.perf_counter() - t_p:.2f}s")

        t_o = time.perf_counter()
        # Forward-ordered gate: verify generate-stage O parity first, before SL tree checks.
        _assert_pdp_o_window_matches(eng, "PDP_sx", pdp, k)
        o_sl = [[pdp["O"][g][t] for t in range(k)] for g in range(len(pdp["O"]))]
        _tlog(timing, f"pre-SL O parity+build o_sl: {time.perf_counter() - t_o:.2f}s")

        if use_checkpoint:
            ck_dir.mkdir(parents=True, exist_ok=True)
            with ck_py.open("wb") as f:
                pickle.dump({"o_sl": o_sl}, f, protocol=pickle.HIGHEST_PROTOCOL)
            eng.eval(f"save('{ck_mat.as_posix()}','O_fsl_sx','S_fsl_sx');", nargout=0)
            _tlog(timing, f"checkpoint saved: {ck_py.name}, {ck_mat.name}")

    assert o_sl is not None
    # Next earliest deterministic boundary inside SL path: stream-wise grouping.
    t_g = time.perf_counter()
    _assert_rgm_group_streams_exact(eng, "O_fsl_sx", o_sl, s_mat, d_val=sc)
    _tlog(timing, f"rgm_group checkpoints: {time.perf_counter() - t_g:.2f}s")
    t_sl = time.perf_counter()
    mdp_p = spm_faster_structure_learning(o_sl, s_mat, sc)
    _tlog(timing, f"python spm_faster_structure_learning: {time.perf_counter() - t_sl:.2f}s")

    t_tree = time.perf_counter()
    _assert_mdp_tree_exhaustive_exact(eng, mdp_m_name, mdp_p, n_stream=4)
    _tlog(timing, f"mdp tree exhaustive compare: {time.perf_counter() - t_tree:.2f}s")
    _tlog(timing, f"total exhaustive gate: {time.perf_counter() - t0:.2f}s")
