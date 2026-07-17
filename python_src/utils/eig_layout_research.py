"""
Research helpers for MATLAB ``eig(...,'nobalance')`` column layout (not production API).

Used by Entry 4 inspection instruments (``eig.md`` §20). Goal: quantify whether
failures are multiset/permutation vs true spectrum drift before inventing a full
MATLAB-layout eigen solver.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def matrix_fingerprint(sub: np.ndarray) -> dict[str, Any]:
    """Scalar descriptors for one ``MI(i,i)`` block (audit / clustering)."""
    a = np.asarray(sub, dtype=np.float64, order="F")
    n = int(a.shape[0])
    sym = a - a.T
    aw = np.abs(a)
    return {
        "n": n,
        "fro_norm": float(np.linalg.norm(a, ord="fro")),
        "max_abs_entry": float(np.max(aw)) if aw.size else 0.0,
        "symmetry_residual_max": float(np.max(np.abs(sym))) if sym.size else 0.0,
        "symmetry_residual_fro": float(np.linalg.norm(sym, ord="fro")),
        "is_symmetric_1e12": bool(float(np.max(np.abs(sym))) <= 1e-12),
        "trace": float(np.trace(a)),
        "diag_min": float(np.min(np.diag(a))),
        "diag_max": float(np.max(np.diag(a))),
    }


def greedy_match_abs_w(
    w_ref: np.ndarray, w_got: np.ndarray, *, tol: float = 1e-9
) -> dict[str, Any]:
    """
    Greedy one-to-one match on |w| (smallest residual first).

    Does not prove optimal assignment; sufficient for inspection when n <= 2657
    and failures are few.
    """
    w_ref = np.asarray(w_ref, dtype=np.complex128).ravel(order="F")
    w_got = np.asarray(w_got, dtype=np.complex128).ravel(order="F")
    n = min(w_ref.size, w_got.size)
    if n == 0:
        return {"n": 0, "pairs": [], "max_pair_abs_w_diff": 0.0, "mean_pair_abs_w_diff": 0.0}

    aw_ref = np.abs(w_ref[:n])
    aw_got = np.abs(w_got[:n])
    used_g = np.zeros(n, dtype=bool)
    pairs: list[dict[str, Any]] = []
    residuals: list[float] = []

    for i in range(n):
        best_j = -1
        best_d = np.inf
        for j in range(n):
            if used_g[j]:
                continue
            d = float(abs(aw_ref[i] - aw_got[j]))
            if d < best_d:
                best_d = d
                best_j = j
        if best_j < 0:
            break
        used_g[best_j] = True
        dw = float(np.abs(w_got[best_j] - w_ref[i]))
        residuals.append(dw)
        pairs.append(
            {
                "ref_col": int(i),
                "got_col": int(best_j),
                "abs_w_ref": float(aw_ref[i]),
                "abs_w_got": float(aw_got[best_j]),
                "abs_w_residual": float(best_d),
                "w_diff": dw,
                "phase_diff_rad": float(np.angle(w_got[best_j]) - np.angle(w_ref[i])),
            }
        )

    res_arr = np.asarray(residuals, dtype=np.float64)
    return {
        "n": n,
        "n_pairs": len(pairs),
        "pairs": pairs,
        "max_pair_abs_w_diff": float(np.max(res_arr)) if res_arr.size else None,
        "mean_pair_abs_w_diff": float(np.mean(res_arr)) if res_arr.size else None,
        "all_pairs_under_tol": bool(np.all(res_arr <= tol)) if res_arr.size else True,
        "tol": float(tol),
    }


def cyclic_shift_scores(w_ref: np.ndarray, w_got: np.ndarray, *, max_shift: int = 3) -> list[dict[str, Any]]:
    """Test whether ``w_got`` is a cyclic permutation of ``w_ref`` (column-order hypothesis)."""
    w_ref = np.asarray(w_ref, dtype=np.complex128).ravel(order="F")
    w_got = np.asarray(w_got, dtype=np.complex128).ravel(order="F")
    n = min(w_ref.size, w_got.size)
    out: list[dict[str, Any]] = []
    for shift in range(-max_shift, max_shift + 1):
        if shift == 0:
            perm = np.arange(n, dtype=np.int64)
        else:
            perm = (np.arange(n, dtype=np.int64) + shift) % n
        dw = np.abs(w_got[:n] - w_ref[perm])
        out.append(
            {
                "shift": int(shift),
                "max_abs_w_diff": float(np.max(dw)),
                "mean_abs_w_diff": float(np.mean(dw)),
                "jmax_ref": int(np.argmax(np.abs(w_ref[:n]))),
                "jmax_got": int(np.argmax(np.abs(w_got[:n]))),
                "jmax_got_under_shift": int(np.argmax(np.abs(w_got[:n]))),
            }
        )
    best = min(out, key=lambda x: x["max_abs_w_diff"])
    return {"scores": out, "best_shift": int(best["shift"]), "best_max_abs_w_diff": float(best["max_abs_w_diff"])}


def column_permutation_report(
    w_ref: np.ndarray,
    w_got: np.ndarray,
    v_ref: np.ndarray,
    v_got: np.ndarray,
    *,
    jmax_ref: int,
    jmax_got: int,
) -> dict[str, Any]:
    """After greedy |w| match, compare principal columns at matched and jmax indices."""
    gm = greedy_match_abs_w(w_ref, w_got)
    v_ref = np.asarray(v_ref, dtype=np.complex128, order="F")
    v_got = np.asarray(v_got, dtype=np.complex128, order="F")
    col_jmax = {
        "max_abs_principal_diff": float(np.max(np.abs(v_ref[:, jmax_ref] - v_got[:, jmax_got]))),
        "max_abs_abs_principal_diff": float(
            np.max(np.abs(np.abs(v_ref[:, jmax_ref]) - np.abs(v_got[:, jmax_got])))
        ),
    }
    matched_cols: list[dict[str, Any]] = []
    for p in gm["pairs"][: min(10, len(gm["pairs"]))]:
        ir, ig = int(p["ref_col"]), int(p["got_col"])
        matched_cols.append(
            {
                "ref_col": ir,
                "got_col": ig,
                "w_diff": p["w_diff"],
                "max_abs_V_diff": float(np.max(np.abs(v_ref[:, ir] - v_got[:, ig]))),
            }
        )
    return {"greedy_w_match": gm, "principal_at_jmax": col_jmax, "matched_col_samples": matched_cols}


def l2_normalize_principal_column(w: np.ndarray, v: np.ndarray) -> np.ndarray:
    """L2-normalize ``V[:,jmax]`` (MATLAB ``eig`` columns are unit-norm on dumps)."""
    from python_src.utils.eig_spectral_policy import l2_normalize_principal_column as _fn

    return _fn(w, v)


def reorder_eigenpairs_ascending_abs_w(
    w: np.ndarray, v: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Reorder columns so ``|w[0]| <= |w[1]| <= ...`` (MATLAB dump invariant on FSL blocks).

    NumPy ``linalg.eig`` column order is arbitrary; MATLAB ``diag(v)`` on captured Entry 4
    blocks is ascending in ``|w|`` (``eig.md`` §22).
    """
    from python_src.utils.eig_spectral_policy import reorder_eigenpairs_ascending_abs_w as _fn

    return _fn(w, v)


