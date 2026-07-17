"""Read-only Entry 4 spectral / eig diagnosis helpers (see repo-root ``eig.md`` §19)."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

import numpy as np
import scipy.linalg as spla

from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from python_src.utils.eig_nobalance import eig_nobalance, geevx_available, resolve_backend

# Failure stages (first failing stage in pipeline order).
STAGE_OK = "OK"
STAGE_W_SPECTRUM = "W_SPECTRUM"  # |w| layout / dominant mode index
STAGE_PRINCIPAL_COL = "PRINCIPAL_COL"  # jmax matches but |V[:,j]| vector differs
STAGE_SORT_ABS = "SORT_ABS"  # abs(e(:,jmax)) sort permutation differs
STAGE_CHOSEN_THRESH = "CHOSEN_THRESH"  # u_thresh + dx cap on sorted order
STAGE_PROBE_CAPTURE = "PROBE_CAPTURE"  # dump record != recompute from vals/vecs


def sub_hash(sub: np.ndarray) -> str:
    arr = np.asarray(sub, dtype=np.float64, order="F")
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def rgm_spectral_decisions(sub: np.ndarray, w: np.ndarray, v: np.ndarray) -> dict[str, Any]:
    """Mirror ``spm_rgm_group`` post-eig indices for one ``MI`` block."""
    sub = np.asarray(sub, dtype=np.float64)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    n = int(sub.shape[0])
    if v.shape != (n, n):
        v = np.reshape(v, sub.shape, order="F")
    jmax = int(np.argmax(np.abs(w)))
    col = v[:, jmax]
    absv = np.asarray(np.abs(col), dtype=np.float64).ravel()
    order = _sort_abs_descend_matlab_like(absv)
    return {
        "n": n,
        "jmax": jmax,
        "order": order,
        "absv": absv,
        "w": w,
        "v": v,
    }


def _top_k_argmax_abs_w(w: np.ndarray, k: int = 5) -> list[dict[str, Any]]:
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    aw = np.abs(w)
    if aw.size == 0:
        return []
    k = min(int(k), int(aw.size))
    # Stable: ascending index order among equals (matches np.argmax first-max).
    idx = np.argsort(-aw, kind="mergesort")[:k]
    return [
        {"col": int(i), "abs_w": float(aw[i]), "w": complex(w[i])}
        for i in idx
    ]


def analyze_w_stage(w_ref: np.ndarray, w_got: np.ndarray) -> dict[str, Any]:
    """Eigenvalue-vector stage (MATLAB ``diag(v)`` layout as 1-D ``w``)."""
    w_ref = np.asarray(w_ref, dtype=np.complex128).ravel(order="F")
    w_got = np.asarray(w_got, dtype=np.complex128).ravel(order="F")
    same_len = int(w_ref.size) == int(w_got.size)
    jmax_ref = int(np.argmax(np.abs(w_ref))) if w_ref.size else -1
    jmax_got = int(np.argmax(np.abs(w_got))) if w_got.size else -1
    out: dict[str, Any] = {
        "same_length": same_len,
        "jmax_ref": jmax_ref,
        "jmax_got": jmax_got,
        "jmax_match": bool(jmax_ref == jmax_got),
        "abs_w_at_jmax_ref": float(np.abs(w_ref[jmax_ref])) if w_ref.size else None,
        "abs_w_at_jmax_got": float(np.abs(w_got[jmax_got])) if w_got.size else None,
        "top5_ref": _top_k_argmax_abs_w(w_ref, 5),
        "top5_got": _top_k_argmax_abs_w(w_got, 5),
    }
    if same_len:
        dw = np.abs(w_got - w_ref)
        out["max_abs_w_diff"] = float(np.max(dw))
        out["mean_abs_w_diff"] = float(np.mean(dw))
        out["argmax_abs_w_diff_col"] = int(np.argmax(dw))
        # Same multiset of |w| (weak diagnostic — ignores permutation).
        sw_ref = np.sort(np.abs(w_ref))
        sw_got = np.sort(np.abs(w_got))
        out["sorted_abs_w_max_diff"] = float(np.max(np.abs(sw_got - sw_ref)))
    else:
        out["max_abs_w_diff"] = None
    return out


def first_order_mismatch(
    order_ref: np.ndarray, order_got: np.ndarray, absv_ref: np.ndarray, absv_got: np.ndarray
) -> dict[str, Any] | None:
    o_ref = np.asarray(order_ref, dtype=np.int64).ravel()
    o_got = np.asarray(order_got, dtype=np.int64).ravel()
    n = min(o_ref.size, o_got.size)
    for rank in range(n):
        if o_ref[rank] != o_got[rank]:
            ir, ig = int(o_ref[rank]), int(o_got[rank])
            return {
                "rank": int(rank),
                "idx_ref": ir,
                "idx_got": ig,
                "absv_ref": float(absv_ref[ir]),
                "absv_got": float(absv_got[ig]),
                "absv_diff": float(abs(absv_ref[ir] - absv_got[ig])),
            }
    if o_ref.size != o_got.size:
        return {"rank": int(n), "note": "length_mismatch", "len_ref": int(o_ref.size), "len_got": int(o_got.size)}
    return None


def chosen_from_spectral(
    active_before: np.ndarray,
    absv: np.ndarray,
    order: np.ndarray,
    dx: int,
    u_thresh: float,
) -> np.ndarray:
    """Replay ``spm_rgm_group`` threshold + ``dx`` cap after ``sort(abs(...),'descend')``."""
    active = np.asarray(active_before, dtype=np.int64).ravel()
    absv = np.asarray(absv, dtype=np.float64).ravel()
    order = np.asarray(order, dtype=np.int64).ravel()
    j_take = order[: min(len(order), int(dx))]
    e_top = absv[j_take]
    j_take = j_take[e_top >= float(u_thresh)]
    return np.asarray(active[j_take], dtype=np.int64)


def classify_failure_stage(
    ref: dict[str, Any],
    got: dict[str, Any],
    *,
    w_stage: dict[str, Any],
) -> str:
    if not w_stage.get("jmax_match", False):
        return STAGE_W_SPECTRUM
    if float(w_stage.get("max_abs_w_diff") or 0.0) > 1e-10:
        # Large elementwise |w| drift in LAPACK column order — still spectrum stage.
        if float(w_stage.get("max_abs_w_diff") or 0.0) > 1e-6:
            return STAGE_W_SPECTRUM
    v_ref = ref["v"][:, ref["jmax"]]
    v_got = got["v"][:, got["jmax"]]
    if float(np.max(np.abs(np.abs(v_ref) - np.abs(v_got)))) > 1e-12:
        return STAGE_PRINCIPAL_COL
    if not np.array_equal(ref["order"], got["order"]):
        return STAGE_SORT_ABS
    return STAGE_OK


def granular_spectral_report(
    sub: np.ndarray,
    w_ref: np.ndarray,
    v_ref: np.ndarray,
    *,
    eig_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]],
    label: str,
    probe_rec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Stage-by-stage report for one ``sub_mi`` block vs MATLAB reference eigenpairs.

    Stages follow ``spm_rgm_group.m`` after ``eig``:
    ``w`` → ``jmax`` → ``absv`` → ``order`` → ``chosen`` (via ``dx``, ``u_thresh``).
    """
    ref = rgm_spectral_decisions(sub, w_ref, v_ref)
    w_py, v_py = eig_fn(np.asarray(sub, dtype=np.float64))
    got = rgm_spectral_decisions(sub, w_py, v_py)
    w_stage = analyze_w_stage(ref["w"], got["w"])

    absv_ref = ref["absv"]
    absv_got = got["absv"]
    order_mismatch = first_order_mismatch(ref["order"], got["order"], absv_ref, absv_got)

    stage = classify_failure_stage(ref, got, w_stage=w_stage)

    report: dict[str, Any] = {
        "label": label,
        "sub_hash": sub_hash(sub),
        "n": ref["n"],
        "stage": stage,
        "order_ok": bool(np.array_equal(ref["order"], got["order"])),
        "jmax_ok": bool(ref["jmax"] == got["jmax"]),
        "w_stage": w_stage,
        "jmax_ref": ref["jmax"],
        "jmax_got": got["jmax"],
        "max_abs_principal_col_diff": float(
            np.max(np.abs(ref["v"][:, ref["jmax"]] - got["v"][:, got["jmax"]]))
        ),
        "max_absv_diff_at_jmax_col": float(np.max(np.abs(absv_ref - absv_got))),
        "order_first_mismatch": order_mismatch,
    }

    if probe_rec is not None:
        active = np.asarray(probe_rec["active_before"], dtype=np.int64)
        dx = int(probe_rec["dx"])
        u = float(probe_rec["u_thresh"])
        chosen_ref = chosen_from_spectral(active, absv_ref, ref["order"], dx, u)
        chosen_got = chosen_from_spectral(active, absv_got, got["order"], dx, u)
        chosen_mat_probe = np.asarray(probe_rec["chosen_mat"], dtype=np.int64)
        chosen_py_probe = np.asarray(probe_rec["chosen_py"], dtype=np.int64)
        report["context"] = {
            "lev_call": int(probe_rec.get("lev_call", -1)),
            "stream_idx": int(probe_rec.get("stream_idx", -1)),
            "iter_idx": int(probe_rec["iter_idx"]),
            "dx": dx,
            "u_thresh": u,
            "n_active": int(active.size),
        }
        report["chosen"] = {
            "mat_probe": chosen_mat_probe.tolist(),
            "recomputed_mat_eig": chosen_ref.tolist(),
            "recomputed_got_eig": chosen_got.tolist(),
            "mat_probe_vs_recomputed_mat": bool(np.array_equal(chosen_mat_probe, chosen_ref)),
            "got_vs_mat_probe": bool(np.array_equal(chosen_got, chosen_mat_probe)),
            "chosen_ok": bool(np.array_equal(chosen_ref, chosen_got)),
        }
        if not report["chosen"]["mat_probe_vs_recomputed_mat"]:
            report["stage_probe"] = STAGE_PROBE_CAPTURE
        elif stage == STAGE_OK and not report["chosen"]["chosen_ok"]:
            report["stage"] = STAGE_CHOSEN_THRESH

    return report


