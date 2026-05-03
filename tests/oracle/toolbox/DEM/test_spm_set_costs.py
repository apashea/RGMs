"""Oracle: ``spm_set_costs`` MATLAB vs Python (Entry 10 goals MDP boundary)."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import load_or_build_entry10_sort_artifact


@pytest.fixture
def dem_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


@pytest.mark.slow
def test_spm_set_costs_matlab_capture_oracle(dem_eng):
    """Python ``spm_set_costs`` matches MATLAB capture on ``mdp10_goals_mat``.

    Artifact ``mdp11_costs_mat`` is MATLAB ``spm_set_costs(...,[2,3],[C,-C])`` after
    goals; Python starts from a deep copy of ``mdp10_goals_mat`` with the same call.
    """
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = load_or_build_entry10_sort_artifact(dem_eng, training_t, n_outer)
    mdp_in = copy.deepcopy(artifact["mdp10_goals_mat"])
    out = spm_set_costs(
        mdp_in,
        np.array([2.0, 3.0], dtype=np.float64),
        np.array([32.0, -32.0], dtype=np.float64),
    )
    _assert_mdp_full_equal(out, artifact["mdp11_costs_mat"], 1)
