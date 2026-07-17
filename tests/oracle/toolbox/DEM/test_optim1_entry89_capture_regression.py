"""Oracle tests using captured Atari boundary slices (OPTIM1 high-risk regression guard)."""

from __future__ import annotations

import copy
import pickle
from pathlib import Path

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_merge_structure_learning_optim import (
    spm_merge_structure_learning_optim,
)
from python_src.optimized.toolbox.DEM.spm_RDP_basin_optim import spm_RDP_basin_optim
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

_CAPTURE = (
    Path(__file__).resolve().parent
    / "_checkpoint_data"
    / "optim1_entry89"
    / "optim1_entry89_atari_boundary_slices.pkl"
)


@pytest.fixture(scope="module")
def entry89_capture() -> dict:
    if not _CAPTURE.is_file():
        pytest.skip(
            f"missing {_CAPTURE} — run: "
            "python tests/demo1/optim1/optim1_capture_entry89_regression.py"
        )
    with _CAPTURE.open("rb") as f:
        blob = pickle.load(f)
    return blob


def test_capture_merge_cases_fidelity_matches_ref(entry89_capture: dict) -> None:
    for name in ("merge_outer1_inner1", "merge_outer2_inner1"):
        case = entry89_capture["cases"][name]
        out = spm_merge_structure_learning(copy.deepcopy(case["O"]), copy.deepcopy(case["MDP_in"]))
        _assert_mdp_full_equal(out, case["MDP_out_ref"], k=8)


def test_capture_merge_cases_optim_matches_ref(entry89_capture: dict) -> None:
    for name in ("merge_outer1_inner1", "merge_outer2_inner1"):
        case = entry89_capture["cases"][name]
        out = spm_merge_structure_learning_optim(
            copy.deepcopy(case["O"]), copy.deepcopy(case["MDP_in"])
        )
        _assert_mdp_full_equal(out, case["MDP_out_ref"], k=8)


def test_capture_basin_fidelity_matches_ref(entry89_capture: dict) -> None:
    case = entry89_capture["cases"]["basin_after_two_merges"]
    mdp_out, d, o, h, c = spm_RDP_basin(
        copy.deepcopy(case["MDP_in"]), case["S"], case["chi"]
    )
    _assert_mdp_full_equal(mdp_out, case["MDP_out_ref"], k=9)
    assert np.array_equal(np.asarray(d, dtype=bool).ravel(order="F"), np.asarray(case["d_ref"], dtype=bool).ravel(order="F"))
    assert np.array_equal(np.asarray(o, dtype=bool).ravel(order="F"), np.asarray(case["o_ref"], dtype=bool).ravel(order="F"))


def test_capture_basin_optim_matches_ref(entry89_capture: dict) -> None:
    case = entry89_capture["cases"]["basin_after_two_merges"]
    mdp_out, d, o, h, c = spm_RDP_basin_optim(
        copy.deepcopy(case["MDP_in"]), case["S"], case["chi"]
    )
    _assert_mdp_full_equal(mdp_out, case["MDP_out_ref"], k=9)
    assert np.array_equal(np.asarray(d, dtype=bool).ravel(order="F"), np.asarray(case["d_ref"], dtype=bool).ravel(order="F"))
