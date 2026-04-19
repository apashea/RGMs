import matlab
import numpy as np

from python_src.spm_psi import spm_psi
from tests.helpers.compare import assert_matlab_match


def test_spm_psi_matrix_oracle(eng):
    a = np.array([[2.0, 4.0, 8.0], [3.0, 5.0, 13.0]])
    a_matlab = matlab.double(a.tolist())

    A_matlab = eng.spm_psi(a_matlab)
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)


def test_spm_psi_row_oracle(eng):
    a = np.array([[2.0, 3.0, 4.0]])
    a_matlab = matlab.double(a.tolist())

    A_matlab = eng.spm_psi(a_matlab)
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)


def test_spm_psi_clip_oracle(eng):
    a = np.array([[0.01, 2.0], [100.0, 3.0]])
    a_matlab = matlab.double(a.tolist())

    A_matlab = eng.spm_psi(a_matlab)
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)


def test_spm_psi_raw_1d_is_row_oracle(eng):
    a = np.array([2.0, 3.0, 4.0])

    A_matlab = eng.eval("spm_psi([2 3 4])")
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)


def test_spm_psi_column_oracle(eng):
    a = np.array([[2.0], [3.0], [4.0]])
    a_matlab = matlab.double(a.tolist())

    A_matlab = eng.spm_psi(a_matlab)
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)


def test_spm_psi_scalar_oracle(eng):
    a = 2.0

    A_matlab = eng.spm_psi(a)
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)


def test_spm_psi_tensor_oracle(eng):
    a = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")

    A_matlab = eng.eval("spm_psi(reshape(1:24,[2 3 4]))")
    A_python = spm_psi(a)

    assert_matlab_match(A_matlab, A_python)
