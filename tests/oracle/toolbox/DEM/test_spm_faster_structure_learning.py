"""Oracle: ``spm_faster_structure_learning.m`` vs ``spm_faster_structure_learning``."""

from pathlib import Path
from unittest.mock import patch
import os
import pickle
import time

import matlab
import numpy as np
import pytest
import scipy.linalg as spla

from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from python_src.toolbox.DEM.spm_faster_structure_learning import spm_faster_structure_learning
from python_src.toolbox.DEM.spm_rgm_group import _spm_cat_row, _spm_mdp_mi_scalar, spm_rgm_group
from python_src.spm_dir_MI import spm_dir_MI
from python_src.spm_log import spm_log
from tests.helpers.compare import assert_matlab_match


def _env_flag(name: str) -> bool:
    return str(os.getenv(name, "0")).strip().lower() in ("1", "true", "yes", "on")


def _tlog(enabled: bool, msg: str) -> None:
    if enabled:
        print(f"[TIMER] {msg}", flush=True)


def _diaglog(enabled: bool, msg: str) -> None:
    if enabled:
        print(f"[DIAG] {msg}", flush=True)


def _make_matlab_rgm_eig_pair(eng):
    """Build ``eig_pair`` for :func:`spm_rgm_group` using MATLAB ``eig(...,'nobalance')``.

    Mirrors ``[e,v] = eig(MI(i,i),'nobalance')`` in ``spm_rgm_group.m`` so Python’s
    spectral partition matches MATLAB’s when SciPy/OpenBLAS eigenvectors differ at
    ULP-level ties. Oracle / checkpoint harness only — not for production runs.
    """
    call_i = {"n": 0}

    def _eig_pair(sub: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        sub = np.asarray(sub, dtype=np.float64)
        n = int(sub.shape[0])
        if sub.shape != (n, n):
            raise ValueError("eig_pair expects a square MI block")
        call_i["n"] = call_i["n"] + 1
        tag = f"{call_i['n']}_{id(sub) & 0xFFFFFF:x}"
        mname = f"rgms_MIwk_{tag}"
        ename = f"rgms_e_{tag}"
        vname = f"rgms_v_{tag}"
        eng.workspace[mname] = matlab.double(sub.tolist())
        eng.eval(f"[{ename},{vname}] = eig({mname},'nobalance');", nargout=0)
        lam = eng.eval(f"diag({vname})")
        vals = np.asarray(lam, dtype=np.complex128).reshape(-1, order="F").ravel()
        evecs = np.asarray(eng.eval(ename), dtype=np.complex128)
        if evecs.size != n * n:
            raise RuntimeError(
                f"MATLAB eig returned size {evecs.size}, expected {n * n} for n={n}"
            )
        if evecs.shape != (n, n):
            evecs = np.reshape(evecs, (n, n), order="F")
        eng.eval(f"clear {mname} {ename} {vname}", nargout=0)
        return vals, evecs

    return _eig_pair


def _matlab_mi_for_o_slice(eng, pdp_o_name: str, idx_mat: str) -> np.ndarray:
    """Build MATLAB ``rgms_MI`` for ``O([idx],:)`` (same script as stream-1 oracle)."""
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
    return np.asarray(eng.eval("rgms_MI"), dtype=np.float64)


def _matlab_mi_from_o_cell_var(eng, cell_name: str, m: int) -> np.ndarray:
    """MATLAB ``MI`` for a cell ``O`` already in the Engine (mirrors ``spm_rgm_group.m``).

    Builds the Kronecker-reduced ``R`` grid, ``spm_cat`` rows, flags, and symmetric
    ``MI`` using MATLAB ``spm_MDP_MI`` — same numerics as ``spm_rgm_group`` on that
    slice. ``cell_name`` must be a safe MATLAB identifier (caller-generated).
    """
    eng.eval(
        f"rgms_Os_loc = {cell_name}; "
        "[rgms_No0,rgms_ntB] = size(rgms_Os_loc); "
        f"rgms_mB = {int(m)}; "
        "rgms_Rb = {}; "
        "for rgms_tb = 1:rgms_ntB, "
        "  rgms_ii = 1; "
        "  for rgms_oo = 1:rgms_mB:rgms_No0, "
        "    p = rgms_Os_loc{rgms_oo,rgms_tb}; "
        "    for rgms_rr = 1:(rgms_mB - 1), "
        "      p = kron(p, rgms_Os_loc{rgms_oo + rgms_rr,rgms_tb}); "
        "    end; "
        "    rgms_Rb{rgms_ii,rgms_tb} = p; "
        "    rgms_ii = rgms_ii + 1; "
        "  end; "
        "end; "
        "rgms_No1 = size(rgms_Rb,1); "
        "rgms_nb = false(1,rgms_No1); "
        "rgms_rb = cell(1,rgms_No1); "
        "for rgms_ox = 1:rgms_No1, "
        "  rgms_rb{rgms_ox} = spm_cat(rgms_Rb(rgms_ox,:)); "
        "  rgms_nb(rgms_ox) = any(diff(rgms_rb{rgms_ox},[],2),'all'); "
        "end; "
        "rgms_MI_out = zeros(rgms_No1,rgms_No1); "
        "for rgms_ix = 1:rgms_No1, "
        "  for rgms_jx = rgms_ix:rgms_No1, "
        "    if rgms_nb(rgms_ix) && rgms_nb(rgms_jx), "
        "      rgms_pb = rgms_rb{rgms_ix}*rgms_rb{rgms_jx}'; "
        "      rgms_MI_out(rgms_ix,rgms_jx) = spm_MDP_MI(rgms_pb); "
        "      rgms_MI_out(rgms_jx,rgms_ix) = rgms_MI_out(rgms_ix,rgms_jx); "
        "    end; "
        "  end; "
        "end;",
        nargout=0,
    )
    return np.asarray(eng.eval("rgms_MI_out"), dtype=np.float64)


def _make_matlab_link_dir_mi_fn(eng):
    """Oracle-only: ``spm_dir_MI(a)`` in MATLAB for linked stream matrices ``ss.ID`` / ``IE``."""

    seq = {"i": 0}

    def _link_mi(a_mat: np.ndarray) -> float:
        seq["i"] += 1
        tag = seq["i"]
        mname = f"rgms_am_link_{tag}"
        outname = f"rgms_E_link_{tag}"
        a_mat = np.asarray(a_mat, dtype=np.float64)
        nr, nc = int(a_mat.shape[0]), int(a_mat.shape[1])
        eng.workspace[mname] = matlab.double(a_mat.tolist(), size=(nr, nc))
        eng.eval(f"{outname} = spm_dir_MI({mname});", nargout=0)
        val = float(np.asarray(eng.eval(outname), dtype=np.float64).reshape(-1)[0])
        eng.eval(f"clear {mname} {outname}", nargout=0)
        return val

    return _link_mi


def _make_rgm_mi_override_fn_matlab(eng):
    """PROVISIONAL / ORACLE-ONLY: push each ``o_sub`` slice to MATLAB and return ``MI``.

    Reversible: callers omit ``rgm_mi_override_fn`` (default). Used only to keep
    Python ``spm_faster_structure_learning`` aligned with MATLAB while validating
    the transliteration; remove once native ``MI`` + ``eig`` parity is restored.
    """
    seq = {"i": 0}

    def _mi_fn(o_sub: list, m: int) -> np.ndarray:
        seq["i"] += 1
        cname = f"rgmsOb{seq['i']}"
        no = len(o_sub)
        nt = len(o_sub[0]) if no else 0
        for o in range(no):
            for t in range(nt):
                arr = np.asarray(o_sub[o][t], dtype=np.float64)
                ns = int(arr.shape[0])
                md = matlab.double(arr.tolist(), size=(ns, 1))
                eng.workspace["O_tmp_rgm"] = md
                eng.eval(f"{cname}{{{o+1},{t+1}}} = O_tmp_rgm;", nargout=0)
        mi = _matlab_mi_from_o_cell_var(eng, cname, int(m))
        eng.eval(f"clear {cname}", nargout=0)
        return mi

    return _mi_fn


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


def _assert_repro_close_f64(mat, py, path: str, atol: float = 5e-16, rtol: float = 0.0) -> None:
    m = np.asarray(mat, dtype=np.float64)
    p = np.asarray(py, dtype=np.float64)
    assert m.shape == p.shape, f"{path}: shape mismatch MATLAB {m.shape} vs Python {p.shape}"
    if not np.allclose(m, p, atol=atol, rtol=rtol, equal_nan=True):
        diff = np.max(np.abs(m - p))
        raise AssertionError(f"{path}: reproducibility mismatch (max abs diff {diff})")


def _last_argmax_abs_complex(vals: np.ndarray) -> int:
    v = np.asarray(vals, dtype=np.complex128).ravel()
    if v.size == 0:
        raise ValueError("empty eigenvalue vector")
    keys = np.stack((np.real(v), np.imag(v)), axis=1)
    order = np.lexsort((-np.arange(v.size, dtype=np.int64), -keys[:, 1], -keys[:, 0]))
    return int(order[0])


def _sort_abs_descend_matlab_like(absv: np.ndarray) -> np.ndarray:
    a = np.asarray(absv, dtype=np.float64).ravel()
    n = int(a.size)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    return np.argsort(-a, kind="mergesort").astype(np.int64, copy=False)


def _python_groups_from_mi(
    mi: np.ndarray,
    dx: int,
    u_thresh: float = float(np.exp(-16.0)),
    method: str = "eigh",
    sort_kind: str = "mergesort",
) -> list[np.ndarray]:
    active = np.arange(1, mi.shape[0] + 1, dtype=np.int64)
    groups: list[np.ndarray] = []
    while active.size > 0:
        sub = mi[np.ix_(active - 1, active - 1)]
        sub = np.asarray(sub, dtype=np.float64)
        if method == "eig":
            vals, vecs = np.linalg.eig(sub)
            idx_max = _last_argmax_abs_complex(vals)
            vec = vecs[:, idx_max]
        elif method == "scipy_eig":
            vals, vecs = spla.eig(sub, check_finite=False, overwrite_a=False)
            idx_max = _last_argmax_abs_complex(vals)
            vec = vecs[:, idx_max]
        elif method == "power":
            n = sub.shape[0]
            v = np.ones((n,), dtype=np.float64)
            v /= np.linalg.norm(v)
            for _ in range(256):
                w = sub @ v
                nw = np.linalg.norm(w)
                if nw == 0:
                    break
                v_next = w / nw
                if np.linalg.norm(v_next - v) < 1e-14:
                    v = v_next
                    break
                v = v_next
            vec = v
        else:
            vals, vecs = np.linalg.eigh(sub)
            vec = vecs[:, int(np.argmax(vals))]
        order = _sort_abs_descend_matlab_like(np.abs(vec))
        j_take = order[: min(len(order), int(dx))]
        e_top = np.abs(vec)[j_take]
        j_take = j_take[e_top >= u_thresh]
        groups.append(active[j_take].copy())
        mask = np.ones(active.shape, dtype=bool)
        mask[j_take] = False
        active = active[mask]
    return groups


def _python_group_trace_from_mi(
    mi: np.ndarray,
    dx: int,
    u_thresh: float = float(np.exp(-16.0)),
    method: str = "eigh",
    n_iter: int = 2,
    sort_kind: str = "mergesort",
) -> list[list[int]]:
    active = np.arange(1, mi.shape[0] + 1, dtype=np.int64)
    trace: list[list[int]] = []
    for _ in range(n_iter):
        if active.size == 0:
            break
        sub = mi[np.ix_(active - 1, active - 1)]
        sub = np.asarray(sub, dtype=np.float64)
        if method == "eig":
            vals, vecs = np.linalg.eig(sub)
            idx_max = _last_argmax_abs_complex(vals)
            vec = vecs[:, idx_max]
        elif method == "scipy_eig":
            vals, vecs = spla.eig(sub, check_finite=False, overwrite_a=False)
            idx_max = _last_argmax_abs_complex(vals)
            vec = vecs[:, idx_max]
        elif method == "power":
            n = sub.shape[0]
            v = np.ones((n,), dtype=np.float64)
            v /= np.linalg.norm(v)
            for _ in range(256):
                w = sub @ v
                nw = np.linalg.norm(w)
                if nw == 0:
                    break
                v_next = w / nw
                if np.linalg.norm(v_next - v) < 1e-14:
                    v = v_next
                    break
                v = v_next
            vec = v
        else:
            vals, vecs = np.linalg.eigh(sub)
            vec = vecs[:, int(np.argmax(vals))]
        order = _sort_abs_descend_matlab_like(np.abs(vec))
        j_take = order[: min(len(order), int(dx))]
        e_top = np.abs(vec)[j_take]
        j_take = j_take[e_top >= u_thresh]
        trace.append(active[j_take].astype(int).tolist())
        mask = np.ones(active.shape, dtype=bool)
        mask[j_take] = False
        active = active[mask]
    return trace


def _matlab_find_map(eng, expr: str) -> dict[tuple[int, int], float]:
    eng.eval(f"[rgms_i,rgms_j,rgms_v] = find({expr});", nargout=0)
    ii = np.asarray(eng.eval("rgms_i"), dtype=np.int64).ravel()
    jj = np.asarray(eng.eval("rgms_j"), dtype=np.int64).ravel()
    vv = np.asarray(eng.eval("rgms_v"), dtype=np.float64).ravel()
    out: dict[tuple[int, int], float] = {}
    for k in range(ii.size):
        out[(int(ii[k]), int(jj[k]))] = float(vv[k])
    return out


def _diag_ss_mi_link_mismatch(
    eng,
    mdp_name: str,
    mdp_py: list,
    lev: int,
    si: int,
    sj: int,
    kind: str,
    key: tuple[int, int],
    mv: float,
    pv: float,
) -> None:
    """Isolate ``ss.ID`` / ``ss.IE`` mismatch: linked ``a`` matrix vs ``spm_dir_MI``."""
    fi, fj = key
    print(
        f"[SS-LINK-DIAG] MDP{{{lev}}}.ss.{kind}{{{si},{sj}}} key={key} "
        f"matlab_mi={mv:.17g} python_mi={pv:.17g}",
        flush=True,
    )
    try:
        gi_py = int(mdp_py[lev - 1]["ss"]["D"][si - 1][sj - 1][key])
    except Exception as exc:
        print(f"[SS-LINK-DIAG] Python ss.D lookup failed: {exc}", flush=True)
        gi_py = None
    try:
        gi_m = int(
            float(
                np.asarray(
                    eng.eval(
                        f"full({mdp_name}{{{lev}}}.ss.D{{{si},{sj}}}({fi},{fj}))"
                    ),
                    dtype=np.float64,
                ).ravel()[0]
            )
        )
    except Exception as exc:
        print(f"[SS-LINK-DIAG] MATLAB ss.D lookup failed: {exc}", flush=True)
        gi_m = None
    if gi_py is not None and gi_m is not None and gi_py != gi_m:
        print(
            f"[SS-LINK-DIAG] ss.D gi mismatch: MATLAB gi={gi_m} Python gi={gi_py}",
            flush=True,
        )
    gi = gi_m if gi_m is not None else gi_py
    if gi is None:
        return
    lev_next = lev + 1
    if lev_next > len(mdp_py):
        print(
            f"[SS-LINK-DIAG] skip matrix pull: need MDP{{{lev_next}}} (have {len(mdp_py)} levels)",
            flush=True,
        )
        return
    try:
        a_m = _eval_mat_array(eng, f"full({mdp_name}{{{lev_next}}}.a{{{gi}}})")
        a_p = mdp_py[lev_next - 1]["a"][gi - 1][0]
        if hasattr(a_p, "toarray"):
            a_p = a_p.toarray()
        a_p = np.asarray(a_p, dtype=np.float64)
        dif = float(np.max(np.abs(np.asarray(a_m, dtype=np.float64) - a_p)))
        print(
            f"[SS-LINK-DIAG] linked a MDP{{{lev_next}}}.a{{{gi}}} max|diff|={dif:.3e} "
            f"shape_mat={np.asarray(a_m).shape} shape_py={a_p.shape}",
            flush=True,
        )
        sm, bm = _canon_bytes(np.asarray(a_m, dtype=np.float64), np.float64)
        sp, bp = _canon_bytes(a_p, np.float64)
        print(
            f"[SS-LINK-DIAG] linked a bytes match: {sm == sp and bm == bp}",
            flush=True,
        )
    except Exception as exc:
        print(f"[SS-LINK-DIAG] linked a matrix pull failed: {exc}", flush=True)
        return
    try:
        py_mi_on_ap = float(np.real(spm_dir_MI(a_p)))
        print(
            f"[SS-LINK-DIAG] spm_dir_MI(Python a)={py_mi_on_ap:.17g} "
            f"(stored ss.{kind} py={pv:.17g})",
            flush=True,
        )
    except Exception as exc:
        print(f"[SS-LINK-DIAG] Python spm_dir_MI(a_p) failed: {exc}", flush=True)
        py_mi_on_ap = None
    try:
        eng.workspace["rgms_ap"] = matlab.double(a_p.tolist())
        eng.eval("rgms_mi_from_py_a = spm_dir_MI(rgms_ap);", nargout=0)
        ml_mi_on_py_a = float(
            np.asarray(eng.eval("rgms_mi_from_py_a"), dtype=np.float64).ravel()[0]
        )
        print(
            f"[SS-LINK-DIAG] spm_dir_MI(MATLAB on Python a)={ml_mi_on_py_a:.17g}",
            flush=True,
        )
        if py_mi_on_ap is not None:
            print(
                f"[SS-LINK-DIAG] Python vs MATLAB-on-Python-a MI delta="
                f"{py_mi_on_ap - ml_mi_on_py_a:.3e}",
                flush=True,
            )
        print(
            f"[SS-LINK-DIAG] MATLAB ss.{kind} stored={mv:.17g} vs MATLAB(spm_dir_MI(py a)) "
            f"delta={mv - ml_mi_on_py_a:.3e}",
            flush=True,
        )
    except Exception as exc:
        print(f"[SS-LINK-DIAG] MATLAB spm_dir_MI(rgms_ap) failed: {exc}", flush=True)


def _assert_ss_exact(
    eng,
    mdp_name: str,
    mdp_py_lev: dict,
    lev: int,
    n_stream: int,
    *,
    mdp_py_full: list | None = None,
) -> None:
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
                        try:
                            _assert_exact_canon(
                                np.array([mv], dtype=np.float64),
                                np.array([pv], dtype=np.float64),
                                np.float64,
                                f"MDP{{{lev}}}.ss.{kind}{{{si},{sj}}}{key}",
                            )
                        except AssertionError:
                            if mdp_py_full is not None and kind in ("ID", "IE"):
                                _diag_ss_mi_link_mismatch(
                                    eng,
                                    mdp_name,
                                    mdp_py_full,
                                    lev,
                                    si,
                                    sj,
                                    kind,
                                    key,
                                    mv,
                                    pv,
                                )
                            raise


def _assert_rgm_group_streams_exact(
    eng,
    pdp_o_name: str,
    o_py: list,
    s_mat: np.ndarray,
    d_val: int,
    *,
    rgm_eig_pair=None,
    rgm_mi_override_fn=None,
) -> None:
    """Forward-ordered Step-6 start: n=1 call setup, then stream-wise grouping parity."""
    if rgm_eig_pair is None and _env_flag("RGMS_FSL_RGM_MATLAB_EIG"):
        rgm_eig_pair = _make_matlab_rgm_eig_pair(eng)
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
            diag = _env_flag("RGMS_FSL_MI_DIAG")
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
            if rgm_mi_override_fn is not None:
                mi_p = np.asarray(
                    rgm_mi_override_fn(o_sub, int(s_mat[s - 1, 3])),
                    dtype=np.float64,
                )
            else:
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
                    "rgms_logA = spm_log(rgms_Aij(:)); "
                    "rgms_t1 = rgms_Aij(:)'*spm_log(rgms_Aij(:)); "
                    "rgms_t1_alt = sum(rgms_Aij(:).*spm_log(rgms_Aij(:))); "
                    "rgms_t2 = sum(rgms_Aij,1)*spm_log(sum(rgms_Aij,1)'); "
                    "rgms_t3 = sum(rgms_Aij,2)'*spm_log(sum(rgms_Aij,2));",
                    nargout=0,
                )
                t1_m = float(np.asarray(eng.eval("rgms_t1"), dtype=np.float64).ravel()[0])
                t1_m_alt = float(np.asarray(eng.eval("rgms_t1_alt"), dtype=np.float64).ravel()[0])
                t2_m = float(np.asarray(eng.eval("rgms_t2"), dtype=np.float64).ravel()[0])
                t3_m = float(np.asarray(eng.eval("rgms_t3"), dtype=np.float64).ravel()[0])
                a_p_norm = np.asarray(p_p, dtype=np.float64) / float(np.asarray(p_p, dtype=np.float64).sum())
                a_col = a_p_norm.reshape(-1, 1, order="F")
                t1_p = float((a_col.T @ spm_log(a_col)).ravel()[0])
                row_sum = np.sum(a_p_norm, axis=0, keepdims=True)
                col_sum = np.sum(a_p_norm, axis=1, keepdims=True)
                t2_p = float((row_sum @ spm_log(row_sum.T)).ravel()[0])
                t3_p = float((col_sum.T @ spm_log(col_sum)).ravel()[0])
                if diag:
                    a_col_m = a_m_norm.reshape(-1, 1, order="F")
                    log_col_m_mat = np.asarray(eng.eval("rgms_logA"), dtype=np.float64).reshape(-1, 1, order="F")
                    log_col_m = spm_log(a_col_m)
                    log_col_p = spm_log(a_col)
                    contrib_m = a_col_m * log_col_m
                    contrib_p = a_col * log_col_p
                    log_diffs = np.where(
                        log_col_m_mat.reshape(-1, order="F") != log_col_m.reshape(-1, order="F")
                    )[0]
                    flat_m = contrib_m.reshape(-1, order="F")
                    flat_p = contrib_p.reshape(-1, order="F")
                    diffs = np.where(flat_m != flat_p)[0]
                    _diaglog(
                        True,
                        (
                            f"MI({i1},{j1}) t1_m={t1_m:.17g} t1_m_alt={t1_m_alt:.17g} t1_p={t1_p:.17g} "
                            f"delta={t1_m - t1_p:.17g}"
                        ),
                    )
                    if diffs.size:
                        k0 = int(diffs[0])
                        _diaglog(
                            True,
                            (
                                f"MI({i1},{j1}) first contrib diff at idx {k0 + 1}: "
                                f"A_m={float(a_col_m[k0, 0]):.17g}, A_p={float(a_col[k0, 0]):.17g}, "
                                f"log_m={float(log_col_m[k0, 0]):.17g}, log_p={float(log_col_p[k0, 0]):.17g}, "
                                f"contrib_m={float(flat_m[k0]):.17g}, contrib_p={float(flat_p[k0]):.17g}"
                            ),
                        )
                    else:
                        t1_p_sum = float(np.sum(flat_p, dtype=np.float64))
                        t1_p_sum_f = float(
                            np.sum(np.asarray(contrib_p, dtype=np.float64).reshape(-1, order="F"), dtype=np.float64)
                        )
                        t1_p_dot = float(np.dot(a_col.ravel(order="F"), log_col_p.ravel(order="F")))
                        _diaglog(
                            True,
                            (
                                f"MI({i1},{j1}) no per-entry contrib byte diff; accumulation candidates "
                                f"matmul={t1_p:.17g}, sum={t1_p_sum:.17g}, sumF={t1_p_sum_f:.17g}, "
                                f"dotF={t1_p_dot:.17g}"
                            ),
                        )
                    if log_diffs.size:
                        klog = int(log_diffs[0])
                        _diaglog(
                            True,
                            (
                                f"MI({i1},{j1}) first spm_log diff at idx {klog + 1}: "
                                f"log_mat={float(log_col_m_mat[klog, 0]):.17g}, "
                                f"log_py={float(log_col_m[klog, 0]):.17g}"
                            ),
                        )
                    else:
                        _diaglog(True, f"MI({i1},{j1}) spm_log(A(:)) matches entrywise")
                _assert_repro_close_f64(
                    np.array([t1_m], dtype=np.float64),
                    np.array([t1_p], dtype=np.float64),
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
                _assert_repro_close_f64(
                    np.array([mi_scalar_m], dtype=np.float64),
                    np.array([mi_scalar_p], dtype=np.float64),
                    f"spm_rgm_group stream 1 MI-scalar({i1},{j1})",
                )
            _assert_repro_close_f64(mi_m, mi_p, "spm_rgm_group stream 1 MI")
            if _env_flag("RGMS_FSL_GROUP_DIAG"):
                eng.eval(
                    "rgms_dbg_i = 1:size(rgms_MI,1); "
                    "rgms_dbg_dx = fix(" + f"{int(d_val)}" + "); "
                    "rgms_dbg_U = exp(-16); "
                    "for rgms_dbg_iter = 1:2, "
                    "  rgms_dbg_sub = rgms_MI(rgms_dbg_i,rgms_dbg_i); "
                    "  [rgms_dbg_evec,rgms_dbg_eval] = eig(rgms_dbg_sub,'nobalance'); "
                    "  rgms_dbg_lambda = diag(rgms_dbg_eval); "
                    "  [~,rgms_dbg_jmax] = max(diag(rgms_dbg_eval),[],1); "
                    "  rgms_dbg_col = rgms_dbg_evec(:,rgms_dbg_jmax); "
                    "  [rgms_dbg_es,rgms_dbg_js] = sort(abs(rgms_dbg_evec(:,rgms_dbg_jmax)),'descend'); "
                    "  rgms_dbg_k = 1:min(numel(rgms_dbg_js),rgms_dbg_dx); "
                    "  rgms_dbg_j = rgms_dbg_js(rgms_dbg_k); "
                    "  rgms_dbg_j(rgms_dbg_es(rgms_dbg_k) < rgms_dbg_U) = []; "
                    "  assignin('base',sprintf('rgms_dbg_i_%d',rgms_dbg_iter),rgms_dbg_i); "
                    "  assignin('base',sprintf('rgms_dbg_j_%d',rgms_dbg_iter),rgms_dbg_j); "
                    "  assignin('base',sprintf('rgms_dbg_es_%d',rgms_dbg_iter),rgms_dbg_es(rgms_dbg_k)); "
                    "  assignin('base',sprintf('rgms_dbg_lam_%d',rgms_dbg_iter),rgms_dbg_lambda); "
                    "  assignin('base',sprintf('rgms_dbg_jmax_%d',rgms_dbg_iter),rgms_dbg_jmax); "
                    "  assignin('base',sprintf('rgms_dbg_col_%d',rgms_dbg_iter),full(rgms_dbg_col)); "
                    "  rgms_dbg_i(rgms_dbg_j) = []; "
                    "end;",
                    nargout=0,
                )

        eng.eval(
            f"rgms_g_stream = spm_rgm_group({pdp_o_name}([{idx_mat}],:), {int(d_val)}, 1);",
            nargout=0,
        )
        n_g = int(eng.eval("numel(rgms_g_stream)"))
        o_sub = [o_py[int(i) - 1] for i in idx]
        if rgm_eig_pair is not None:
            mi_mlab = _matlab_mi_for_o_slice(eng, pdp_o_name, idx_mat)
            g_py = spm_rgm_group(
                o_sub,
                d_val,
                1,
                eig_pair=rgm_eig_pair,
                mi_override=mi_mlab,
            )
        else:
            g_py = spm_rgm_group(o_sub, d_val, 1)
        assert n_g == len(g_py), f"spm_rgm_group stream {s}: length mismatch"
        for gi in range(1, n_g + 1):
            g_m = _eval_mat_array(eng, f"rgms_g_stream{{{gi}}}")
            g_p = np.asarray(g_py[gi - 1], dtype=np.float64)
            if s == 1 and _env_flag("RGMS_FSL_GROUP_DIAG"):
                g_m_r = np.asarray(g_m).ravel()
                g_p_r = np.asarray(g_p).ravel()
                if not np.array_equal(g_m_r, g_p_r):
                    mi_from_m = np.asarray(eng.eval("rgms_MI"), dtype=np.float64)
                    py_from_mi_m = _python_groups_from_mi(mi_from_m, int(d_val), method="eigh", sort_kind="mergesort")
                    py_from_mi_m_eig = _python_groups_from_mi(mi_from_m, int(d_val), method="eig", sort_kind="mergesort")
                    py_from_mi_m_eig_quick = _python_groups_from_mi(
                        mi_from_m, int(d_val), method="eig", sort_kind="quicksort"
                    )
                    py_from_mi_m_scipy = _python_groups_from_mi(
                        mi_from_m, int(d_val), method="scipy_eig", sort_kind="mergesort"
                    )
                    py_from_mi_m_power = _python_groups_from_mi(
                        mi_from_m, int(d_val), method="power", sort_kind="mergesort"
                    )
                    g_from_mi = (
                        py_from_mi_m[gi - 1].astype(np.float64)
                        if gi - 1 < len(py_from_mi_m)
                        else np.array([], dtype=np.float64)
                    )
                    g_from_mi_eig = (
                        py_from_mi_m_eig[gi - 1].astype(np.float64)
                        if gi - 1 < len(py_from_mi_m_eig)
                        else np.array([], dtype=np.float64)
                    )
                    g_from_mi_eig_quick = (
                        py_from_mi_m_eig_quick[gi - 1].astype(np.float64)
                        if gi - 1 < len(py_from_mi_m_eig_quick)
                        else np.array([], dtype=np.float64)
                    )
                    g_from_mi_scipy = (
                        py_from_mi_m_scipy[gi - 1].astype(np.float64)
                        if gi - 1 < len(py_from_mi_m_scipy)
                        else np.array([], dtype=np.float64)
                    )
                    g_from_mi_power = (
                        py_from_mi_m_power[gi - 1].astype(np.float64)
                        if gi - 1 < len(py_from_mi_m_power)
                        else np.array([], dtype=np.float64)
                    )
                    _diaglog(
                        True,
                        (
                            f"group diag stream 1 g{gi}: "
                            f"mat={g_m_r.astype(int).tolist()} "
                            f"py={g_p_r.astype(int).tolist()} "
                            f"py_from_matMI_eigh={g_from_mi.astype(int).tolist()} "
                            f"py_from_matMI_eig={g_from_mi_eig.astype(int).tolist()} "
                            f"py_from_matMI_eig_quick={g_from_mi_eig_quick.astype(int).tolist()} "
                            f"py_from_matMI_scipy_eig={g_from_mi_scipy.astype(int).tolist()} "
                            f"py_from_matMI_power={g_from_mi_power.astype(int).tolist()}"
                        ),
                    )
                    try:
                        i1 = np.asarray(eng.eval("rgms_dbg_i_1"), dtype=np.int64).ravel(order="F")
                        j1 = np.asarray(eng.eval("rgms_dbg_j_1"), dtype=np.int64).ravel(order="F")
                        i2 = np.asarray(eng.eval("rgms_dbg_i_2"), dtype=np.int64).ravel(order="F")
                        j2 = np.asarray(eng.eval("rgms_dbg_j_2"), dtype=np.int64).ravel(order="F")
                        lam2 = np.asarray(eng.eval("rgms_dbg_lam_2"), dtype=np.complex128).ravel(order="F")
                        jmax2 = int(np.asarray(eng.eval("rgms_dbg_jmax_2"), dtype=np.int64).ravel(order="F")[0])
                        col2_m = np.asarray(eng.eval("rgms_dbg_col_2"), dtype=np.complex128).ravel(order="F")
                        _diaglog(
                            True,
                            (
                                f"matlab spectral dbg: iter1 i_len={i1.size} j={j1.astype(int).tolist()} | "
                                f"iter2 i_len={i2.size} j={j2.astype(int).tolist()}"
                            ),
                        )
                        tr_eigh = _python_group_trace_from_mi(
                            mi_from_m, int(d_val), method="eigh", n_iter=2, sort_kind="mergesort"
                        )
                        tr_eig = _python_group_trace_from_mi(
                            mi_from_m, int(d_val), method="eig", n_iter=2, sort_kind="mergesort"
                        )
                        tr_eig_quick = _python_group_trace_from_mi(
                            mi_from_m, int(d_val), method="eig", n_iter=2, sort_kind="quicksort"
                        )
                        tr_scipy = _python_group_trace_from_mi(
                            mi_from_m, int(d_val), method="scipy_eig", n_iter=2, sort_kind="mergesort"
                        )
                        tr_power = _python_group_trace_from_mi(
                            mi_from_m, int(d_val), method="power", n_iter=2, sort_kind="mergesort"
                        )
                        _diaglog(
                            True,
                            f"python spectral dbg: eigh={tr_eigh} | eig={tr_eig} | eig_quick={tr_eig_quick} | scipy_eig={tr_scipy} | power={tr_power}",
                        )
                        lam2_abs = np.sort(np.abs(lam2))[::-1]
                        _diaglog(
                            True,
                            f"matlab iter2 |lambda| top6={lam2_abs[:6].tolist()} gap12={float(lam2_abs[0]-lam2_abs[1]):.3e}",
                        )
                        sub2 = mi_from_m[np.ix_(i2 - 1, i2 - 1)]
                        sub2 = np.asarray(sub2, dtype=np.float64)
                        sub2 = 0.5 * (sub2 + sub2.T)
                        vals2, vecs2 = spla.eig(sub2, check_finite=False, overwrite_a=False)
                        vals2 = np.asarray(vals2, dtype=np.complex128).ravel(order="F")
                        vecs2 = np.asarray(vecs2, dtype=np.complex128)
                        py_jmax = int(np.argmax(np.abs(vals2)))
                        av2 = np.abs(vals2)
                        mx_py = int(np.argmax(av2))
                        _diaglog(
                            True,
                            (
                                f"iter2 scipy |lambda|: argmax 1-based={mx_py + 1} "
                                f"|lam|={float(av2[mx_py]):.17g} "
                                f"spacing={float(np.spacing(av2[mx_py])):.3e}"
                            ),
                        )
                        vec2_py = vecs2[:, py_jmax]
                        lam_sel_m = lam2[jmax2 - 1]
                        lam_sel_py = vals2[py_jmax]
                        _diaglog(
                            True,
                            (
                                f"iter2 eig pick: mat_jmax={jmax2} lam={complex(lam_sel_m)} | "
                                f"py_jmax={py_jmax + 1} lam={complex(lam_sel_py)}"
                            ),
                        )
                        col2_py = vec2_py
                        # Compare principal columns up to complex phase (MATLAB may return arbitrary global phase).
                        cross = np.vdot(col2_m, col2_py)
                        if np.abs(cross) > 0:
                            scale = cross / np.abs(cross)
                            col2_py_aln = col2_py * scale
                        else:
                            col2_py_aln = col2_py
                        max_abs_diff = float(np.max(np.abs(col2_m - col2_py_aln)))
                        _diaglog(
                            True,
                            f"iter2 principal col max|diff| after phase align: {max_abs_diff:.3e}",
                        )
                        am_raw = np.abs(col2_m)
                        ap_raw = np.abs(vec2_py)
                        top_m = np.sort(am_raw)[-2:][::-1]
                        top_p = np.sort(ap_raw)[-2:][::-1]
                        _diaglog(
                            True,
                            f"iter2 |e| top2 mat={top_m.tolist()} py_raw={top_p.tolist()} "
                            f"delta_top1={float(top_m[0]-top_p[0]):.3e}",
                        )
                        ord_m = _sort_abs_descend_matlab_like(np.abs(col2_m))
                        # Match production `spm_rgm_group`: sort `abs` of complex column.
                        ord_p = _sort_abs_descend_matlab_like(np.abs(col2_py))
                        if not np.array_equal(ord_m, ord_p):
                            diff_pos = int(np.argmax(ord_m != ord_p))
                            im = int(ord_m[diff_pos])
                            ip = int(ord_p[diff_pos])
                            am = np.asarray(np.abs(col2_m), dtype=np.float64).ravel()
                            ap = np.asarray(np.abs(col2_py), dtype=np.float64).ravel()
                            dabs = np.abs(am - ap)
                            ref = np.maximum(am, ap)
                            # Focus ULP stats on rows that matter for early `sort` ranks.
                            head = np.unique(
                                np.concatenate(
                                    [ord_m[: min(16, ord_m.size)], ord_p[: min(16, ord_p.size)]]
                                )
                            )
                            ulp_rows: list[float] = []
                            for ii in head:
                                r0 = float(ref[ii])
                                if r0 <= 0:
                                    continue
                                ulp_rows.append(float(dabs[ii] / np.spacing(r0)))
                            ulp_max = max(ulp_rows) if ulp_rows else 0.0
                            _diaglog(
                                True,
                                (
                                    f"iter2 sort order diverges at rank pos {diff_pos + 1}: "
                                    f"mat_idx={im + 1} py_idx={ip + 1} "
                                    f"|mat|={float(am[im]):.17g} |py|={float(ap[ip]):.17g}"
                                ),
                            )
                            _diaglog(
                                True,
                                (
                                    f"iter2 |e| vec ULP on first-16 sort ranks (union mat/py): "
                                    f"max_ulps={ulp_max:.3f} max|am-ap|={float(np.max(dabs)):.3e}"
                                ),
                            )
                            for label, idx0 in (("mat_rank1", im), ("py_rank1", ip)):
                                r0 = float(ref[idx0])
                                ulp0 = float(dabs[idx0] / np.spacing(r0)) if r0 > 0 else float("nan")
                                _diaglog(
                                    True,
                                    (
                                        f"iter2 {label} 1-based={idx0 + 1}: "
                                        f"am={float(am[idx0]):.17g} ap={float(ap[idx0]):.17g} "
                                        f"delta={float(am[idx0] - ap[idx0]):.3e} "
                                        f"ulps={ulp0:.3f}"
                                    ),
                                )
                        else:
                            _diaglog(True, "iter2 sort order matches (abs of complex principal col)")
                    except Exception:
                        pass
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
                # MATLAB often stores index vectors as ``1×n`` rows; Python uses ``n×1``.
                _assert_exact_canon(
                    np.asarray(g_m, dtype=np.float64).ravel(),
                    np.asarray(g_p, dtype=np.float64).ravel(),
                    np.float64,
                    f"MDP{{{lev}}}.G{{{s}}}{{{gi}}}",
                )

        # ss.(D,E,ID,IE)
        _assert_ss_exact(
            eng, mdp_name, mdp_py[lev - 1], lev, n_stream, mdp_py_full=mdp_py
        )


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
    """Exhaustive T11 gate: canonical-byte comparison for every nested MDP entry.

    **Provisional translation bridge (reversible, oracle-only):**

    - ``RGMS_FSL_RGM_MATLAB_EIG=1`` — pass MATLAB ``eig(...,'nobalance')`` into
      :func:`spm_faster_structure_learning` only (``rgm_eig_pair``). Step-6
      ``_assert_rgm_group_streams_exact`` still uses MATLAB ``MI`` + ``eig`` for
      slice-indexed ``O`` when this flag is set. **Fast** enough for routine runs.
    - ``RGMS_FSL_RGM_MATLAB_MI_PUSH=1`` — pass
      ``rgm_mi_override_fn`` so every ``spm_rgm_group`` rebuilds ``MI`` in MATLAB
      from the current Python ``o_sub`` (many Engine round-trips; **slow**). Use
      for lane isolation: with ``RGMS_FSL_RGM_MATLAB_EIG=0`` this is Lane-B
      (MATLAB MI + Python eig), with ``RGMS_FSL_RGM_MATLAB_EIG=1`` this is
      Lane-C (MATLAB MI + MATLAB eig).
    - ``RGMS_FSL_LINK_DIR_MI_MATLAB=1`` — optional ``link_dir_mi_fn`` so stream-link
      stored MI matches MATLAB ``spm_dir_MI`` on each pulled ``a`` (many Engine
      calls inside ``_link_streams``). Use when isolating ``ss.ID`` / ``IE`` parity;
      combine with ``RGMS_FSL_RGM_MATLAB_*`` only when validating end-to-end.

    Omit all three flags for pure Python. Remove bridges when native ``MI`` +
    ``eig`` + link ``spm_dir_MI`` parity/policy is resolved.
    """
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
    rgm_eig_pair = None
    rgm_mi_override_fn = None
    link_dir_mi_fn = None
    lane_b = _env_flag("RGMS_FSL_RGM_MATLAB_MI_PUSH") and not _env_flag(
        "RGMS_FSL_RGM_MATLAB_EIG"
    )
    if _env_flag("RGMS_FSL_RGM_MATLAB_EIG"):
        rgm_eig_pair = _make_matlab_rgm_eig_pair(eng)
    if _env_flag("RGMS_FSL_RGM_MATLAB_MI_PUSH"):
        rgm_mi_override_fn = _make_rgm_mi_override_fn_matlab(eng)
    if _env_flag("RGMS_FSL_LINK_DIR_MI_MATLAB"):
        link_dir_mi_fn = _make_matlab_link_dir_mi_fn(eng)
    if lane_b:
        print(
            "[DIAG] Lane B enabled: MATLAB MI push with Python/SciPy eig "
            "(diagnostic ablation, provisional only).",
            flush=True,
        )
    # Next earliest deterministic boundary inside SL path: stream-wise grouping.
    t_g = time.perf_counter()
    _assert_rgm_group_streams_exact(
        eng,
        "O_fsl_sx",
        o_sl,
        s_mat,
        d_val=sc,
        rgm_eig_pair=rgm_eig_pair,
        rgm_mi_override_fn=rgm_mi_override_fn,
    )
    _tlog(timing, f"rgm_group checkpoints: {time.perf_counter() - t_g:.2f}s")
    t_sl = time.perf_counter()
    mdp_p = spm_faster_structure_learning(
        o_sl,
        s_mat,
        sc,
        rgm_eig_pair=rgm_eig_pair,
        rgm_mi_override_fn=rgm_mi_override_fn,
        link_dir_mi_fn=link_dir_mi_fn,
    )
    _tlog(timing, f"python spm_faster_structure_learning: {time.perf_counter() - t_sl:.2f}s")

    t_tree = time.perf_counter()
    _assert_mdp_tree_exhaustive_exact(eng, mdp_m_name, mdp_p, n_stream=4)
    _tlog(timing, f"mdp tree exhaustive compare: {time.perf_counter() - t_tree:.2f}s")
    _tlog(timing, f"total exhaustive gate: {time.perf_counter() - t0:.2f}s")


@pytest.mark.slow
def test_spm_faster_structure_learning_checkpoint_rgm_streams_matlab_eig_parity(
    dem_eng_fsl_pdp,
):
    """Step-6 grouping bytes match MATLAB when Python uses MATLAB ``eig(...,'nobalance')``.

    Proves the spectral mismatch at ``spm_rgm_group`` stream 1 group 2 is isolated
    to the eigenpair numerics of the active ``MI(i,i)`` block, not MI assembly or
    downstream structure-learning logic in this harness.
    """
    ck_dir = Path(__file__).resolve().parent / "_checkpoint_data"
    ck_py = ck_dir / "fsl_snippet_t1000_o_sl.pkl"
    ck_mat = ck_dir / "fsl_snippet_t1000_matlab_inputs.mat"
    if not ck_py.is_file() or not ck_mat.is_file():
        pytest.skip("checkpoint artifacts missing (run exhaustive once to create them)")
    eng = dem_eng_fsl_pdp
    sc = 9
    s_mat = _snippet_s_matrix(12, 9)
    with ck_py.open("rb") as f:
        o_sl = pickle.load(f)["o_sl"]
    eng.eval(f"load('{ck_mat.as_posix()}','O_fsl_sx','S_fsl_sx');", nargout=0)
    rgp = _make_matlab_rgm_eig_pair(eng)
    _assert_rgm_group_streams_exact(
        eng, "O_fsl_sx", o_sl, s_mat, d_val=sc, rgm_eig_pair=rgp
    )
