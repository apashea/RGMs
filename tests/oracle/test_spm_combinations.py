"""Oracle tests: spm_combinations.m vs python_src.spm_combinations."""

import numpy as np

from python_src.spm_combinations import spm_combinations
from tests.helpers.compare import assert_matlab_match


def _matlab_eval_matrix(eng, matlab_rhs: str) -> np.ndarray:
    eng.eval("clear xs_c__;", nargout=0)
    eng.eval("xs_c__ = " + matlab_rhs + ";", nargout=0)
    return np.asarray(eng.eval("xs_c__"), dtype=float)


def test_spm_combinations_numeric_vector_oracle(eng):
    m = _matlab_eval_matrix(eng, "spm_combinations([2,3,4])")
    u = spm_combinations(np.array([2, 3, 4], dtype=np.int64))
    assert_matlab_match(m, u)


def test_spm_combinations_numeric_column_oracle(eng):
    m = _matlab_eval_matrix(eng, "spm_combinations([2;3])")
    u = spm_combinations(np.array([[2], [3]], dtype=np.int64))
    assert_matlab_match(m, u)


def test_spm_combinations_numeric_list_oracle(eng):
    m = _matlab_eval_matrix(eng, "spm_combinations([2, 2])")
    u = spm_combinations([2, 2])
    assert_matlab_match(m, u)


def test_spm_combinations_cell_two_domains_oracle(eng):
    eng.eval("Nu_c = {[1 2], [10 20 30]};", nargout=0)
    m = _matlab_eval_matrix(eng, "spm_combinations(Nu_c)")
    u = spm_combinations(
        [np.array([1.0, 2.0]), np.array([10.0, 20.0, 30.0])]
    )
    assert_matlab_match(m, u)


def test_spm_combinations_single_factor_oracle(eng):
    m = _matlab_eval_matrix(eng, "spm_combinations([5])")
    u = spm_combinations([5])
    assert_matlab_match(m, u)
