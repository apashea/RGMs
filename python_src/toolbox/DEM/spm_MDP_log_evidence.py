import numpy as np
from scipy.special import psi

from matlab_compat import as_matlab_array
from python_src.spm_betaln import spm_betaln


def spm_MDP_log_evidence(qA, pA, rA):
    qA = as_matlab_array(qA)
    pA = as_matlab_array(pA)
    rA = as_matlab_array(rA)

    # change in free energy or log model evidence
    p = 1 / 512
    rA = rA + p
    pA = pA + p
    qA = qA + p
    sA = qA + rA - pA

    # free energy and posterior
    F = spm_betaln(qA) + spm_betaln(rA) - spm_betaln(pA) - spm_betaln(sA)
    sA = np.maximum(sA - p, 0)

    # dEdA = d/drA (spm_betaln(rA) - spm_betaln(sA))
    def d_betaln(x):
        return psi(x) - psi(_sum_default(x))

    dFdA = d_betaln(rA) - d_betaln(sA + p)

    return F, sA, dFdA


def _sum_default(X):
    X = as_matlab_array(X)
    if X.ndim == 0:
        return np.sum(X)
    for axis, size in enumerate(X.shape):
        if size != 1:
            return np.sum(X, axis=axis, keepdims=True)
    return np.sum(X, axis=0, keepdims=True)
