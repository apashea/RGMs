"""Oracle tests: spm_rgm_group.m vs python_src.toolbox.DEM.spm_rgm_group."""

from pathlib import Path
import pickle
import os

import matlab
import numpy as np
import pytest
import scipy.linalg as spla
from scipy.linalg import lapack

from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like, spm_rgm_group
from tests.helpers.compare import assert_matlab_match


def _spectral_workload_files() -> list[Path]:
    repo = Path(__file__).resolve().parents[4]
    ck_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data"
    tag = str(os.getenv("RGMS_RGM_SPECTRAL_REPLAY_TAG", "")).strip()
    if tag:
        safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in tag)
        cks = sorted(ck_dir.glob(f"fsl_rgm_spectral_workload_{safe}.pkl"))
    else:
        cks = sorted(ck_dir.glob("fsl_rgm_spectral_workload*.pkl"))
    return cks


@pytest.fixture
def dem_eng(eng):
    dem_path = Path(__file__).resolve().parents[4] / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    return eng


def _assign_O_cell(eng, matlab_name: str, o_py: list) -> None:
    """Push ``No × Nt`` cell ``O`` to MATLAB as ``(Ns, 1)`` columns per SPM usage."""
    no = len(o_py)
    nt = len(o_py[0])
    for o in range(no):
        for t in range(nt):
            arr = np.asarray(o_py[o][t], dtype=np.float64)
            ns = int(arr.shape[0])
            md = matlab.double(arr.tolist(), size=(ns, 1))
            eng.workspace["O_tmp_rgm"] = md
            eng.eval(f"{matlab_name}{{{o+1},{t+1}}} = O_tmp_rgm;", nargout=0)


def _pull_G(eng, matlab_name: str) -> list:
    ng = int(eng.eval(f"numel({matlab_name})"))
    return [
        np.asarray(eng.eval(f"{matlab_name}{{{i + 1}}}"), dtype=np.int64).ravel()
        for i in range(ng)
    ]


def test_spm_rgm_group_empty_oracle(dem_eng):
    dem_eng.eval("G_rgm_empty = spm_rgm_group({});", nargout=0)
    assert int(dem_eng.eval("numel(G_rgm_empty)")) == 0
    assert spm_rgm_group([]) == []


