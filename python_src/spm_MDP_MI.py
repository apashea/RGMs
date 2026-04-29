import os

import numpy as np

from matlab_compat import as_matlab_array, matlab_scalar
from python_src.spm_cat import spm_cat
from python_src.spm_log import spm_log


def spm_MDP_MI(a, c=None, h=None):
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

    # deal with tensors
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

    if mode in ("", "default", "matmul", "none", "off", "0", "false", "no"):
        if sub_assoc in ("", "default", "chain", "matlab", "none", "off", "0", "false", "no"):
            A_col = _column(A)
            I = (
                A_col.T @ spm_log(A_col)
                - _sum_dim(A, 1) @ spm_log(_sum_dim(A, 1).T)
                - _sum_dim(A, 2).T @ spm_log(_sum_dim(A, 2))
            )
            return matlab_scalar(I)
        A_col = _column(A)
        t1 = A_col.T @ spm_log(A_col)
        t2 = _sum_dim(A, 1) @ spm_log(_sum_dim(A, 1).T)
        t3 = _sum_dim(A, 2).T @ spm_log(_sum_dim(A, 2))
        I = _combine_three_scalars(t1, t2, t3)
        return matlab_scalar(I)

    cs = np.asarray(_sum_dim(A, 1), dtype=np.float64).ravel(order="F")
    rs = np.asarray(_sum_dim(A, 2), dtype=np.float64).ravel(order="F")
    flat = np.asarray(A, dtype=np.float64).ravel(order="F")
    if mode in ("scalar_fwd", "fwd"):
        t_joint = float(np.sum(flat * np.asarray(spm_log(flat), dtype=np.float64)))
        t_col = float(np.sum(cs * np.asarray(spm_log(cs), dtype=np.float64)))
        t_row = float(np.sum(rs * np.asarray(spm_log(rs), dtype=np.float64)))
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
        t_joint = float(np.sum(fr * np.asarray(spm_log(fr), dtype=np.float64)))
        t_col = float(np.sum(csr * np.asarray(spm_log(csr), dtype=np.float64)))
        t_row = float(np.sum(rsr * np.asarray(spm_log(rsr), dtype=np.float64)))
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
