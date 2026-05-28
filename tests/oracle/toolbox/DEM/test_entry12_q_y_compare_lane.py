"""Oracle: ``Q.Y`` compare-lane pairs flat script **3** row with ``o + t*Ng`` (not ``Q.O`` shiftdim order)."""

from __future__ import annotations

import copy
import pickle
from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import (
    _entry12_align_Q_record_to_mat,
    entry12_align_mdp_to_mat_workspace,
    entry12_mat_pdp_for_value_assert,
)
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp

_REPO = Path(__file__).resolve().parents[4]
_FIX = _REPO / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"
_PKL = _FIX / "DEMAtariIII_XXX_12_pdp.pkl"
_MAT = _FIX / "DEMAtariIII_XXX_12_pdp.mat"


@pytest.fixture(scope="module")
def paired_pdp():
    if not _PKL.is_file() or not _MAT.is_file():
        pytest.skip("missing Entry 12 PDP fixtures (run 1b and 3)")
    with _PKL.open("rb") as f:
        py_pdp = pickle.load(f)["PDP"]
    mat_pdp = _load_matlab_pdp(_MAT)
    return py_pdp, mat_pdp


def test_entry12_q_y_align_preserves_python_cells(paired_pdp):
    """Compare align must not alter nested ``Q.Y{L}`` ``[o][t]`` already in the pickle."""
    py_pdp, mat_pdp = paired_pdp
    raw_y = py_pdp["MDP"]["Q"]["Y"][0]
    mat_q = mat_pdp["MDP"]["Q"]
    aligned_q = _entry12_align_Q_record_to_mat(py_pdp["MDP"]["Q"], mat_q)
    ali = aligned_q["Y"]
    ng, ncol = 111, 128
    mismatches = 0
    for o in range(ng):
        for t in range(ncol):
            rv = np.asarray(raw_y[o][t], dtype=np.float64).ravel()
            av = np.asarray(ali[o][t], dtype=np.float64).ravel()
            if rv.shape != av.shape or not np.allclose(rv, av, rtol=0.0, atol=1e-10):
                mismatches += 1
    assert mismatches == 0, f"align changed {mismatches} Q.Y cells vs raw Python pkl"


def test_entry12_q_y_pdp_value_assert_green_on_fixture(paired_pdp):
    """Paired ``rgms_canonical`` ``Q.Y`` matches after honest ``o + t*Ng`` pairing."""
    py_pdp, mat_pdp = paired_pdp
    py_cmp = entry12_align_mdp_to_mat_workspace(copy.deepcopy(py_pdp), mat_pdp)
    mat_cmp = entry12_mat_pdp_for_value_assert(mat_pdp)
    py_y = py_cmp["MDP"]["Q"]["Y"]
    mat_y = mat_cmp["MDP"]["Q"]["Y"]
    assert len(py_y) == len(mat_y) == 111
    for o in range(111):
        assert len(py_y[o]) == len(mat_y[o]) == 128
        for t in range(128):
            pa = np.asarray(py_y[o][t], dtype=np.float64).ravel()
            ma = np.asarray(mat_y[o][t], dtype=np.float64).ravel()
            assert pa.shape == ma.shape
            assert np.allclose(pa, ma, rtol=0.0, atol=1e-10), f"Q.Y[{o}][{t}]"
