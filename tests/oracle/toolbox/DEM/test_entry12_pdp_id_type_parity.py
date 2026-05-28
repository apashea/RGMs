"""Compare-lane parity: nested ``MDP.id.A`` and ``T``/``U`` align for **12H** type-walk."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    entry12_align_mdp_to_mat_workspace,
    entry12_mat_pdp_for_value_assert,
    default_entry12_mat_output_dir,
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import _collect_type_mismatches

_TAG = ENTRY12_CANONICAL_RUN_TAG


def _canonical_12h_fixtures_present() -> bool:
    mat_p = entry12_subentry_mat_path(_TAG, "12H")
    pkl_p = default_entry12_mat_output_dir() / f"DEMAtariIII_entry12_{_TAG}_12H.pkl"
    return mat_p.is_file() and pkl_p.is_file()


@pytest.mark.skipif(
    not _canonical_12h_fixtures_present(),
    reason="canonical 12H mat/pkl fixtures required",
)
def test_12h_nested_id_a_and_t_u_type_walk_clean_after_shell_align() -> None:
    mat_pdp = mat_nested_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(_TAG, "12H")))[
        "PDP"
    ]
    with (default_entry12_mat_output_dir() / f"DEMAtariIII_entry12_{_TAG}_12H.pkl").open("rb") as f:
        py_pdp = pickle.load(f)["PDP"]

    import copy

    py = entry12_align_mdp_to_mat_workspace(copy.deepcopy(py_pdp), mat_pdp)
    mdp = py["MDP"]
    mat_mdp = mat_pdp["MDP"]
    for i in range(min(len(mdp["id"]["A"]), len(mat_mdp["id"]["A"]))):
        assert type(mdp["id"]["A"][i]) is type(mat_mdp["id"]["A"][i])
    assert isinstance(mdp["T"], (int, np.integer))
    assert type(mdp["U"]).__name__ == type(mat_mdp["U"]).__name__

    mat_cmp = entry12_mat_pdp_for_value_assert(mat_pdp)
    lines: list[str] = []
    _collect_type_mismatches(py, mat_cmp, "PDP", lines)
    assert lines == [], f"unexpected type-walk lines: {lines[:8]}"
