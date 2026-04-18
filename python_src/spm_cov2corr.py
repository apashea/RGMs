import numpy as np
from scipy import sparse

from matlab_compat import as_matlab_array, matlab_scalar


def spm_cov2corr(C):
    if sparse.issparse(C):
        n = max(C.shape)
        d = C.diagonal()
    else:
        C = as_matlab_array(C)
        n = max(C.shape)
        d = np.diag(C)

    D = sparse.csr_matrix(
        (
            np.sqrt(1.0 / (d + np.finfo(float).eps)),
            (np.arange(n), np.arange(n)),
        ),
        shape=(n, n),
    )
    C = np.real(D @ C)
    C = np.real(C @ D)

    return matlab_scalar(C)
