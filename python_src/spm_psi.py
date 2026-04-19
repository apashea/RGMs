import numpy as np
from scipy.special import psi

from matlab_compat import as_matlab_array


def spm_psi(a):
    a = as_matlab_array(a)

    A = np.subtract(psi(a), psi(np.sum(a, axis=0)))
    A = np.maximum(A, -32.0)

    return A
