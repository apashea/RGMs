"""Unit tests for ``python_src/toolbox/DEM/entry12_matlab_capture.py`` (path helpers + loadmat).

Does not require MATLAB; optional integration with real ``.mat`` files is manual.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    default_entry12_mat_output_dir,
    entry12_subentry_mat_filename,
    entry12_subentry_mat_path,
    entry12_subentry_mat_path_canonical,
    load_entry12_subentry_mat,
    rgms_repo_root,
    saved_rdp_dem_atariiii_mat_path,
)


def test_entry12_subentry_mat_filename_pattern() -> None:
    assert entry12_subentry_mat_filename("my-run", "12A") == "DEMAtariIII_entry12_my-run_12A.mat"


def test_entry12_subentry_mat_path_default_dir() -> None:
    p = entry12_subentry_mat_path("default", "12H")
    assert p.name == "DEMAtariIII_entry12_default_12H.mat"
    assert p.parent == default_entry12_mat_output_dir()


def test_entry12_subentry_mat_invalid_code() -> None:
    with pytest.raises(ValueError, match="12A-12I"):
        entry12_subentry_mat_filename("x", "99Z")


def test_load_entry12_subentry_mat_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "DEMAtariIII_entry12_testtag_12A.mat"
        savemat(str(p), {"MDP": np.array([1.0, 2.0]), "OPTIONS": np.array([])}, format="5")
        d = load_entry12_subentry_mat(p)
        assert "MDP" in d
        np.testing.assert_array_equal(np.asarray(d["MDP"]).ravel(), np.array([1.0, 2.0]))


def test_rgms_repo_root_is_python_src_parent() -> None:
    root = rgms_repo_root()
    assert (root / "python_src").is_dir()


def test_entry12_canonical_tag_non_empty() -> None:
    assert isinstance(ENTRY12_CANONICAL_RUN_TAG, str) and len(ENTRY12_CANONICAL_RUN_TAG) > 0


def test_entry12_subentry_mat_path_canonical_basename() -> None:
    p = entry12_subentry_mat_path_canonical("12A")
    assert f"_{ENTRY12_CANONICAL_RUN_TAG}_12A.mat" in p.name


def test_saved_rdp_path_under_matlab_custom() -> None:
    p = saved_rdp_dem_atariiii_mat_path()
    assert p.name == "saved_rdp_DEM_AtariIII.mat"
    assert "matlab_custom" in p.parts
