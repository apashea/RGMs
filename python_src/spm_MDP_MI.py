import os
import math

import numpy as np

from matlab_compat import as_matlab_array, matlab_scalar
from python_src.spm_cat import spm_cat
from python_src.spm_log import spm_log


def spm_MDP_MI(a, c=None, h=None):
    """Expected information gain (mutual information); Pass 1 translation of ``spm_MDP_MI.m``.

    **Warnings vs MATLAB:** NumPy may emit ``RuntimeWarning`` for ``log(0)``, ``log(NaN)``, or
    ``0/0`` in intermediate arrays **before** ``spm_log`` applies ``np.fmax(np.log(...), -32)``
    (MATLAB ``spm_log.m`` applies ``max(log(...), -32)`` with ``log`` evaluated inside ``max``).
    Those diagnostics do not by themselves imply a different formula from MATLAB: IEEE values
    are clamped afterward like MATLAB's two-argument ``max`` with ``-32``. MATLAB's Command
    Window is usually quiet for the same float events. The non-cell tensor path uses
    ``np.errstate(divide='ignore', invalid='ignore')`` so only those expected NumPy float
    diagnostics are suppressed here (not elsewhere in the codebase).
    """
    # deal cells of (multimodal) tensors (omitting gradients)
    if _iscell(a):
        E = 0
        a = _cell_list(a)
        for g in range(len(a)):
            if h is not None:
                e = spm_MDP_MI(a[g], _cell_list(c)[g], h)
            elif c is not None:
                e = spm_MDP_MI(a[g], _cell_list(c)[g])
            else:
                e = spm_MDP_MI(a[g])
            E = E + (e[0] if isinstance(e, tuple) else e)
        return E

    # deal with tensors (expected log/0/0 warnings: see docstring; scoped errstate)
    with np.errstate(divide="ignore", invalid="ignore"):
        a = _matrix_view(a)

        # expected information gain (and negative cost)
        s = np.sum(a)
        A = a / s
        E = _spm_MI(A)

        # expected (negative) cost : outcomes
        if c is not None:
            if _numel(c):
                c = _column(c) / np.sum(c)
                C = spm_log(c)
                E = E + C.T @ _sum_dim(A, 2)
            else:
                C = 0

        # expected (negative) cost : latent states
        if h is not None:
            h = _spm_cat_colon(h)
            if _numel(h):
                h = _column(h) / np.sum(h)
                H = spm_log(h)
                E = E + _sum_dim(A, 1) @ H
            else:
                H = 0

        # dEdA
        dEdA = spm_log(A / (_sum_dim(A, 2) @ _sum_dim(A, 1))) - 1

        # expected (negative) cost
        if c is not None:
            if np.isscalar(C):
                dEdA = dEdA + (C - C * _sum_dim(A, 2))
            else:
                dEdA = dEdA + (C - C.T @ _sum_dim(A, 2))
        if h is not None:
            if np.isscalar(H):
                dEdA = dEdA + (H - _sum_dim(A, 1) * H)
            else:
                dEdA = dEdA + (H.T - _sum_dim(A, 1) @ H)

        # dEda = dEdA.*dAda, dAda = (1/s - a/(s^2))
        dEda = dEdA * (1 - A) / s

        return matlab_scalar(E), dEda, dEdA


