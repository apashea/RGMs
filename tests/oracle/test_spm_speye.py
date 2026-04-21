"""Oracle tests: spm_speye.m vs python_src.spm_speye."""

import numpy as np
from scipy import sparse

from python_src.spm_speye import spm_speye
from tests.helpers.compare import assert_matlab_match


def _matlab_speye_full(eng, *args):
    """Dense oracle: MATLAB Engine cannot return sparse; use full(spm_speye(...))."""
    argstr = ",".join(str(float(a)) for a in args)
    eng.eval("clear xs_dense__;", nargout=0)
    eng.eval("xs_dense__ = full(spm_speye(" + argstr + "));", nargout=0)
    return np.asarray(eng.eval("xs_dense__"), dtype=float)


def _assert_sparse_oracle(eng, args_tuple, py_args):
    m = _matlab_speye_full(eng, *args_tuple)
    d_py = spm_speye(*py_args)
    assert sparse.issparse(d_py)
    assert_matlab_match(m, d_py.toarray())


def test_spm_speye_one_arg_identity_oracle(eng):
    _assert_sparse_oracle(eng, (5.0,), (5,))


def test_spm_speye_two_args_rectangular_main_diag_oracle(eng):
    _assert_sparse_oracle(eng, (5.0, 4.0), (5, 4))


def test_spm_speye_superdiagonal_oracle(eng):
    _assert_sparse_oracle(eng, (5.0, 4.0, 1.0), (5, 4, 1))


def test_spm_speye_subdiagonal_oracle(eng):
    _assert_sparse_oracle(eng, (5.0, 4.0, -1.0), (5, 4, -1))


def test_spm_speye_wrap_c1_negative_k_oracle(eng):
    _assert_sparse_oracle(eng, (6.0, 6.0, -2.0, 1.0), (6, 6, -2, 1))


def test_spm_speye_wrap_c1_positive_k_oracle(eng):
    _assert_sparse_oracle(eng, (6.0, 6.0, 2.0, 1.0), (6, 6, 2, 1))


def test_spm_speye_pong_paddle_cases_oracle(eng):
    # Nc=9, u=1..3 from spm_MDP_pong: spm_speye(Nc,Nc,u-2,2)
    nc = 9.0
    for u in (1.0, 2.0, 3.0):
        k = u - 2.0
        _assert_sparse_oracle(eng, (nc, nc, k, 2.0), (9, 9, int(k), 2))


def test_spm_speye_square_power_oracle(eng):
    _assert_sparse_oracle(eng, (4.0, 4.0, 0.0, 0.0, 2.0), (4, 4, 0, 0, 2))


def test_spm_speye_mdp_pong_small_speye_oracle(eng):
    # spm_MDP_pong: full(spm_speye(5,3)) with default k,c,o
    _assert_sparse_oracle(eng, (5.0, 3.0), (5, 3))
