import numpy as np

from matlab_compat import as_matlab_array


def spm_log(A):
    A = as_matlab_array(A)

    if np.issubdtype(A.dtype, np.bool_):
        A = -32.0 * (~A)
    else:
        A = np.maximum(np.log(A), -32.0)

    return A
