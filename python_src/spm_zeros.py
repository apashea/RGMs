import numpy as np

from python_src.spm_length import spm_length
from python_src.spm_unvec import spm_unvec


def spm_zeros(X):
    # create zeros structure
    X = spm_unvec(np.zeros((spm_length(X), 1)), X)

    return X