def compare_eig_to_matlab_ref(
    sub: np.ndarray,
    w_ref: np.ndarray,
    v_ref: np.ndarray,
    *,
    eig_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]],
    label: str,
    probe_rec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summary compare (legacy) plus embedded ``granular`` when ``probe_rec`` supplied."""
    g = granular_spectral_report(sub, w_ref, v_ref, eig_fn=eig_fn, label=label, probe_rec=probe_rec)
    return {
        "label": g["label"],
        "sub_hash": g["sub_hash"],
        "n": g["n"],
        "order_ok": g["order_ok"],
        "jmax_ok": g["jmax_ok"],
        "jmax_ref": g["jmax_ref"],
        "jmax_got": g["jmax_got"],
        "max_abs_w_diff": g["w_stage"].get("max_abs_w_diff"),
        "max_abs_principal_col_diff": g["max_abs_principal_col_diff"],
        "stage": g["stage"],
        "granular": g,
    }


def probe_record_decisions(rec: dict[str, Any]) -> dict[str, Any]:
    """Decisions from one Python dump probe record (MATLAB eig + SciPy lane)."""
    sub = np.asarray(rec["sub_mi"], dtype=np.float64)
    w_mat = np.asarray(rec["vals_mat"], dtype=np.complex128)
    v_mat = np.asarray(rec["vecs_mat"], dtype=np.complex128)
    w_py = np.asarray(rec["vals_py"], dtype=np.complex128)
    v_py = np.asarray(rec["vecs_py"], dtype=np.complex128)
    dec_mat = rgm_spectral_decisions(sub, w_mat, v_mat)
    dec_scipy = rgm_spectral_decisions(sub, w_py, v_py)
    order_mat_probe = np.asarray(rec["order_mat"], dtype=np.int64)
    order_py_probe = np.asarray(rec["order_py"], dtype=np.int64)
    chosen_mat = np.asarray(rec["chosen_mat"], dtype=np.int64)
    chosen_py = np.asarray(rec["chosen_py"], dtype=np.int64)
    om = first_order_mismatch(dec_mat["order"], order_mat_probe, dec_mat["absv"], dec_mat["absv"])
    oy = first_order_mismatch(dec_scipy["order"], order_py_probe, dec_scipy["absv"], dec_scipy["absv"])
    return {
        "sub_hash": sub_hash(sub),
        "n": dec_mat["n"],
        "lev_call": int(rec.get("lev_call", -1)),
        "stream_idx": int(rec.get("stream_idx", -1)),
        "iter_idx": int(rec["iter_idx"]),
        "order_mat_recomputed": dec_mat["order"].tolist(),
        "order_mat_probe": order_mat_probe.tolist(),
        "order_py_recomputed": dec_scipy["order"].tolist(),
        "order_py_probe": order_py_probe.tolist(),
        "mat_recompute_matches_probe": bool(np.array_equal(dec_mat["order"], order_mat_probe)),
        "scipy_vs_matlab_order": bool(np.array_equal(dec_mat["order"], order_py_probe)),
        "scipy_vs_matlab_first_mismatch": oy,
        "mat_capture_first_mismatch": om,
        "chosen_mat": chosen_mat.tolist(),
        "chosen_py": chosen_py.tolist(),
        "chosen_mat_vs_py": bool(np.array_equal(chosen_mat, chosen_py)),
    }


def stage_counts(reports: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in reports:
        st = str(r.get("stage", "UNKNOWN"))
        counts[st] = counts.get(st, 0) + 1
    return counts


def scipy_eig_fn(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return spla.eig(a, check_finite=False, overwrite_a=False)
