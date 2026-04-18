import numpy as np
from scipy.special import gammaln

from matlab_compat import as_matlab_array, matlab_scalar


def spm_betaln(z):
    z = as_matlab_array(z)

    # log multivariate beta function
    z = np.maximum(z, np.exp(-32))
    y = np.sum(gammaln(z), axis=0, keepdims=True) - gammaln(
        np.sum(z, axis=0, keepdims=True)
    )

    return matlab_scalar(y)
