"""
Expected information gain (mutual information) for Dirichlet parameters.

Translated from spm_dir_MI.m (Pass 1). Local entropy helper mirrors
subfunction `spm_H`, using SciPy `psi` (digamma) like MATLAB `psi`.

**Cell + `h` branch:** staged MATLAB line 25 calls `spm_dir_MI(a{g},c{g},h)` with
the full multimodal `h`, which mis-dimensions `sum(A,1)*H` when `numel(h)>1`.
Python passes the per-modality slice `h[g]` (aligned with `a{g}` / `c{g}`); oracle
for multimodal + `h` compares against the MATLAB **sum of per-modality** calls.
"""

from __future__ import annotations

import math
import os
from typing import Any, List, Optional, Sequence, Union

import numpy as np
from scipy.special import psi

from matlab_compat import as_matlab_array
from python_src.spm_cat import spm_cat
from python_src.spm_log import spm_log


ArrayLike = Union[np.ndarray, List[Any], tuple]

_MISSING = object()
_EXPERIMENT_STATS = {
    "one_arg_calls": 0,
    "row_ulp_triggered": 0,
}


def _trace_enabled() -> bool:
    return str(os.getenv("RGMS_DIR_MI_TRACE", "0")).strip().lower() in ("1", "true", "yes", "on")


def _trace(msg: str) -> None:
    if _trace_enabled():
        print(f"[DIR-MI-TRACE] {msg}", flush=True)


def _env_flag(name: str) -> bool:
    return str(os.getenv(name, "0")).strip().lower() in ("1", "true", "yes", "on")


def _stats_enabled() -> bool:
    return _env_flag("RGMS_DIR_MI_EXPERIMENT_STATS")


def reset_experiment_stats() -> None:
    _EXPERIMENT_STATS["one_arg_calls"] = 0
    _EXPERIMENT_STATS["row_ulp_triggered"] = 0


def get_experiment_stats() -> dict:
    return {
        "one_arg_calls": int(_EXPERIMENT_STATS["one_arg_calls"]),
        "row_ulp_triggered": int(_EXPERIMENT_STATS["row_ulp_triggered"]),
    }


def _iscell_arg(x: Any) -> bool:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return True
    if isinstance(x, (list, tuple)) and len(x) > 0:
        # MATLAB `iscell(a)`; avoid treating a plain numeric list like `[1, 2]`
        # as a cell of modalities (those are `double` in MATLAB).
        if all(isinstance(item, np.ndarray) for item in x):
            return True
        if isinstance(x[0], (list, tuple)):
            return True
    return False


def _numel_cell(x: Sequence[Any]) -> int:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return int(x.size)
    return len(x)


def _cell_get(x: Sequence[Any], index: int) -> Any:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return x.reshape(-1, order="F")[index]
    return x[index]


