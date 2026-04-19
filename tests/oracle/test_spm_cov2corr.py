import matlab
import numpy as np
from scipy import sparse

from python_src.spm_cov2corr import spm_cov2corr
from tests.helpers.compare import assert_matlab_match


def test_spm_cov2corr_dense_oracle(eng):
    C = np.array(
        [
            [4.0, 2.0, -1.0],
            [2.0, 9.0, 3.0],
            [-1.0, 3.0, 16.0],
        ]
    )
    C_matlab = matlab.double(C.tolist())

    R_matlab = eng.spm_cov2corr(C_matlab)
    R_python = spm_cov2corr(C)

    assert not sparse.issparse(R_python)
    assert_matlab_match(R_matlab, R_python)


def test_spm_cov2corr_zero_variance_oracle(eng):
    C = np.array([[0.0, 0.0], [0.0, 4.0]])
    C_matlab = matlab.double(C.tolist())

    R_matlab = eng.spm_cov2corr(C_matlab)
    R_python = spm_cov2corr(C)

    assert not sparse.issparse(R_python)
    assert_matlab_match(R_matlab, R_python)


def test_spm_cov2corr_sparse_oracle(eng):
    eng.eval(
        "C_spm_cov2corr = sparse([4 0.5 0; 0.5 9 0; 0 0 16]);",
        nargout=0,
    )
    R_matlab_sparse = eng.eval("issparse(spm_cov2corr(C_spm_cov2corr))")
    R_matlab_full = eng.eval("full(spm_cov2corr(C_spm_cov2corr))")

    C = sparse.csr_matrix(
        [
            [4.0, 0.5, 0.0],
            [0.5, 9.0, 0.0],
            [0.0, 0.0, 16.0],
        ]
    )
    R_python = spm_cov2corr(C)

    assert sparse.issparse(R_python) == bool(R_matlab_sparse)
    assert_matlab_match(R_matlab_full, R_python.toarray())


def test_spm_cov2corr_identity_oracle(eng):
    C = np.eye(3)
    C_matlab = matlab.double(C.tolist())

    R_matlab = eng.spm_cov2corr(C_matlab)
    R_python = spm_cov2corr(C)

    assert_matlab_match(R_matlab, R_python)


def test_spm_cov2corr_singleton_oracle(eng):
    C = 4.0

    R_matlab = eng.eval("full(spm_cov2corr(4))")
    R_python = spm_cov2corr(C)

    assert_matlab_match(R_matlab, R_python)
