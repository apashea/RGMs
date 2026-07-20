"""Contracts for prior_qp F-order ``B×P`` transition (Step A1; unwired until wall GO)."""
from __future__ import annotations

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.vb_orchestrator_optim import _prior_qp_transition_from_BP
from python_src.spm_dot import spm_dot


def _ref(B: np.ndarray, P: np.ndarray) -> np.ndarray:
    return np.asarray(spm_dot(B, [P]), dtype=np.float64)


@pytest.mark.parametrize(
    "shape",
    [
        (485, 485, 6),  # nr_g01 dominant prior_qp key
        (183, 183, 5),  # call4 dominant analogue
        (41, 41, 14),
        (10, 10, 10),
        (9, 9, 3),
        (2, 2, 2),
    ],
)
def test_prior_qp_transition_matches_spm_dot_f_order(shape: tuple[int, int, int]) -> None:
    rng = np.random.default_rng(0)
    B = np.asfortranarray(rng.random(shape))
    P = rng.random((shape[2], 1))
    got = _prior_qp_transition_from_BP(B, P)
    exp = _ref(B, P)
    assert got.shape == exp.shape
    np.testing.assert_allclose(got, exp, rtol=0.0, atol=1e-11)


def test_prior_qp_transition_matches_spm_dot_c_order_input() -> None:
    """In-situ is F-order; still require C-order input correctness."""
    rng = np.random.default_rng(1)
    B = np.ascontiguousarray(rng.random((64, 64, 4)))
    P = rng.random((4, 1))
    got = _prior_qp_transition_from_BP(B, P)
    exp = _ref(B, P)
    np.testing.assert_allclose(got, exp, rtol=0.0, atol=1e-11)


def test_prior_qp_transition_fallback_nonsquare() -> None:
    rng = np.random.default_rng(2)
    B = np.asfortranarray(rng.random((8, 5, 3)))
    P = rng.random((3, 1))
    got = _prior_qp_transition_from_BP(B, P)
    exp = _ref(B, P)
    np.testing.assert_allclose(got, exp, rtol=0.0, atol=1e-11)
