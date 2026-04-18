import numpy as np

from matlab_compat import as_matlab_array


def spm_softmax(x, k=None):
    x = as_matlab_array(x)

    if k is not None:
        x = k * x
    if x.ndim == 0 or np.shape(x)[0] < 2:
        y = np.ones(np.shape(x))
        return y

    x = np.exp(np.subtract(x, np.max(x, axis=0)))
    y = np.divide(x, np.sum(x, axis=0))

    return y
