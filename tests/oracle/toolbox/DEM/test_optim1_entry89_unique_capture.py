"""Oracle: captured Atari ``spm_unique`` / ``spm_information_distance`` refs (Tier B2 guard)."""

from __future__ import annotations

import copy
import pickle
from pathlib import Path

import numpy as np
import pytest

from python_src.optimized.toolbox.DEM.spm_information_distance_optim import (
    spm_information_distance_optim,
)
from python_src.optimized.toolbox.DEM.spm_unique_optim import spm_unique_optim
from python_src.toolbox.DEM.spm_information_distance import spm_information_distance
from python_src.toolbox.DEM.spm_unique import spm_unique

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


def _merge_cases_with_unique(capture: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for name in ("merge_outer1_inner1", "merge_outer2_inner1"):
        case = capture["cases"][name]
        if "unique_samples" not in case:
            pytest.skip(
                f"capture missing unique_samples in {name} — re-run optim1_capture_entry89_regression.py"
            )
        out.append((name, case))
    return out


@pytest.mark.parametrize("case_name", ["merge_outer1_inner1", "merge_outer2_inner1"])
def test_capture_unique_samples_fidelity_reproduces_refs(
    entry89_capture: dict, case_name: str
) -> None:
    case = entry89_capture["cases"][case_name]
    samples = case.get("unique_samples")
    if not samples:
        pytest.skip(f"no unique_samples in {case_name}")
    for idx, sample in enumerate(samples):
        combined = copy.deepcopy(sample["combined"])
        i_out, j_out = spm_unique(combined)
        d_out, _ = spm_information_distance(copy.deepcopy(sample["combined"]))
        i_ref = np.asarray(sample["i_ref"], dtype=np.int64).ravel(order="F")
        j_ref = np.asarray(sample["j_ref"], dtype=np.int64).ravel(order="F")
        i_py = np.asarray(i_out, dtype=np.int64).ravel(order="F")
        j_py = np.asarray(j_out, dtype=np.int64).ravel(order="F")
        np.testing.assert_array_equal(i_py, i_ref, err_msg=f"{case_name} sample {idx} i mismatch")
        np.testing.assert_array_equal(j_py, j_ref, err_msg=f"{case_name} sample {idx} j mismatch")
        np.testing.assert_allclose(
            np.asarray(d_out, dtype=np.float64),
            np.asarray(sample["D_ref"], dtype=np.float64),
            rtol=0.0,
            atol=1e-12,
            err_msg=f"{case_name} sample {idx} D mismatch",
        )


@pytest.mark.parametrize("case_name", ["merge_outer1_inner1", "merge_outer2_inner1"])
def test_capture_unique_samples_optim_matches_refs(
    entry89_capture: dict, case_name: str
) -> None:
    case = entry89_capture["cases"][case_name]
    samples = case.get("unique_samples")
    if not samples:
        pytest.skip(f"no unique_samples in {case_name}")
    for idx, sample in enumerate(samples):
        combined = copy.deepcopy(sample["combined"])
        i_out, j_out = spm_unique_optim(combined)
        d_out, _ = spm_information_distance_optim(copy.deepcopy(sample["combined"]))
        i_ref = np.asarray(sample["i_ref"], dtype=np.int64).ravel(order="F")
        j_ref = np.asarray(sample["j_ref"], dtype=np.int64).ravel(order="F")
        i_py = np.asarray(i_out, dtype=np.int64).ravel(order="F")
        j_py = np.asarray(j_out, dtype=np.int64).ravel(order="F")
        np.testing.assert_array_equal(i_py, i_ref, err_msg=f"{case_name} sample {idx} i mismatch")
        np.testing.assert_array_equal(j_py, j_ref, err_msg=f"{case_name} sample {idx} j mismatch")
        np.testing.assert_allclose(
            np.asarray(d_out, dtype=np.float64),
            np.asarray(sample["D_ref"], dtype=np.float64),
            rtol=0.0,
            atol=1e-12,
            err_msg=f"{case_name} sample {idx} D mismatch",
        )


def test_capture_unique_samples_stable_row_count(entry89_capture: dict) -> None:
    for case_name, case in _merge_cases_with_unique(entry89_capture):
        for idx, sample in enumerate(case["unique_samples"]):
            i = np.asarray(sample["i_ref"], dtype=np.int64).ravel(order="F")
            j = np.asarray(sample["j_ref"], dtype=np.int64).ravel(order="F")
            d = np.asarray(sample["D_ref"], dtype=np.float64)
            assert i.size >= 1, f"{case_name}[{idx}] empty i"
            assert j.size == d.shape[0], f"{case_name}[{idx}] j/D row mismatch"
            assert d.shape[0] == d.shape[1], f"{case_name}[{idx}] D not square"
