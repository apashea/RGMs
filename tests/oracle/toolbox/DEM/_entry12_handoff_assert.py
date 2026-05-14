from __future__ import annotations

from typing import Any

import numpy as np


def assert_deep_exact_equal(a: Any, b: Any, path: str = "root") -> None:
    if type(a) is not type(b):
        raise AssertionError(f"{path}: type mismatch {type(a)!r} != {type(b)!r}")

    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            raise AssertionError(f"{path}: dict keys mismatch")
        for k in sorted(a.keys(), key=str):
            assert_deep_exact_equal(a[k], b[k], f"{path}.{k}")
        return

    if isinstance(a, list):
        if len(a) != len(b):
            raise AssertionError(f"{path}: list length mismatch {len(a)} != {len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            assert_deep_exact_equal(ai, bi, f"{path}[{i}]")
        return

    if isinstance(a, tuple):
        if len(a) != len(b):
            raise AssertionError(f"{path}: tuple length mismatch {len(a)} != {len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            assert_deep_exact_equal(ai, bi, f"{path}({i})")
        return

    if isinstance(a, np.ndarray):
        if a.shape != b.shape:
            raise AssertionError(f"{path}: shape mismatch {a.shape} != {b.shape}")
        if a.dtype != b.dtype:
            raise AssertionError(f"{path}: dtype mismatch {a.dtype} != {b.dtype}")
        if not np.array_equal(a, b, equal_nan=True):
            raise AssertionError(f"{path}: ndarray values differ")
        return

    if isinstance(a, (np.floating, float)):
        if np.isnan(a) and np.isnan(b):
            return
        if float(a) != float(b):
            raise AssertionError(f"{path}: float mismatch {a} != {b}")
        return

    if isinstance(a, (np.integer, int, np.bool_, bool, str, type(None))):
        if a != b:
            raise AssertionError(f"{path}: scalar mismatch {a!r} != {b!r}")
        return

    if hasattr(a, "toarray") and hasattr(b, "toarray"):
        aa = np.asarray(a.toarray())
        bb = np.asarray(b.toarray())
        assert_deep_exact_equal(aa, bb, path + ".toarray")
        return

    if a != b:
        raise AssertionError(f"{path}: value mismatch {a!r} != {b!r}")
