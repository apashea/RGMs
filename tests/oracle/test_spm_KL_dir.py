import matlab
import numpy as np

from python_src.spm_KL_dir import spm_KL_dir
from tests.helpers.compare import assert_matlab_match


def test_spm_KL_dir_matrix_with_clipping_oracle(eng):
    q = np.array([[0.0, 2.0], [3.0, 4.0]])
    p = np.array([[1.0, 0.0], [0.5, 2.0]])

    d_matlab = eng.spm_KL_dir(matlab.double(q.tolist()), matlab.double(p.tolist()))
    d_python = spm_KL_dir(q, p)

    assert_matlab_match(d_matlab, d_python)


def test_spm_KL_dir_raw_1d_row_oracle(eng):
    q = np.array([2.0, 3.0, 4.0])
    p = np.array([1.0, 5.0, 2.0])

    d_matlab = eng.eval("spm_KL_dir([2 3 4], [1 5 2])")
    d_python = spm_KL_dir(q, p)

    assert_matlab_match(d_matlab, d_python)
