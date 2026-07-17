"""Oracle tests: spm_RDP_sort_optim vs fidelity (OPTIM1 Entry 10)."""

from __future__ import annotations

import copy
import pickle

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_RDP_sort_optim import (
    _ness_prune_mask_col_support,
    _ness_prune_mask_shrinking_active,
    spm_RDP_sort_optim,
)
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort
from tests.demo1.demo1_paths import demo1_fixtures_dir
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal


def _fidelity_ness_prune_mask(b_mat: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Fidelity ``j_mask`` loop from ``spm_RDP_sort`` (boolean mask form)."""
    ns = int(b_mat.shape[0])
    idx = np.arange(ns, dtype=np.int64)
    j_mask = np.ones(ns, dtype=bool)
    k = np.lexsort((idx, p))
    for i in k:
        d = j_mask.copy()
        d[int(i)] = False
        if not np.any(d):
            continue
        b_dd = b_mat[np.ix_(d, d)]
        if np.all(np.any(b_dd, axis=0)):
            j_mask = d
    return j_mask


@pytest.mark.parametrize("seed", [0, 1, 42, 99, 123])
def test_ness_prune_col_support_matches_fidelity_mask(seed: int):
    rng = np.random.default_rng(seed)
    ns = 12
    b_mat = (rng.random((ns, ns)) > 0.55).astype(np.float64)
    np.fill_diagonal(b_mat, 1.0)
    p = rng.random(ns)
    p = p / np.sum(p)
    opt = _ness_prune_mask_col_support(b_mat, p, ns)
    fid = _fidelity_ness_prune_mask(b_mat, p)
    np.testing.assert_array_equal(opt, fid)


@pytest.mark.parametrize("seed", [0, 1, 42])
def test_ness_prune_shrinking_active_matches_fidelity_mask(seed: int):
    rng = np.random.default_rng(seed)
    ns = 12
    b_mat = (rng.random((ns, ns)) > 0.55).astype(np.float64)
    np.fill_diagonal(b_mat, 1.0)
    p = rng.random(ns)
    p = p / np.sum(p)
    opt = _ness_prune_mask_shrinking_active(b_mat, p, ns)
    fid = _fidelity_ness_prune_mask(b_mat, p)
    np.testing.assert_array_equal(opt, fid)


@pytest.mark.slow
def test_spm_RDP_sort_optim_matches_fidelity_demo1_pre_entry10():
    """Production boundary — native ``eig`` (holistic OPTIM1 driver path)."""
    pkl = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    if not pkl.is_file():
        pytest.skip(f"missing DEMO1 boundary {pkl}")
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    mdp = blob["mdp"]
    m_fid, j_fid = spm_RDP_sort(copy.deepcopy(mdp))
    m_opt, j_opt = spm_RDP_sort_optim(copy.deepcopy(mdp))
    _assert_mdp_full_equal(m_opt, m_fid, k=10)
    np.testing.assert_array_equal(
        np.asarray(j_opt, dtype=np.int64).ravel(order="F"),
        np.asarray(j_fid, dtype=np.int64).ravel(order="F"),
    )
