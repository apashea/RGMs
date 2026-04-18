import matlab
import numpy as np

from python_src.spm_betaln import spm_betaln
from tests.helpers.compare import assert_matlab_match


def test_spm_betaln_matrix_oracle(eng):
    z = np.array([[2.0, 3.0, 4.0], [5.0, 7.0, 11.0]])
    z_matlab = matlab.double(z.tolist())

    y_matlab = eng.spm_betaln(z_matlab)
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)


def test_spm_betaln_row_oracle(eng):
    z = np.array([[2.0, 3.0, 4.0]])
    z_matlab = matlab.double(z.tolist())

    y_matlab = eng.spm_betaln(z_matlab)
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)


def test_spm_betaln_clip_oracle(eng):
    z = np.array([[0.0, -1.0], [1e-20, 3.0]])
    z_matlab = matlab.double(z.tolist())

    y_matlab = eng.spm_betaln(z_matlab)
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)


def test_spm_betaln_raw_1d_is_row_oracle(eng):
    z = np.array([2.0, 3.0, 4.0])

    y_matlab = eng.eval("spm_betaln([2 3 4])")
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)


def test_spm_betaln_column_oracle(eng):
    z = np.array([[2.0], [3.0]])
    z_matlab = matlab.double(z.tolist())

    y_matlab = eng.spm_betaln(z_matlab)
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)


def test_spm_betaln_single_column_oracle(eng):
    z = np.array([[2.0], [3.0], [4.0], [5.0], [6.0]])
    z_matlab = matlab.double(z.tolist())

    y_matlab = eng.spm_betaln(z_matlab)
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)


def test_spm_betaln_tensor_oracle(eng):
    z = np.arange(1.0, 25.0).reshape((2, 3, 4), order="F")

    y_matlab = eng.eval("spm_betaln(reshape(1:24,[2 3 4]))")
    y_python = spm_betaln(z)

    assert_matlab_match(y_matlab, y_python)
