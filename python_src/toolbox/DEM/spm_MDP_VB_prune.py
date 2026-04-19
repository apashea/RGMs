import numpy as np

from matlab_compat import as_matlab_array
from python_src.spm_MDP_MI import spm_MDP_MI
from python_src.spm_psi import spm_psi
from python_src.spm_softmax import spm_softmax
from python_src.spm_sum import spm_sum
from python_src.toolbox.DEM.spm_MDP_log_evidence import spm_MDP_log_evidence


def spm_MDP_VB_prune(qA, pA=None, f=0, T=0, pC=None, OPT="MI"):
    qA = as_matlab_array(qA)

    # defaults
    nd = np.shape(qA)
    if pA is None:
        pA = 0 * qA + 1
    else:
        pA = as_matlab_array(pA)
    if pC is None:
        pC = []

    # assume uniform priors if pA is a scalar
    if np.size(pA) == 1:
        pA = np.zeros(np.shape(qA)) + np.asarray(pA).reshape(-1, order="F")[0]

    f = int(np.asarray(f).reshape(-1, order="F")[0])
    s = np.prod(np.asarray(nd)[f])

    # sum Dirichlet parameters over conditionally independent factors
    if f:
        pA = spm_sum(pA, f + 1)
        qA = spm_sum(qA, f + 1)

    # unfold tensors
    qA = _matrix_view(qA)
    pA = _matrix_view(pA)

    # gradients of expected information gain (i.e., expected free energy)
    if OPT == "MI":

        # evaluate gradients of expected free energy
        E, dEdA, _ = spm_MDP_MI(pA, pC)
        rA = pA * np.exp(pA * dEdA)
        rA = rA * (_sum_default(pA) / _sum_default(rA))

    elif OPT == "SIMPLE":

        # simple pruning based on sparsity hyperprior
        rA = spm_psi(qA)
        rA = rA - _max_default(rA)
        rA = pA * (rA > -np.log(32))
        rA = rA * (_sum_default(pA) / _sum_default(rA))

    else:
        rA = pA

    # retain reduced priors and posteriors if outwith Occam's window
    F, sA, _ = spm_MDP_log_evidence(qA, pA, rA)

    if T or str(OPT).lower() == "simple":

        # apply Occam's razor
        j = np.asarray(F < -T).ravel(order="F")
        qA[:, j] = sA[:, j]
        pA[:, j] = rA[:, j]

    else:

        # Bayesian model averaging based on reduced free energy
        from python_src.spm_zeros import spm_zeros

        F = _as_row(F)
        P = spm_softmax(32 * np.vstack((F, _as_row(spm_zeros(F)))))
        qA = sA * P[0:1, :] + qA * P[1:2, :]
        pA = rA * P[0:1, :] + pA * P[1:2, :]

    # redistribute scaled parameters over contracted dimensions
    if f:
        qA = np.zeros(nd) + _matlab_implicit_expand(qA / s, nd)
        pA = np.zeros(nd) + _matlab_implicit_expand(pA / s, nd)

    else:

        # fold tensors
        qA = np.reshape(qA, nd, order="F")
        pA = np.reshape(pA, nd, order="F")

    return qA, pA


def _matrix_view(x):
    x = as_matlab_array(x)
    if x.ndim <= 2:
        return x
    return np.reshape(x, (x.shape[0], int(np.prod(x.shape[1:]))), order="F")


def _sum_default(X):
    X = as_matlab_array(X)
    if X.ndim == 0:
        return np.sum(X)
    for axis, size in enumerate(X.shape):
        if size != 1:
            return np.sum(X, axis=axis, keepdims=True)
    return np.sum(X, axis=0, keepdims=True)


def _max_default(X):
    X = as_matlab_array(X)
    if X.ndim == 0:
        return np.max(X)
    for axis, size in enumerate(X.shape):
        if size != 1:
            return np.max(X, axis=axis, keepdims=True)
    return np.max(X, axis=0, keepdims=True)


def _as_row(X):
    X = as_matlab_array(X)
    if X.ndim == 0:
        return np.reshape(X, (1, 1), order="F")
    if X.ndim == 1:
        return np.reshape(X, (1, X.shape[0]), order="F")
    return X


def _matlab_implicit_expand(X, nd):
    X = as_matlab_array(X)
    if len(nd) > X.ndim:
        X = np.reshape(X, X.shape + (1,) * (len(nd) - X.ndim), order="F")
    return X