def _marginals_sum_matlab_like(a_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``sum(a,2)`` and ``sum(a,1)`` with sequential float accumulation (MATLAB ``sum``).

    NumPy ``np.sum(..., axis=...)`` can use pairwise reduction; SPM marginals feed
    ``spm_H`` and drive MI cancellation at ~ULP scale on large grids.
    """
    a_arr = np.asarray(a_arr, dtype=np.float64)
    nr, nc = int(a_arr.shape[0]), int(a_arr.shape[1])
    col_sums = np.zeros((nr, 1), dtype=np.float64)
    row_sums = np.zeros((1, nc), dtype=np.float64)
    for i in range(nr):
        s = 0.0
        for j in range(nc):
            s += float(a_arr[i, j])
        col_sums[i, 0] = s
    for j in range(nc):
        s = 0.0
        for i in range(nr):
            s += float(a_arr[i, j])
        row_sums[0, j] = s
    return col_sums, row_sums


def _sum_all_matlab_like(a_arr: np.ndarray) -> float:
    """``sum(a,'all')`` in linear index order ``a(:)`` (column-major)."""
    av = np.asarray(a_arr, dtype=np.float64).reshape(-1, order="F")
    s = 0.0
    for x in av:
        s += float(x)
    return float(s)


def _sum_axis1_matlab_like(a_arr: np.ndarray) -> np.ndarray:
    """``sum(A,2)`` for compatibility with outcome-cost term (column vector)."""
    a_arr = np.asarray(a_arr, dtype=np.float64)
    nr, nc = int(a_arr.shape[0]), int(a_arr.shape[1])
    out = np.zeros((nr, 1), dtype=np.float64)
    for i in range(nr):
        s = 0.0
        for j in range(nc):
            s += float(a_arr[i, j])
        out[i, 0] = s
    return out


def _sum_axis0_matlab_like(a_arr: np.ndarray) -> np.ndarray:
    """``sum(A,1)`` as row vector for state-cost term."""
    a_arr = np.asarray(a_arr, dtype=np.float64)
    nr, nc = int(a_arr.shape[0]), int(a_arr.shape[1])
    out = np.zeros((1, nc), dtype=np.float64)
    for j in range(nc):
        s = 0.0
        for i in range(nr):
            s += float(a_arr[i, j])
        out[0, j] = s
    return out


def _pairwise_sum(vals: list[float]) -> float:
    """Deterministic pairwise reduction (left-to-right chunk folding)."""
    if not vals:
        return 0.0
    work = list(vals)
    while len(work) > 1:
        nxt: list[float] = []
        i = 0
        n = len(work)
        while i + 1 < n:
            nxt.append(float(work[i] + work[i + 1]))
            i += 2
        if i < n:
            nxt.append(float(work[i]))
        work = nxt
    return float(work[0])


def _spm_H(a: np.ndarray) -> float:
    """Differential entropy of a Dirichlet distribution (MATLAB local `spm_H`).

    MATLAB ``spm_H`` applies ``sum`` to vectors in linear-index order (column-major
    storage). Flatten ``a`` with Fortran order before accumulating so marginal/joint
    entropy paths match MATLAB ``spm_dir_MI`` cancellation behavior on tiny MI.
    """
    a_arr = np.asarray(a, dtype=np.float64)
    av = a_arr.reshape(-1, order="F")
    if _env_flag("RGMS_DIR_MI_EXPERIMENT_SHAPE_SUM") and a_arr.ndim == 2 and (
        int(a_arr.shape[0]) == 1 or int(a_arr.shape[1]) == 1
    ):
        # Principled candidate: mirror MATLAB default ``sum`` dimension
        # (first non-singleton) for vector-shaped inputs before scalarization.
        axis = 0 if int(a_arr.shape[0]) > 1 else 1
        a0 = float(np.asarray(np.sum(a_arr, axis=axis), dtype=np.float64).reshape(-1)[0])
        prod = np.asarray(a_arr * psi(a_arr + 1.0), dtype=np.float64)
        s = float(np.asarray(np.sum(prod, axis=axis), dtype=np.float64).reshape(-1)[0])
    else:
        a0 = 0.0
        for x in av:
            a0 += float(x)
        s = 0.0
        for i in range(av.size):
            s += float(av[i]) * float(psi(float(av[i]) + 1.0))
    if _env_flag("RGMS_DIR_MI_EXPERIMENT_FSUM"):
        a0 = math.fsum(float(x) for x in av.tolist())
        s = math.fsum(float(x) * float(psi(float(x) + 1.0)) for x in av.tolist())
    elif _env_flag("RGMS_DIR_MI_EXPERIMENT_PAIRWISE"):
        vals = [float(x) for x in av.tolist()]
        a0 = _pairwise_sum(vals)
        s = _pairwise_sum([v * float(psi(v + 1.0)) for v in vals])
    elif _env_flag("RGMS_DIR_MI_EXPERIMENT_LDACC"):
        # Candidate D: accumulate a0 and inner term in extended precision; psi stays float64.
        av_ld = np.asarray(av, dtype=np.longdouble).reshape(-1, order="F")
        a0_ld = np.sum(av_ld, dtype=np.longdouble)
        inner_ld = np.longdouble(0.0)
        for i in range(av_ld.size):
            xv = float(av_ld[i])
            inner_ld += av_ld[i] * np.longdouble(psi(xv + 1.0))
        a0 = float(a0_ld)
        s = float(inner_ld)
    elif _env_flag("RGMS_DIR_MI_EXPERIMENT_DOT"):
        # Candidate E: sequential a0 with a single stable inner product primitive.
        av64 = np.asarray(av, dtype=np.float64).reshape(-1, order="F")
        a0 = 0.0
        for x in av64:
            a0 += float(x)
        pv = np.asarray(psi(av64 + 1.0), dtype=np.float64)
        s = float(np.dot(av64, pv))
    if a0 == 0.0:
        raise ValueError("spm_H: sum(a) is zero")
    psi_a0 = float(psi(a0 + 1.0))
    frac = float(s / a0)
    # Default: ``(psi(a0+1)*a0 - inner_sum) / a0`` matches MATLAB ``psi(a0+1) -
    # sum(a.*psi(a+1))/a0`` in real arithmetic; on float64 it aligns better with
    # MATLAB's rounded ``spm_H`` on captured ``spm_faster_structure_learning`` link
    # workloads than ``psi_a0 - frac`` (see logs/log_0.md, ALT_ORDER replay batch).
    if _env_flag("RGMS_DIR_MI_LEGACY_SPM_H_EVAL"):
        out = float(psi_a0 - frac)
    else:
        out = float((psi_a0 * a0 - s) / a0)
    if _trace_enabled():
        # Trace-only diagnostics: compare default float path with alternate
        # accumulation/precision estimates without affecting returned behavior.
        a0_fsum = math.fsum(float(x) for x in av.tolist())
        inner_terms = [float(av[i]) * float(psi(float(av[i]) + 1.0)) for i in range(av.size)]
        s_fsum = math.fsum(inner_terms)
        frac_fsum = float(s_fsum / a0_fsum) if a0_fsum != 0.0 else float("nan")
        out_fsum = float(psi_a0 - frac_fsum) if a0_fsum != 0.0 else float("nan")
        try:
            av_ld = np.asarray(av, dtype=np.longdouble)
            a0_ld = np.sum(av_ld, dtype=np.longdouble)
            psi_ld = np.longdouble(psi(float(a0_ld + np.longdouble(1.0))))
            inner_ld = np.sum(
                av_ld
                * np.asarray(psi((av_ld + np.longdouble(1.0)).astype(np.float64)), dtype=np.longdouble),
                dtype=np.longdouble,
            )
            out_ld = psi_ld - (inner_ld / a0_ld)
            out_ld_s = f"{float(out_ld):.17g}"
        except Exception:
            out_ld_s = "nan"
    else:
        out_fsum = float("nan")
        out_ld_s = "nan"
    _trace(
        f"spm_H n={av.size} a0={a0:.17g} psi(a0+1)={psi_a0:.17g} "
        f"inner={s:.17g} inner/a0={frac:.17g} out={out:.17g} "
        f"out_fsum={out_fsum:.17g} out_longdouble={out_ld_s}"
    )
    return out


def spm_dir_MI(
    a: ArrayLike,
    c: Any = _MISSING,
    h: Any = _MISSING,
) -> float:
    """
    FORMAT E = spm_dir_MI(a)
    FORMAT E = spm_dir_MI(a, c)
    FORMAT E = spm_dir_MI(a, c, h)

    Use ``spm_dir_MI(a, [], h)`` to supply ``h`` with an empty outcome preference
    vector (matches MATLAB ``spm_dir_MI(a, [], h)`` with ``nargin > 1``).
    """
    if _iscell_arg(a):
        total = 0.0
        ng = _numel_cell(a)  # type: ignore[arg-type]
        for g in range(ng):
            ag = _cell_get(a, g)  # type: ignore[arg-type]
            if h is not _MISSING:
                cg = _cell_get(c, g)  # type: ignore[arg-type,union-attr]
                hg = _cell_get(h, g)  # type: ignore[arg-type,union-attr]
                total += spm_dir_MI(ag, cg, hg)
            elif c is not _MISSING:
                cg = _cell_get(c, g)  # type: ignore[arg-type,union-attr]
                total += spm_dir_MI(ag, cg)
            else:
                total += spm_dir_MI(ag)
        return float(total)

    a_arr = np.asarray(a, dtype=np.float64)
    if a_arr.ndim != 2:
        n0 = int(a_arr.shape[0])
        a_arr = np.reshape(a_arr, (n0, -1), order="F")
    # Linked ``a`` matrices in ``spm_faster_structure_learning`` can be
    # non-contiguous views; force a standalone Fortran-order float64 copy so
    # marginal / joint ``spm_H`` paths see stable element addressing (matches
    # fresh numpy arrays from MATLAB Engine pulls in oracle tests).
    a_arr = np.asfortranarray(np.array(a_arr, dtype=np.float64, copy=True))

    # Match MATLAB ``sum(a,2)`` / ``sum(a,1)`` sequential accumulation (not
    # ``np.sum`` pairwise reduction) before ``spm_H`` — feeds ULP-sensitive MI.
    col_sums, row_sums = _marginals_sum_matlab_like(a_arr)
    flat = np.reshape(a_arr, (-1, 1), order="F")

    h_col = _spm_H(col_sums)
    h_row = _spm_H(row_sums)
    h_flat = _spm_H(flat)
    if _stats_enabled() and c is _MISSING and h is _MISSING:
        _EXPERIMENT_STATS["one_arg_calls"] += 1
    if (
        _env_flag("RGMS_DIR_MI_EXPERIMENT_ROW_ULP")
        and c is _MISSING
        and h is _MISSING
        and h_col == 0.0
        and h_row == h_flat
    ):
        h_row = float(np.nextafter(np.float64(h_row), np.float64(np.inf)))
        if _stats_enabled():
            _EXPERIMENT_STATS["row_ulp_triggered"] += 1
        _trace(f"row-ulp experiment applied h_row={h_row:.17g}")

    e_val = h_col + h_row - h_flat
    _trace(
        "shape="
        f"{a_arr.shape} h_col={h_col:.17g} h_row={h_row:.17g} "
        f"h_flat={h_flat:.17g} e_base={e_val:.17g}"
    )

    big_a: Optional[np.ndarray] = None
    if c is not _MISSING or h is not _MISSING:
        denom = _sum_all_matlab_like(a_arr)
        if denom == 0.0:
            raise ValueError("spm_dir_MI: sum(a,'all') is zero")
        big_a = a_arr / denom

    if c is not _MISSING:
        c_arr = as_matlab_array(np.asarray(c, dtype=np.float64))
        c_col = np.reshape(c_arr, (-1, 1), order="F")
        if big_a is None:
            raise RuntimeError("internal: big_a unset")
        if c_col.size > 0:
            c_sum = float(np.sum(c_col))
            if c_sum != 0.0:
                c_col = c_col / c_sum
            cap_c = spm_log(c_col)
            s2 = _sum_axis1_matlab_like(big_a)
            e_val = e_val + float(np.asarray(cap_c.T @ s2, dtype=np.float64).reshape(-1)[0])
            _trace(f"c-term added e_now={e_val:.17g}")

    if h is not _MISSING:
        if big_a is None:
            raise ValueError(
                "spm_dir_MI: third argument h requires second argument c to be "
                "passed (use [] for empty c, matching MATLAB nargin > 1)."
            )
        h_wrapped: Any = h
        h_cat = spm_cat(h_wrapped)
        h_mat = np.asarray(h_cat.todense() if hasattr(h_cat, "todense") else h_cat, dtype=np.float64)
        h_col = np.reshape(h_mat, (-1, 1), order="F")
        if h_col.size > 0:
            h_sum = float(np.sum(h_col))
            if h_sum != 0.0:
                h_col = h_col / h_sum
            cap_h = spm_log(h_col)
            s1 = _sum_axis0_matlab_like(big_a)
            e_val = e_val + float(np.asarray(s1 @ cap_h, dtype=np.float64).reshape(-1)[0])
            _trace(f"h-term added e_now={e_val:.17g}")

    _trace(f"return e={e_val:.17g}")
    return float(e_val)
