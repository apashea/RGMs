import numpy as np
from scipy.special import psi

from matlab_compat import as_matlab_array, matlab_scalar
from python_src.spm_betaln import spm_betaln


def spm_KL_dir(q, p):
    # KL divergence based on log beta functions
    def spm_psi(q):
        return np.subtract(psi(q), psi(_sum_default(q)))

    p = as_matlab_array(p)
    q = as_matlab_array(q)

    p = np.maximum(p, np.exp(-16))
    q = np.maximum(q, np.exp(-16))
    d = spm_betaln(p) - spm_betaln(q) + _sum_default((q - p) * spm_psi(q))
    d = np.sum(d)

    return matlab_scalar(d)


def _sum_default(X):
    X = as_matlab_array(X)
    if X.ndim == 0:
        return np.sum(X)
    for axis, size in enumerate(X.shape):
        if size != 1:
            return np.sum(X, axis=axis, keepdims=True)
    return np.sum(X, axis=0, keepdims=True)