def _spm_MI(A):
    # expected information gain of joint distribution
    A = as_matlab_array(A)
    mode = str(os.getenv("RGMS_MDP_MI_EXPERIMENT_TERM_ORDER", "")).strip().lower()
    sub_assoc = str(os.getenv("RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC", "")).strip().lower()
    log_sites_mode = str(os.getenv("RGMS_MDP_MI_EXPERIMENT_LOG_SITES", "")).strip().lower()
    reduction_mode = str(os.getenv("RGMS_MDP_MI_EXPERIMENT_REDUCTION", "")).strip().lower()

    def _spm_log_site(x, site: str):
        """Diagnostics-only per-term kernel toggle for Bottleneck #1 sweeps."""
        if log_sites_mode in ("", "default", "none", "off", "0", "false", "no"):
            return spm_log(x)
        if log_sites_mode == "all_log2_ln2":
            return np.fmax(np.log2(x) * np.log(2.0), -32.0)
        enabled = {part.strip() for part in log_sites_mode.split(",") if part.strip()}
        if enabled.issubset({"t1", "t2", "t3"}):
            if site in enabled:
                return np.fmax(np.log2(x) * np.log(2.0), -32.0)
            return spm_log(x)
        raise ValueError(
            "unknown RGMS_MDP_MI_EXPERIMENT_LOG_SITES mode: "
            f"{log_sites_mode!r}; expected default/none, all_log2_ln2, or comma list of t1,t2,t3"
        )

    def _combine_three_scalars(t_a: np.ndarray, t_b: np.ndarray, t_c: np.ndarray) -> np.float64:
        """Float64 scalar combination for Bottleneck #1 experiment sweeps only."""
        x = np.float64(matlab_scalar(t_a))
        y = np.float64(matlab_scalar(t_b))
        z = np.float64(matlab_scalar(t_c))
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            # Matches MATLAB grouping: ((joint - col_marg) - row_marg) as one expression.
            return np.float64(x - y - z)
        if sub_assoc in ("t1_minus_sum23", "j_minus_cr", "joint_minus_sum"):
            return np.float64(x - (y + z))
        if sub_assoc in ("t1_minus_t3_minus_t2", "j_minus_r_minus_c", "joint_row_col"):
            return np.float64(np.float64(x - z) - y)
        raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC mode: {sub_assoc!r}")

    def _kahan_dot(a_vec: np.ndarray, b_vec: np.ndarray) -> float:
        """Compensated summation of elementwise products (diagnostics-only)."""
        s = np.float64(0.0)
        c = np.float64(0.0)
        for i in range(a_vec.size):
            y = np.float64(a_vec[i] * b_vec[i]) - c
            t = s + y
            c = np.float64((t - s) - y)
            s = np.float64(t)
        return float(s)

    def _fsum_dot(a_vec: np.ndarray, b_vec: np.ndarray) -> float:
        """High-precision scalar reduction via math.fsum (diagnostics-only)."""
        return float(math.fsum(float(a_vec[i] * b_vec[i]) for i in range(a_vec.size)))

    def _reduce_prod(a_vec: np.ndarray, b_vec: np.ndarray, term: str) -> float:
        """Diagnostics-only reduction selector for Bottleneck #1 sweeps."""
        a_vec = np.asarray(a_vec, dtype=np.float64).ravel(order="F")
        b_vec = np.asarray(b_vec, dtype=np.float64).ravel(order="F")
        if reduction_mode in ("", "default", "none", "off", "0", "false", "no", "npdot"):
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("kahan_t1", "kahan_joint"):
            if term == "t1":
                return _kahan_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("kahan_t2", "kahan_col"):
            if term == "t2":
                return _kahan_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("kahan_t3", "kahan_row"):
            if term == "t3":
                return _kahan_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("kahan_t1_t2", "kahan_joint_col"):
            if term in ("t1", "t2"):
                return _kahan_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("kahan_all", "kahan"):
            return _kahan_dot(a_vec, b_vec)
        if reduction_mode in ("fsum_t1", "fsum_joint"):
            if term == "t1":
                return _fsum_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("fsum_t2", "fsum_col"):
            if term == "t2":
                return _fsum_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("fsum_t3", "fsum_row"):
            if term == "t3":
                return _fsum_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("fsum_t1_t2", "fsum_joint_col"):
            if term in ("t1", "t2"):
                return _fsum_dot(a_vec, b_vec)
            return float(np.dot(a_vec, b_vec))
        if reduction_mode in ("fsum_all", "fsum"):
            return _fsum_dot(a_vec, b_vec)
        raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_REDUCTION mode: {reduction_mode!r}")

    if mode in ("", "default", "matmul", "none", "off", "0", "false", "no"):
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            A_col = _column(A)
            I = (
                A_col.T @ _spm_log_site(A_col, "t1")
                - _sum_dim(A, 1) @ _spm_log_site(_sum_dim(A, 1).T, "t2")
                - _sum_dim(A, 2).T @ _spm_log_site(_sum_dim(A, 2), "t3")
            )
            return matlab_scalar(I)
        A_col = _column(A)
        t1 = A_col.T @ _spm_log_site(A_col, "t1")
        t2 = _sum_dim(A, 1) @ _spm_log_site(_sum_dim(A, 1).T, "t2")
        t3 = _sum_dim(A, 2).T @ _spm_log_site(_sum_dim(A, 2), "t3")
        I = _combine_three_scalars(t1, t2, t3)
        return matlab_scalar(I)

    cs = np.asarray(_sum_dim(A, 1), dtype=np.float64).ravel(order="F")
    rs = np.asarray(_sum_dim(A, 2), dtype=np.float64).ravel(order="F")
    flat = np.asarray(A, dtype=np.float64).ravel(order="F")
    if mode in ("scalar_fwd", "fwd"):
        t_joint = _reduce_prod(flat, _spm_log_site(flat, "t1"), "t1")
        t_col = _reduce_prod(cs, _spm_log_site(cs, "t2"), "t2")
        t_row = _reduce_prod(rs, _spm_log_site(rs, "t3"), "t3")
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            return matlab_scalar(t_joint - t_col - t_row)
        if sub_assoc in ("t1_minus_sum23", "j_minus_cr", "joint_minus_sum"):
            return matlab_scalar(np.float64(t_joint - (t_col + t_row)))
        if sub_assoc in ("t1_minus_t3_minus_t2", "j_minus_r_minus_c", "joint_row_col"):
            return matlab_scalar(np.float64(np.float64(t_joint - t_row) - t_col))
        raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC mode: {sub_assoc!r}")
    if mode in ("scalar_rev", "rev", "reverse"):
        fr = flat[::-1]
        csr = cs[::-1]
        rsr = rs[::-1]
        t_joint = _reduce_prod(fr, _spm_log_site(fr, "t1"), "t1")
        t_col = _reduce_prod(csr, _spm_log_site(csr, "t2"), "t2")
        t_row = _reduce_prod(rsr, _spm_log_site(rsr, "t3"), "t3")
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            return matlab_scalar(t_joint - t_col - t_row)
        if sub_assoc in ("t1_minus_sum23", "j_minus_cr", "joint_minus_sum"):
            return matlab_scalar(np.float64(t_joint - (t_col + t_row)))
        if sub_assoc in ("t1_minus_t3_minus_t2", "j_minus_r_minus_c", "joint_row_col"):
            return matlab_scalar(np.float64(np.float64(t_joint - t_row) - t_col))
        raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC mode: {sub_assoc!r}")
    if mode in ("dot_fwd", "ddot_fwd"):
        t_joint = _reduce_prod(flat, _spm_log_site(flat, "t1"), "t1")
        t_col = _reduce_prod(cs, _spm_log_site(cs, "t2"), "t2")
        t_row = _reduce_prod(rs, _spm_log_site(rs, "t3"), "t3")
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            return matlab_scalar(t_joint - t_col - t_row)
        if sub_assoc in ("t1_minus_sum23", "j_minus_cr", "joint_minus_sum"):
            return matlab_scalar(np.float64(t_joint - (t_col + t_row)))
        if sub_assoc in ("t1_minus_t3_minus_t2", "j_minus_r_minus_c", "joint_row_col"):
            return matlab_scalar(np.float64(np.float64(t_joint - t_row) - t_col))
        raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC mode: {sub_assoc!r}")
    if mode in ("dot_rev", "ddot_rev"):
        fr = flat[::-1]
        csr = cs[::-1]
        rsr = rs[::-1]
        t_joint = _reduce_prod(fr, _spm_log_site(fr, "t1"), "t1")
        t_col = _reduce_prod(csr, _spm_log_site(csr, "t2"), "t2")
        t_row = _reduce_prod(rsr, _spm_log_site(rsr, "t3"), "t3")
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            return matlab_scalar(t_joint - t_col - t_row)
        if sub_assoc in ("t1_minus_sum23", "j_minus_cr", "joint_minus_sum"):
            return matlab_scalar(np.float64(t_joint - (t_col + t_row)))
        if sub_assoc in ("t1_minus_t3_minus_t2", "j_minus_r_minus_c", "joint_row_col"):
            return matlab_scalar(np.float64(np.float64(t_joint - t_row) - t_col))
        raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC mode: {sub_assoc!r}")
    raise ValueError(f"unknown RGMS_MDP_MI_EXPERIMENT_TERM_ORDER mode: {mode!r}")


def _matrix_view(x):
    x = as_matlab_array(x)
    if x.ndim <= 2:
        return x
    return np.reshape(x, (x.shape[0], int(np.prod(x.shape[1:]))), order="F")


def _column(x):
    x = as_matlab_array(x)
    return np.reshape(x, (-1, 1), order="F")


def _sum_dim(x, dim):
    axis = dim - 1
    if axis >= np.ndim(x):
        return x
    return np.sum(x, axis=axis, keepdims=True)


def _numel(x):
    if x is None:
        return 0
    if _iscell(x):
        return len(_cell_list(x))
    return np.asarray(x).size


def _iscell(x):
    if isinstance(x, np.ndarray):
        return x.dtype == object
    return isinstance(x, (list, tuple))


def _cell_list(x):
    if isinstance(x, np.ndarray):
        return list(x.ravel(order="F"))
    return list(x)


def _spm_cat_colon(x):
    if _iscell(x):
        return spm_cat([[item] for item in _cell_list(x)])
    return spm_cat(_column(x))
