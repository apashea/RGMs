"""C4o contracts: belief_after Nu>1 LL F-order specialize ≡ nested ``spm_dot``."""
from __future__ import annotations

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.vb_orchestrator_optim import (
    _belief_after_ll_from_B_Qt_Qtm1,
)
from python_src.spm_dot import spm_dot


def _ref(B: np.ndarray, Qt: np.ndarray, Qtm1: np.ndarray) -> np.ndarray:
    return np.asarray(spm_dot(spm_dot(B, Qt), Qtm1), dtype=np.float64)


@pytest.mark.parametrize(
    "shape",
    [
        (485, 485, 6),  # nr_g01 dominant belief_after Nu>1
        (183, 183, 5),  # call4 dominant
        (41, 41, 14),
        (10, 10, 10),
        (9, 9, 3),
        (2, 2, 2),
    ],
)
def test_belief_after_ll_matches_nested_spm_dot_f_order(
    shape: tuple[int, int, int],
) -> None:
    rng = np.random.default_rng(7)
    B = np.asfortranarray(rng.random(shape))
    Qt = rng.random((shape[0], 1))
    Qtm1 = rng.random((shape[0], 1))
    got = _belief_after_ll_from_B_Qt_Qtm1(B, Qt, Qtm1)
    ref = _ref(B, Qt, Qtm1)
    assert got.shape == ref.shape
    # Nested spm_dot vs single GEMM: ~1e-11 class on large Ns (same as C4m prior_qp).
    np.testing.assert_allclose(got, ref, rtol=0.0, atol=1e-10)


def test_belief_after_ll_c_order_b_matches_ref() -> None:
    rng = np.random.default_rng(11)
    B = np.ascontiguousarray(rng.random((41, 41, 14)))
    Qt = rng.random((41, 1))
    Qtm1 = rng.random((41, 1))
    got = _belief_after_ll_from_B_Qt_Qtm1(B, Qt, Qtm1)
    ref = _ref(B, Qt, Qtm1)
    np.testing.assert_allclose(got, ref, rtol=0.0, atol=1e-10)


def test_belief_after_ll_2d_fallback_matches_ref() -> None:
    rng = np.random.default_rng(13)
    B = rng.random((8, 8))
    Qt = rng.random((8, 1))
    Qtm1 = rng.random((8, 1))
    got = _belief_after_ll_from_B_Qt_Qtm1(B, Qt, Qtm1)
    ref = _ref(B, Qt, Qtm1)
    np.testing.assert_allclose(got, ref, rtol=0.0, atol=1e-10)