def test_spm_rgm_group_no_less_than_dx_single_group_oracle(dem_eng):
    no, nt, ns = 5, 2, 2
    np.random.seed(2)
    o_py = []
    for o in range(no):
        row = []
        for t in range(nt):
            v = np.random.rand(ns, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_O_cell(dem_eng, "O_rgm_small", o_py)
    dem_eng.eval("G_rgm_small = spm_rgm_group(O_rgm_small, 16);", nargout=0)
    g_m = _pull_G(dem_eng, "G_rgm_small")
    g_p = spm_rgm_group(o_py, 16, 1)
    assert len(g_m) == len(g_p) == 1
    assert_matlab_match(g_m[0], g_p[0])


def test_spm_rgm_group_clustering_oracle(dem_eng):
    no, nt, ns = 6, 4, 3
    np.random.seed(0)
    o_py = []
    for o in range(no):
        row = []
        for t in range(nt):
            v = np.random.rand(ns, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_O_cell(dem_eng, "O_rgm_clu", o_py)
    dem_eng.eval("G_rgm_clu = spm_rgm_group(O_rgm_clu, 3);", nargout=0)
    g_m = _pull_G(dem_eng, "G_rgm_clu")
    g_p = spm_rgm_group(o_py, 3, 1)
    assert len(g_m) == len(g_p)
    for a, b in zip(g_m, g_p):
        assert_matlab_match(a, b)


def test_spm_rgm_group_m2_oracle(dem_eng):
    no, nt, ns, m = 4, 3, 2, 2
    np.random.seed(1)
    o_py = []
    for o in range(no):
        row = []
        for t in range(nt):
            v = np.random.rand(ns, 1)
            row.append(v / np.sum(v))
        o_py.append(row)
    _assign_O_cell(dem_eng, "O_rgm_m2", o_py)
    dem_eng.eval("G_rgm_m2 = spm_rgm_group(O_rgm_m2, 8, 2);", nargout=0)
    g_m = _pull_G(dem_eng, "G_rgm_m2")
    g_p = spm_rgm_group(o_py, 8, 2)
    assert len(g_m) == len(g_p)
    for a, b in zip(g_m, g_p):
        assert_matlab_match(a, b)


def _replay_python_spectral_decision(
    sub_mi: np.ndarray,
    active_before: np.ndarray,
    dx: int,
    u_thresh: float,
) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    sub = np.asarray(sub_mi, dtype=np.float64)
    mode = str(os.getenv("RGMS_RGM_EXPERIMENT_SUB_CONDITION", "")).strip().lower()
    if mode not in ("", "none", "off", "0", "false", "no"):
        if mode in ("scale_maxabs", "scale"):
            m = float(np.max(np.abs(sub))) if sub.size else 0.0
            if m != 0.0:
                sub = sub / m
        elif mode in ("psd_clip", "psd"):
            vals_c, vecs_c = np.linalg.eigh(sub)
            vals_c = np.maximum(np.asarray(vals_c, dtype=np.float64), 0.0)
            sub = (vecs_c @ np.diag(vals_c) @ vecs_c.T).astype(np.float64, copy=False)
            sub = 0.5 * (sub + sub.T)
        elif mode in ("scale_psd", "scale_then_psd"):
            m = float(np.max(np.abs(sub))) if sub.size else 0.0
            if m != 0.0:
                sub = sub / m
            vals_c, vecs_c = np.linalg.eigh(sub)
            vals_c = np.maximum(np.asarray(vals_c, dtype=np.float64), 0.0)
            sub = (vecs_c @ np.diag(vals_c) @ vecs_c.T).astype(np.float64, copy=False)
            sub = 0.5 * (sub + sub.T)
        else:
            raise ValueError(f"unknown RGMS_RGM_EXPERIMENT_SUB_CONDITION mode: {mode!r}")
    if str(os.getenv("RGMS_RGM_EXPERIMENT_SUB_ROUND15", "")).strip().lower() not in (
        "",
        "0",
        "false",
        "no",
        "off",
    ):
        sub = np.round(sub, decimals=15)
    if str(os.getenv("RGMS_RGM_EXPERIMENT_USE_DGEEV", "")).strip().lower() not in (
        "",
        "0",
        "false",
        "no",
        "off",
    ):
        wr, wi, _vl, vr, info = lapack.dgeev(
            np.asarray(sub, dtype=np.float64), compute_vl=0, compute_vr=1
        )
        if int(info) != 0:
            raise RuntimeError(f"dgeev failed with info={int(info)}")
        vals_py = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
        vals_py = np.asarray(vals_py, dtype=np.complex128).ravel(order="F")
        vr = np.asarray(vr, dtype=np.float64)
        n = int(vr.shape[0])
        vecs_py = np.zeros((n, n), dtype=np.complex128)
        k = 0
        while k < n:
            if abs(float(wi[k])) < 1e-300:
                vecs_py[:, k] = vr[:, k]
                k += 1
            else:
                vecs_py[:, k] = vr[:, k] + 1j * vr[:, k + 1]
                vecs_py[:, k + 1] = vr[:, k] - 1j * vr[:, k + 1]
                k += 2
    else:
        vals_py, vecs_py = spla.eig(sub, check_finite=False, overwrite_a=False)
    vals_py = np.asarray(vals_py, dtype=np.complex128).ravel(order="F")
    vecs_py = np.asarray(vecs_py, dtype=np.complex128)
    if vecs_py.shape != np.asarray(sub_mi).shape:
        vecs_py = np.reshape(vecs_py, np.asarray(sub_mi).shape, order="F")
    jmax_py = int(np.argmax(np.abs(vals_py)))
    absv_py = np.asarray(np.abs(vecs_py[:, jmax_py]), dtype=np.float64).ravel()
    if str(os.getenv("RGMS_RGM_EXPERIMENT_ABSV_ROUND15", "")).strip().lower() not in (
        "",
        "0",
        "false",
        "no",
        "off",
    ):
        absv_py = np.round(absv_py, decimals=15)
    order_py = _sort_abs_descend_matlab_like(absv_py)
    j_take_py = order_py[: min(len(order_py), int(dx))]
    e_top_py = absv_py[j_take_py]
    j_take_py = j_take_py[e_top_py >= float(u_thresh)]
    chosen_py = np.asarray(active_before, dtype=np.int64).ravel()[j_take_py]
    return (
        jmax_py,
        np.asarray(order_py, dtype=np.int64),
        np.asarray(chosen_py, dtype=np.int64),
        np.asarray(vals_py, dtype=np.complex128),
    )


def _normalize_vals_for_record(vals: np.ndarray, n: int) -> np.ndarray:
    arr = np.asarray(vals, dtype=np.complex128)
    if arr.ndim == 2 and arr.shape == (n, n):
        return np.diag(arr).astype(np.complex128, copy=False).ravel(order="F")
    flat = arr.ravel(order="F")
    if flat.size == n:
        return flat
    if flat.size == n * n:
        return np.diag(np.reshape(flat, (n, n), order="F")).astype(np.complex128, copy=False).ravel(order="F")
    raise ValueError(f"unexpected eigenvalue payload shape/size: shape={arr.shape} size={flat.size} n={n}")


def _top2_abs_gap(vals: np.ndarray) -> float:
    a = np.sort(np.abs(np.asarray(vals, dtype=np.complex128).ravel()))
    if a.size < 2:
        return float("nan")
    return float(a[-1] - a[-2])


def _normalize_vecs_for_record(vecs: np.ndarray, n: int) -> np.ndarray:
    arr = np.asarray(vecs, dtype=np.complex128)
    if arr.shape == (n, n):
        return arr
    flat = arr.ravel(order="F")
    if flat.size != n * n:
        raise ValueError(f"unexpected eigenvector payload shape/size: shape={arr.shape} size={flat.size} n={n}")
    return np.reshape(flat, (n, n), order="F")


def _unit_abs_col_similarity(col_a: np.ndarray, col_b: np.ndarray) -> float:
    a = np.asarray(np.abs(col_a), dtype=np.float64).ravel()
    b = np.asarray(np.abs(col_b), dtype=np.float64).ravel()
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return float("nan")
    return float(np.dot(a / na, b / nb))


def _first_order_divergence(order_a: np.ndarray, order_b: np.ndarray) -> int | None:
    n = min(int(order_a.size), int(order_b.size))
    for k in range(n):
        if int(order_a[k]) != int(order_b[k]):
            return k
    if int(order_a.size) != int(order_b.size):
        return n
    return None


def _load_spectral_workload_records() -> list[dict]:
    cks = _spectral_workload_files()
    if not cks:
        return []
    records: list[dict] = []
    for ck in cks:
        with ck.open("rb") as f:
            payload = pickle.load(f)
        records.extend(list(payload.get("records", [])))
    return records


def test_spm_rgm_group_spectral_workload_fast_replay_oracle():
    """Replay captured spectral decisions against MATLAB references.

    This is the fast bottleneck-2 gate for *Python-native* spectral parity:
    each record recomputes Python eig/sort decisions from the captured ``sub_mi``
    block and compares them to the stored MATLAB decision path from the same run.

    **Important:** SciPy ``eig`` and MATLAB ``eig`` may return the same eigenpairs
    in **different column orders**. The MATLAB line ``[~,j]=max(diag(v),[],1)``
    indexes into *that* decomposition's layout, so raw ``j`` indices are not
    stable cross-library identifiers. This gate therefore asserts **downstream
    discrete choices** (``chosen`` / ``order``) against the captured MATLAB
    reference, while still counting ``j`` mismatches as **diagnostic-only** when
    the principal directions align (see column-profile prints).
    """
    cks = _spectral_workload_files()
    if not cks:
        pytest.skip(
            "spectral workload checkpoint missing "
            "(run exhaustive once with RGMS_FSL_CAPTURE_RGM_SPECTRAL_WORKLOAD=1, "
            "RGMS_FSL_RGM_MATLAB_MI_PUSH=1, RGMS_FSL_RGM_MATLAB_EIG=1)"
        )
    total = 0
    # Python replay determinism wrt stored Python capture payload.
    py_self_jmax_mismatch = 0
    py_self_order_mismatch = 0
    py_self_chosen_mismatch = 0
    # Python-native vs captured MATLAB reference (core parity signal).
    py_vs_mat_order_mismatch = 0
    py_vs_mat_chosen_mismatch = 0
    py_vs_mat_jmax_index_mismatch = 0
    mat_ref_missing = 0
    mismatch_examples: list[str] = []
    mismatch_spectral_profiles: list[str] = []
    mismatch_column_profiles: list[str] = []
    mismatch_rank_profiles: list[str] = []
    first_diff_ranks: list[int] = []
    first_diff_delta_abs: list[float] = []
    global_max_abs_col_diff = 0.0
    global_max_abs_col_diff_rec: tuple[int, int] | None = None
    for ck in cks:
        with ck.open("rb") as f:
            payload = pickle.load(f)
        records = list(payload.get("records", []))
        if not records:
            continue
        for rec in records:
            total += 1
            sub_mi = np.asarray(rec["sub_mi"], dtype=np.float64)
            active = np.asarray(rec["active_before"], dtype=np.int64).ravel()
            dx = int(rec["dx"])
            u_thresh = float(rec["u_thresh"])
            jmax_py, order_py, chosen_py, vals_py = _replay_python_spectral_decision(
                sub_mi, active, dx, u_thresh
            )
            if jmax_py != int(rec["jmax_py"]):
                py_self_jmax_mismatch += 1
            if not np.array_equal(order_py, np.asarray(rec["order_py"], dtype=np.int64).ravel()):
                py_self_order_mismatch += 1
            if not np.array_equal(chosen_py, np.asarray(rec["chosen_py"], dtype=np.int64).ravel()):
                py_self_chosen_mismatch += 1

            order_mat = rec.get("order_mat")
            chosen_mat = rec.get("chosen_mat")
            jmax_mat_stored = rec.get("jmax_mat")
            if order_mat is None or chosen_mat is None:
                mat_ref_missing += 1
                continue
            order_mat_arr = np.asarray(order_mat, dtype=np.int64).ravel()
            chosen_mat_arr = np.asarray(chosen_mat, dtype=np.int64).ravel()
            j_mis_diag = (
                jmax_mat_stored is not None and int(jmax_py) != int(jmax_mat_stored)
            )
            o_mis = not np.array_equal(order_py, order_mat_arr)
            c_mis = not np.array_equal(chosen_py, chosen_mat_arr)
            if j_mis_diag:
                py_vs_mat_jmax_index_mismatch += 1
            if o_mis:
                py_vs_mat_order_mismatch += 1
            if c_mis:
                py_vs_mat_chosen_mismatch += 1
            if (j_mis_diag or o_mis or c_mis) and len(mismatch_examples) < 12:
                mismatch_examples.append(
                    "record_id="
                    f"{rec.get('record_id', rec.get('idx', '?'))} lev={rec.get('lev_call', rec.get('lev', '?'))} "
                    f"stream={rec.get('stream_idx', rec.get('stream', '?'))} iter={rec.get('iter_idx', '?')} "
                    f"j(py/mat_stored)={jmax_py}/{jmax_mat_stored} "
                    f"order_mis={int(o_mis)} chosen_mis={int(c_mis)}"
                )
            if (j_mis_diag or o_mis or c_mis) and len(mismatch_spectral_profiles) < 12:
                vals_mat_norm = _normalize_vals_for_record(np.asarray(rec["vals_mat"]), int(active.size))
                py_top = float(np.abs(vals_py[jmax_py]))
                jm = int(jmax_mat_stored) if jmax_mat_stored is not None else int(np.argmax(np.abs(vals_mat_norm)))
                mat_top = float(np.abs(vals_mat_norm[jm]))
                mismatch_spectral_profiles.append(
                    "record_id="
                    f"{rec.get('record_id', rec.get('idx', '?'))} "
                    f"n={int(active.size)} "
                    f"top_abs(py/mat)={py_top:.12e}/{mat_top:.12e} "
                    f"top2_gap(py/mat)={_top2_abs_gap(vals_py):.12e}/{_top2_abs_gap(vals_mat_norm):.12e}"
                )
            if (j_mis_diag or o_mis or c_mis) and len(mismatch_column_profiles) < 12:
                n = int(active.size)
                vecs_py = _normalize_vecs_for_record(np.asarray(rec["vecs_py"]), n)
                vecs_mat = _normalize_vecs_for_record(np.asarray(rec["vecs_mat"]), n)
                py_col = vecs_py[:, jmax_py]
                sims = np.asarray(
                    [_unit_abs_col_similarity(py_col, vecs_mat[:, kk]) for kk in range(n)],
                    dtype=np.float64,
                )
                best_k = int(np.nanargmax(sims))
                best_sim = float(sims[best_k])
                jm = int(jmax_mat_stored) if jmax_mat_stored is not None else best_k
                sim_at_jmat = float(sims[jm])
                mismatch_column_profiles.append(
                    "record_id="
                    f"{rec.get('record_id', rec.get('idx', '?'))} "
                    f"j_py={jmax_py} j_mat_stored={jmax_mat_stored} "
                    f"best_mat_col_for_py={best_k} "
                    f"sim(best)={best_sim:.12e} sim(j_mat_stored)={sim_at_jmat:.12e}"
                )
            if j_mis_diag or o_mis or c_mis:
                n = int(active.size)
                vecs_py = _normalize_vecs_for_record(np.asarray(rec["vecs_py"]), n)
                vecs_mat = _normalize_vecs_for_record(np.asarray(rec["vecs_mat"]), n)
                jm = int(jmax_mat_stored) if jmax_mat_stored is not None else int(np.argmax(np.abs(vals_py)))
                absv_py = np.asarray(np.abs(vecs_py[:, jmax_py]), dtype=np.float64).ravel()
                absv_mat = np.asarray(np.abs(vecs_mat[:, jm]), dtype=np.float64).ravel()
                max_abs_col_diff = float(np.max(np.abs(absv_py - absv_mat)))
                if max_abs_col_diff > global_max_abs_col_diff:
                    global_max_abs_col_diff = max_abs_col_diff
                    global_max_abs_col_diff_rec = (
                        int(rec.get("record_id", rec.get("idx", -1))),
                        int(rec.get("iter_idx", -1)),
                    )
                k0 = _first_order_divergence(order_py, order_mat_arr)
                if k0 is not None:
                    first_diff_ranks.append(int(k0))
                    py_idx = int(order_py[k0]) if k0 < int(order_py.size) else -1
                    mat_idx = int(order_mat_arr[k0]) if k0 < int(order_mat_arr.size) else -1
                    if py_idx >= 0 and mat_idx >= 0:
                        delta_at_first = float(abs(absv_py[py_idx] - absv_mat[mat_idx]))
                        first_diff_delta_abs.append(delta_at_first)
                    if len(mismatch_rank_profiles) < 12:
                        mismatch_rank_profiles.append(
                            "record_id="
                            f"{rec.get('record_id', rec.get('idx', '?'))} "
                            f"first_diff_rank={k0} py_idx={py_idx} mat_idx={mat_idx} "
                            f"abs_py(py_idx)={(absv_py[py_idx] if py_idx >= 0 else float('nan')):.12e} "
                            f"abs_mat(mat_idx)={(absv_mat[mat_idx] if mat_idx >= 0 else float('nan')):.12e} "
                            f"max_abs_col_diff={max_abs_col_diff:.12e}"
                        )
        print(
            "[RGM-SPECTRAL-REPLAY] file="
            f"{ck.name} records={len(records)} "
            f"py_self(jmax/order/chosen)="
            f"{py_self_jmax_mismatch}/{py_self_order_mismatch}/{py_self_chosen_mismatch} "
            f"py_vs_mat(order/chosen)={py_vs_mat_order_mismatch}/{py_vs_mat_chosen_mismatch} "
            f"j_index_diag_only={py_vs_mat_jmax_index_mismatch} "
            f"mat_ref_missing={mat_ref_missing}",
            flush=True,
        )
    assert total > 0
    first_rank_summary = (
        "none"
        if not first_diff_ranks
        else (
            f"min={int(min(first_diff_ranks))} "
            f"median={float(np.median(np.asarray(first_diff_ranks, dtype=np.float64))):.1f} "
            f"max={int(max(first_diff_ranks))}"
        )
    )
    first_delta_summary = (
        "none"
        if not first_diff_delta_abs
        else (
            f"min={float(np.min(np.asarray(first_diff_delta_abs, dtype=np.float64))):.12e} "
            f"median={float(np.median(np.asarray(first_diff_delta_abs, dtype=np.float64))):.12e} "
            f"max={float(np.max(np.asarray(first_diff_delta_abs, dtype=np.float64))):.12e}"
        )
    )
    print(
        "[RGM-SPECTRAL-REPLAY] total="
        f"{total} py_self(jmax/order/chosen)="
        f"{py_self_jmax_mismatch}/{py_self_order_mismatch}/{py_self_chosen_mismatch} "
        f"py_vs_mat(order/chosen)={py_vs_mat_order_mismatch}/{py_vs_mat_chosen_mismatch} "
        f"j_index_diag_only={py_vs_mat_jmax_index_mismatch} "
        f"first_diff_rank_stats={first_rank_summary} "
        f"first_diff_abs_delta_stats={first_delta_summary} "
        f"global_max_abs_col_diff={global_max_abs_col_diff:.12e} "
        f"global_max_abs_col_diff_rec={global_max_abs_col_diff_rec} "
        f"mat_ref_missing={mat_ref_missing}",
        flush=True,
    )
    if mismatch_examples:
        print("[RGM-SPECTRAL-REPLAY] top_mismatch_records:", flush=True)
        for line in mismatch_examples:
            print(f"  - {line}", flush=True)
    if mismatch_spectral_profiles:
        print("[RGM-SPECTRAL-REPLAY] top_mismatch_spectral_profiles:", flush=True)
        for line in mismatch_spectral_profiles:
            print(f"  - {line}", flush=True)
    if mismatch_column_profiles:
        print("[RGM-SPECTRAL-REPLAY] top_mismatch_column_profiles:", flush=True)
        for line in mismatch_column_profiles:
            print(f"  - {line}", flush=True)
    if mismatch_rank_profiles:
        print("[RGM-SPECTRAL-REPLAY] top_mismatch_rank_profiles:", flush=True)
        for line in mismatch_rank_profiles:
            print(f"  - {line}", flush=True)
    assert mat_ref_missing == 0, (
        f"spectral workload missing MATLAB references on {mat_ref_missing} records"
    )
    assert py_self_jmax_mismatch == 0 and py_self_order_mismatch == 0 and py_self_chosen_mismatch == 0, (
        "Python replay is not deterministic against captured Python spectral records"
    )
    assert py_vs_mat_order_mismatch == 0 and py_vs_mat_chosen_mismatch == 0, (
        "Python-native spectral order/chosen diverge from captured MATLAB references: "
        f"order={py_vs_mat_order_mismatch}, chosen={py_vs_mat_chosen_mismatch}. "
        f"(j index mismatches across eig layouts are diagnostic-only; count={py_vs_mat_jmax_index_mismatch})"
    )


def test_spm_rgm_group_spectral_workload_blocker_micro_oracle():
    """Focused strict gate for highest-impact blocker records.

    Uses the captured workload records that currently drive chosen-membership
    divergence (`record_id` 2..6). This keeps the byte-exact inner loop tight:
    any candidate that cannot close these records is unlikely to close full replay.
    """
    blocker_ids = {2, 3, 4, 5, 6}
    records = _load_spectral_workload_records()
    if not records:
        pytest.skip(
            "spectral workload checkpoint missing "
            "(run exhaustive once with RGMS_FSL_CAPTURE_RGM_SPECTRAL_WORKLOAD=1, "
            "RGMS_FSL_RGM_MATLAB_MI_PUSH=1, RGMS_FSL_RGM_MATLAB_EIG=1)"
        )

    total_blocker = 0
    order_mismatch = 0
    chosen_mismatch = 0
    detail: list[str] = []
    for rec in records:
        rid = int(rec.get("record_id", rec.get("idx", -1)))
        if rid not in blocker_ids:
            continue
        total_blocker += 1
        sub_mi = np.asarray(rec["sub_mi"], dtype=np.float64)
        active = np.asarray(rec["active_before"], dtype=np.int64).ravel()
        dx = int(rec["dx"])
        u_thresh = float(rec["u_thresh"])
        _, order_py, chosen_py, _ = _replay_python_spectral_decision(sub_mi, active, dx, u_thresh)
        order_mat = np.asarray(rec["order_mat"], dtype=np.int64).ravel()
        chosen_mat = np.asarray(rec["chosen_mat"], dtype=np.int64).ravel()
        om = not np.array_equal(order_py, order_mat)
        cm = not np.array_equal(chosen_py, chosen_mat)
        order_mismatch += int(om)
        chosen_mismatch += int(cm)
        if om or cm:
            detail.append(
                f"id={rid} iter={int(rec.get('iter_idx', -1))} "
                f"order_mis={int(om)} chosen_mis={int(cm)} "
                f"chosen_py={chosen_py.tolist()} chosen_mat={chosen_mat.tolist()}"
            )

    assert total_blocker == len(blocker_ids), (
        f"expected blocker records {sorted(blocker_ids)} once each; found {total_blocker} entries"
    )
    if detail:
        print("[RGM-SPECTRAL-BLOCKER-MICRO] mismatch detail:", flush=True)
        for line in detail:
            print(f"  - {line}", flush=True)
    assert order_mismatch == 0 and chosen_mismatch == 0, (
        "Blocker micro-oracle diverges from MATLAB references: "
        f"order={order_mismatch}, chosen={chosen_mismatch}"
    )
