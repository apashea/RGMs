"""Oracle tests: spm_kron.m vs python_src.spm_kron."""

import numpy as np
from scipy import sparse

from python_src.spm_kron import spm_kron
from tests.helpers.compare import assert_matlab_match


def _matlab_kron_full(eng, matlab_stmt: str) -> np.ndarray:
    """Evaluate MATLAB statement assigning dense xs_kron__."""
    eng.eval("clear xs_kron__;", nargout=0)
    eng.eval("xs_kron__ = full(" + matlab_stmt + ");", nargout=0)
    return np.asarray(eng.eval("xs_kron__"), dtype=float)


def test_spm_kron_two_dense_matrices_oracle(eng):
    eng.eval("A_k = [1 2; 3 4]; B_k = [0 1; 1 0];", nargout=0)
    m = _matlab_kron_full(eng, "spm_kron(A_k, B_k)")
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[0.0, 1.0], [1.0, 0.0]])
    k = spm_kron(a, b)
    assert sparse.issparse(k)
    assert_matlab_match(m, k.toarray())


def test_spm_kron_two_sparse_like_oracle(eng):
    eng.eval("A_k = sparse([1 0; 0 2]); B_k = sparse([0 1; 2 3]);", nargout=0)
    m = _matlab_kron_full(eng, "spm_kron(A_k, B_k)")
    a = sparse.csr_matrix([[1.0, 0.0], [0.0, 2.0]])
    b = sparse.csr_matrix([[0.0, 1.0], [2.0, 3.0]])
    k = spm_kron(a, b)
    assert_matlab_match(m, k.toarray())


def test_spm_kron_cell_two_factors_oracle(eng):
    eng.eval("C1 = [1 2; 3 4]; C2 = [0 1; 1 0];", nargout=0)
    m = _matlab_kron_full(eng, "spm_kron({C1, C2})")
    c1 = np.array([[1.0, 2.0], [3.0, 4.0]])
    c2 = np.array([[0.0, 1.0], [1.0, 0.0]])
    k = spm_kron([c1, c2])
    assert_matlab_match(m, k.toarray())


def test_spm_kron_cell_three_factors_oracle(eng):
    eng.eval("D1 = [1 2]; D2 = [3; 4]; D3 = [1 0; 0 1];", nargout=0)
    m = _matlab_kron_full(eng, "spm_kron({D1, D2, D3})")
    d1 = np.array([[1.0, 2.0]])
    d2 = np.array([[3.0], [4.0]])
    d3 = np.array([[1.0, 0.0], [0.0, 1.0]])
    k = spm_kron([d1, d2, d3])
    assert_matlab_match(m, k.toarray())


def test_spm_kron_rectangular_oracle(eng):
    eng.eval("E1 = [1 2 3]; E2 = [4; 5];", nargout=0)
    m = _matlab_kron_full(eng, "spm_kron(E1, E2)")
    e1 = np.array([[1.0, 2.0, 3.0]])
    e2 = np.array([[4.0], [5.0]])
    k = spm_kron(e1, e2)
    assert_matlab_match(m, k.toarray())
