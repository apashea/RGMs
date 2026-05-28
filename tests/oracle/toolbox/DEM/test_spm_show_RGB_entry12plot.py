"""Oracle: ENTRY 12PLOT — ``J``/``K``/``h`` vs MATLAB capture (no VB re-run).

Phase A (primary): Python plot on **MATLAB ``PDP``** loaded from ``DEMAtariIII_XXX_12_pdp.mat``.
Phase B (after A green): same oracle targets on **Python Entry 12 ``PDP``** from ``DEMAtariIII_XXX_12_pdp.pkl``.

Fixtures (produce once; see ``Atari_plotting.md`` § Plot artifact registry):
  1. ``dump_rdp_DEM_AtariIII_FSL_1_11.m`` → ``DEMAtariIII_fsl_1_11_plot_ctx.mat``
  2. ``DEMAtariIII_entry12_dump_all_subentries.m`` (1b) → ``DEMAtariIII_XXX_12_pdp.mat``
  3. ``DEMAtariIII_entry12_12plot_capture.m`` → ``DEMAtariIII_entry12_<tag>_12PLOT.mat`` + PNG
"""

from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest
from scipy.io import loadmat

from python_src.toolbox.DEM.entry12_plot import (
    DEFAULT_TAG,
    load_12plot_oracle_from_mat,
    load_pdp_mat_for_plot,
    load_pdp_pkl_for_plot,
    load_plot_ctx_from_mat,
    plot_ctx_mat_path,
    plot_oracle_mat_path,
    pdp_mat_path,
    pdp_pkl_path,
    run_entry12plot,
)

_REPO = Path(__file__).resolve().parents[4]
_TAG = DEFAULT_TAG


def _require(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"missing fixture: {path}")
    return path


def _load_pdp_mat() -> dict:
    return load_pdp_mat_for_plot(_require(pdp_mat_path(_REPO)))


def _load_pdp_pkl() -> dict:
    return load_pdp_pkl_for_plot(_require(pdp_pkl_path(_REPO)))


def _assert_jkh(j, k, h, oracle: dict) -> None:
    np.testing.assert_array_equal(j, oracle["J"])
    np.testing.assert_array_equal(k, oracle["K"])
    np.testing.assert_array_equal(h, oracle["h"])


@pytest.fixture(scope="module")
def plot_ctx():
    return load_plot_ctx_from_mat(_require(plot_ctx_mat_path(_REPO)))


@pytest.fixture(scope="module")
def plot_oracle():
    return load_12plot_oracle_from_mat(_require(plot_oracle_mat_path(_TAG, _REPO)))


def test_entry12plot_matlab_pdp_jkh_oracle(plot_ctx, plot_oracle):
    """Phase A: plot code on MATLAB-native ``PDP`` (.mat) — primary sign-off."""
    pdp = _load_pdp_mat()
    j, k, h, png = run_entry12plot(pdp, plot_ctx, repo_root=_REPO, save_png=True)
    assert png is not None and png.is_file()
    assert png.name.startswith("AtariIII_12plot_")
    _assert_jkh(j, k, h, plot_oracle)


def test_entry12plot_python_pdp_jkh_oracle(plot_ctx, plot_oracle):
    """Phase B: same ``J``/``K``/``h`` oracle using Python Entry 12 ``PDP`` (.pkl)."""
    pdp = _load_pdp_pkl()
    j, k, h, _png = run_entry12plot(pdp, plot_ctx, repo_root=_REPO, save_png=False)
    _assert_jkh(j, k, h, plot_oracle)
