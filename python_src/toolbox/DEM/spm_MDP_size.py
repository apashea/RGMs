import numpy as np

from matlab_compat import as_matlab_array


def spm_MDP_size(mdp):
    # checks
    if _hasfield(mdp, "a"):
        a = _getfield(mdp, "a")
    else:
        a = _getfield(mdp, "A")

    if _hasfield(mdp, "b"):
        b = _getfield(mdp, "b")
    else:
        if _hasfield(mdp, "B"):
            b = _getfield(mdp, "B")
        else:
            raise NameError("A")

    a = _cell_list(a)
    b = _cell_list(b)

    # sizes of factors and modilities
    Nf = len(b)
    Ng = len(a)
    Ns = np.zeros((1, Nf))
    Nu = np.zeros((1, Nf))
    No = np.zeros((1, Ng))

    for f in range(Nf):
        Ns[0, f] = _size(b[f], 1)
        Nu[0, f] = _size(b[f], 3)

    for g in range(Ng):
        No[0, g] = _size(a[g], 1)

    return Nf, Ns, Nu, Ng, No


def _hasfield(mdp, field):
    if isinstance(mdp, dict):
        return field in mdp
    return hasattr(mdp, field)


def _getfield(mdp, field):
    if isinstance(mdp, dict):
        return mdp[field]
    return getattr(mdp, field)


def _cell_list(x):
    if isinstance(x, np.ndarray) and x.dtype == object:
        return list(x.ravel(order="F"))
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _size(x, dim):
    x = as_matlab_array(x)
    if dim <= x.ndim:
        return x.shape[dim - 1]
    return 1
