import numpy as np

from matlab_compat import as_matlab_array, full
from python_src.spm_cat import spm_cat
from python_src.spm_cov2corr import spm_cov2corr
from python_src.spm_dir_norm import spm_dir_norm


def spm_information_distance(a):
    # normalise dirichlet counts
    a = spm_dir_norm(a)

    # correlation distance : likelihood mapping
    Ng = _size(a, 1)
    C = spm_cat(a)
    C = spm_cov2corr(C.T @ C)
    D = 2 * np.sqrt(2) * Ng * (1 - full(C))

    return D, C


def _size(a, dim):
    if _iscell(a):
        siz = _cell_size(a)
    else:
        siz = np.shape(as_matlab_array(a))
    if dim <= len(siz):
        return siz[dim - 1]
    return 1


def _iscell(a):
    if isinstance(a, np.ndarray):
        return a.dtype == object
    return isinstance(a, (list, tuple))


def _cell_size(a):
    if isinstance(a, np.ndarray):
        if a.ndim == 0:
            return (1, 1)
        if a.ndim == 1:
            return (1, a.shape[0])
        return a.shape
    if len(a) > 0 and all(isinstance(row, (list, tuple)) for row in a):
        return (len(a), len(a[0]))
    return (1, len(a))
