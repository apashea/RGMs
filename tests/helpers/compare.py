import numpy as np


def assert_matlab_match(matlab_result, python_result, rtol=1e-7, atol=1e-12):
    if isinstance(matlab_result, (list, tuple)) and isinstance(
        python_result, (list, tuple)
    ):
        if _can_compare_as_numeric(matlab_result, python_result):
            _assert_numeric_match(matlab_result, python_result, rtol, atol)
            return

        assert len(matlab_result) == len(python_result), (
            f"length mismatch: MATLAB {len(matlab_result)}, "
            f"Python {len(python_result)}"
        )
        for index, (matlab_item, python_item) in enumerate(
            zip(matlab_result, python_result)
        ):
            try:
                assert_matlab_match(matlab_item, python_item, rtol=rtol, atol=atol)
            except AssertionError as exc:
                raise AssertionError(f"mismatch at index {index}: {exc}") from exc
        return

    _assert_numeric_match(matlab_result, python_result, rtol, atol)


def _can_compare_as_numeric(matlab_result, python_result):
    try:
        np.asarray(matlab_result, dtype=float)
        np.asarray(python_result, dtype=float)
    except (TypeError, ValueError):
        return False
    return True


def _assert_numeric_match(matlab_result, python_result, rtol, atol):
    matlab_array = np.asarray(matlab_result, dtype=float)
    python_array = np.asarray(python_result, dtype=float)

    assert matlab_array.shape == python_array.shape, (
        f"shape mismatch: MATLAB {matlab_array.shape}, "
        f"Python {python_array.shape}"
    )
    np.testing.assert_allclose(
        matlab_array,
        python_array,
        rtol=rtol,
        atol=atol,
        equal_nan=True,
    )