def permute_eigenpairs(
    w: np.ndarray, v: np.ndarray, perm: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Reorder eigenpair columns: ``w_out[i] = w[perm[i]]``, ``V_out[:,i] = V[:,perm[i]]``."""
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    p = np.asarray(perm, dtype=np.int64).ravel()
    return w[p].copy(), v[:, p].copy()


def assign_eigenpairs_greedy_w(
    w_got: np.ndarray,
    v_got: np.ndarray,
    w_ref: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Reorder ``(w_got, v_got)`` columns so ``|w|`` aligns with ``w_ref`` (inspection / ceiling tests).

    Returns ``(w_out, v_out, perm)`` where ``perm[i]`` is the source column used for MATLAB index ``i``.
    """
    w_got = np.asarray(w_got, dtype=np.complex128).ravel(order="F")
    v_got = np.asarray(v_got, dtype=np.complex128, order="F")
    w_ref = np.asarray(w_ref, dtype=np.complex128).ravel(order="F")
    n = w_got.size
    used = np.zeros(n, dtype=bool)
    perm = np.zeros(n, dtype=np.int64)
    aw_ref = np.abs(w_ref)
    aw_got = np.abs(w_got)
    for i in range(n):
        best_j = -1
        best_d = np.inf
        for j in range(n):
            if used[j]:
                continue
            d = float(abs(aw_ref[i] - aw_got[j]))
            if d < best_d:
                best_d = d
                best_j = j
        if best_j < 0:
            raise RuntimeError("greedy w assignment failed")
        used[best_j] = True
        perm[i] = best_j
    return permute_eigenpairs(w_got, v_got, perm)


def align_column_signs_to_reference(v_got: np.ndarray, v_ref: np.ndarray) -> np.ndarray:
    """Flip column sign where ``real(dot) < 0`` (symmetric real-case inspection helper)."""
    v_got = np.asarray(v_got, dtype=np.complex128, order="F").copy()
    v_ref = np.asarray(v_ref, dtype=np.complex128, order="F")
    n = min(v_got.shape[1], v_ref.shape[1])
    for i in range(n):
        if float(np.vdot(v_got[:, i], v_ref[:, i]).real) < 0.0:
            v_got[:, i] *= -1.0
    return v_got


def sort_ulp_failure_report(
    absv_ref: np.ndarray,
    absv_got: np.ndarray,
    order_ref: np.ndarray,
    order_got: np.ndarray,
    *,
    max_rows: int = 16,
) -> dict[str, Any]:
    """
    Diagnose ``sort(abs(...),'descend')`` divergence when principal ``absv`` vectors are ULP-close.
    """
    absv_ref = np.asarray(absv_ref, dtype=np.float64).ravel()
    absv_got = np.asarray(absv_got, dtype=np.float64).ravel()
    order_ref = np.asarray(order_ref, dtype=np.int64).ravel()
    order_got = np.asarray(order_got, dtype=np.int64).ravel()
    n = min(absv_ref.size, absv_got.size)
    rows: list[dict[str, Any]] = []
    first_rank = None
    for rank in range(n):
        ir, ig = int(order_ref[rank]), int(order_got[rank])
        if ir != ig and first_rank is None:
            first_rank = rank
        if ir != ig or rank < max_rows:
            rows.append(
                {
                    "rank": rank,
                    "idx_ref": ir,
                    "idx_got": ig,
                    "match": bool(ir == ig),
                    "absv_ref": float(absv_ref[ir]),
                    "absv_got": float(absv_got[ig]),
                    "absv_delta": float(abs(absv_ref[ir] - absv_got[ig])),
                }
            )
    max_absv_diff = float(np.max(np.abs(absv_ref[:n] - absv_got[:n])))
    return {
        "max_absv_vector_diff": max_absv_diff,
        "first_mismatch_rank": first_rank,
        "n_rank_mismatches": int(np.sum(order_ref[:n] != order_got[:n])),
        "rows": rows[: max_rows + 8],
    }
