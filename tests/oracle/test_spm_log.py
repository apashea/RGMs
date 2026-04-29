import pickle
from pathlib import Path

import matlab
import numpy as np
import pytest

from python_src.spm_log import spm_log
from tests.helpers.compare import assert_matlab_match

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MI_WORKLOAD_PKL = (
    _REPO_ROOT
    / "tests"
    / "oracle"
    / "toolbox"
    / "DEM"
    / "_checkpoint_data"
    / "fsl_rgm_mi_workload_full_native_mi.pkl"
)

# Ceiling from MATLAB Engine vs Python on MI workload multiset (see notes).
_MI_WORKLOAD_ULP_CEILING = 3


@pytest.fixture(autouse=True)
def _clear_spm_log_experiment_kernel(monkeypatch):
    """Oracle tests target MATLAB-faithful `spm_log`; unset diagnostic kernel."""
    monkeypatch.delenv("RGMS_SPM_LOG_EXPERIMENT_KERNEL", raising=False)


def _float_ulp_distance(a: float, b: float) -> int:
    """Ordered ULP gap between two float64 values (handles signed zero)."""

    def _ordered_int_bits(x: float) -> int:
        u = int(np.frombuffer(np.float64(x).tobytes(), dtype=np.uint64)[0])
        return u ^ (((u >> 63) & 1) * 0x7FFFFFFFFFFFFFFF)

    return abs(_ordered_int_bits(a) - _ordered_int_bits(b))


def _matlab_spm_log_column(eng, v_col: np.ndarray) -> np.ndarray:
    """Column vector (n,1) float64 in / out."""
    v_col = np.asarray(v_col, dtype=np.float64).reshape(-1, 1)
    nr, nc = v_col.shape
    eng.workspace["rgml_a"] = matlab.double(v_col.tolist(), size=(nr, nc))
    eng.eval("rgml_y = spm_log(rgml_a);", nargout=0)
    return np.asarray(eng.eval("rgml_y"), dtype=np.float64).reshape(-1, order="F")


def test_spm_log_numeric_oracle(eng):
    A = np.array([[0.5, 0.0], [1.0, 1e-20]])
    A_matlab = matlab.double(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_logical_oracle(eng):
    A = np.array([[True, False], [False, True]])
    A_matlab = matlab.logical(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_scalar_oracle(eng):
    A = 0.5

    A_matlab = eng.spm_log(A)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_nan_scalar_matches_matlab_max_semantics_oracle(eng):
    """MATLAB `max(log(NaN), -32)` yields -32 (IEEE fmax-like), not NaN."""
    val_m = float(np.asarray(eng.eval("spm_log(NaN)"), dtype=np.float64).reshape(-1)[0])
    val_p = float(
        np.asarray(spm_log(np.array([[np.nan]], dtype=np.float64)), dtype=np.float64).reshape(
            -1
        )[0]
    )
    assert val_m == val_p == -32.0


def test_spm_log_all_zeros_oracle(eng):
    A = np.zeros((2, 3))
    A_matlab = matlab.double(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_column_oracle(eng):
    A = np.array([[0.5], [1.0], [2.0]])
    A_matlab = matlab.double(A.tolist())

    A_matlab = eng.spm_log(A_matlab)
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_raw_1d_is_row_oracle(eng):
    A = np.array([0.5, 1.0, 2.0])

    A_matlab = eng.eval("spm_log([0.5 1 2])")
    A_python = spm_log(A)

    assert_matlab_match(A_matlab, A_python)


def test_spm_log_clamp_and_reference_values_max_ulp_oracle(eng):
    """MATLAB `max(log(A),-32)` on values that stress the clamp and zeros."""
    em32 = np.exp(np.float64(-32.0))
    vals = np.array(
        [
            0.0,
            np.nextafter(np.float64(0.0), np.float64(1.0)),
            0.5,
            1.0,
            2.0,
            em32,
            np.nextafter(em32, np.float64(0.0)),
            np.nextafter(em32, np.float64(1.0)),
            1e-300,
        ],
        dtype=np.float64,
    )
    v_col = vals.reshape(-1, 1)
    y_m = _matlab_spm_log_column(eng, v_col)
    y_p = np.asarray(spm_log(v_col), dtype=np.float64).ravel(order="F")
    ulps = [_float_ulp_distance(float(y_p[i]), float(y_m[i])) for i in range(len(vals))]
    assert max(ulps) <= _MI_WORKLOAD_ULP_CEILING, f"ULP per row: {ulps}"


def test_spm_log_mi_workload_reference_max_ulp_oracle(eng):
    """All float inputs that appear in captured Bottleneck #1 MI paths vs MATLAB."""
    if not _MI_WORKLOAD_PKL.is_file():
        pytest.skip(f"MI workload checkpoint missing: {_MI_WORKLOAD_PKL}")

    with _MI_WORKLOAD_PKL.open("rb") as f:
        payload = pickle.load(f)
    pairs = [r for r in payload["records"] if r.get("kind") != "stream_summary"]

    parts: list[np.ndarray] = []
    for rec in pairs:
        p = np.asarray(rec["p_mat"], dtype=np.float64)
        s = float(np.sum(p))
        if s == 0.0:
            continue
        a = p / s
        parts.append(a.ravel(order="F"))
        parts.append(np.sum(a, axis=0).ravel(order="F"))
        parts.append(np.sum(a, axis=1).ravel(order="F"))

    if not parts:
        pytest.skip("no numeric rows in MI workload payload")

    u = np.unique(np.concatenate(parts))
    v_col = u.reshape(-1, 1)
    y_m = _matlab_spm_log_column(eng, v_col)
    y_p = np.asarray(spm_log(v_col), dtype=np.float64).ravel(order="F")
    assert y_m.shape == y_p.shape == (u.size,)

    max_ulp = 0
    strict_mis = 0
    for i in range(u.size):
        ul = _float_ulp_distance(float(y_p[i]), float(y_m[i]))
        max_ulp = max(max_ulp, ul)
        if y_p[i] != y_m[i]:
            strict_mis += 1

    assert max_ulp <= _MI_WORKLOAD_ULP_CEILING, (
        f"max_ulp={max_ulp} (ceiling {_MI_WORKLOAD_ULP_CEILING}), "
        f"strict_bit_mismatches={strict_mis} of {u.size}"
    )


def test_spm_log_experiment_kernel_unknown_raises():
    import os

    prev = os.environ.get("RGMS_SPM_LOG_EXPERIMENT_KERNEL")
    try:
        os.environ["RGMS_SPM_LOG_EXPERIMENT_KERNEL"] = "not_a_real_kernel"
        with pytest.raises(ValueError, match="unknown RGMS_SPM_LOG_EXPERIMENT_KERNEL"):
            spm_log(np.array([[0.5]], dtype=np.float64))
    finally:
        if prev is None:
            os.environ.pop("RGMS_SPM_LOG_EXPERIMENT_KERNEL", None)
        else:
            os.environ["RGMS_SPM_LOG_EXPERIMENT_KERNEL"] = prev
