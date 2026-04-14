import numpy as np


def spm_log(A):
    A = np.asarray(A)

    if np.issubdtype(A.dtype, np.bool_):
        A = -32.0 * (~A)
    else:
        A = np.maximum(np.log(A), -32.0)

    return A
