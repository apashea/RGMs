"""Entry 12 canonical ``.mat`` oracle hooks (MATLAB capture vs Python).

Requires artifacts from ``DEMAtariIII_entry12_dump_all_subentries.m`` with
``RGMS_ENTRY12_CAPTURE_RUN_TAG`` matching :data:`ENTRY12_CANONICAL_RUN_TAG` (default ``rgms_canonical``),
plus ``matlab_custom/saved_rdp_DEM_AtariIII.mat``. Skip cleanly when files are absent.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    default_entry12_mat_output_dir,
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
    rgms_repo_root,
    saved_rdp_dem_atariiii_mat_path,
)
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
    load_saved_rdp_as_py,
    mat_nested_to_py,
)
from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal


def _effective_run_tag() -> str:
    return (os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG") or ENTRY12_CANONICAL_RUN_TAG).strip()


def _effective_out_dir() -> Path:
    raw = os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    return Path(raw) if raw else default_entry12_mat_output_dir()


def _require_saved_rdp() -> Path:
    p = saved_rdp_dem_atariiii_mat_path()
    if not p.is_file():
        pytest.skip(f"missing canonical RDP source: {p} (run matlab_custom/dump_rdp_DEM_AtariIII.m)")
    return p


def _require_mat12a() -> Path:
    tag = _effective_run_tag()
    od = _effective_out_dir()
    p12a = entry12_subentry_mat_path(tag, "12A", out_dir=od)
    if not p12a.is_file():
        pytest.skip(
            f"missing 12A capture: {p12a} "
            f"(MATLAB: setenv RGMS_ENTRY12_CAPTURE_RUN_TAG,{tag} "
            f"and run DEMAtariIII_entry12_dump_all_subentries)"
        )
    return p12a


@pytest.mark.slow
def test_entry12a_python_checkx_matches_matlab_capture_mdp() -> None:
    """Parity: ``spm_MDP_checkX(RDP)`` vs ``MDP`` in ``_12A.mat`` (same ``saved_rdp`` lineage)."""
    _require_saved_rdp()
    path_12a = _require_mat12a()

    rdp_py = load_saved_rdp_as_py(saved_rdp_dem_atariiii_mat_path())
    py_mdp = spm_MDP_checkX(copy.deepcopy(rdp_py))

    blob = load_entry12_subentry_mat(path_12a)
    assert "MDP" in blob
    mat_mdp = mat_nested_to_py(blob["MDP"])

    _assert_nested_rdp_equal(py_mdp, mat_mdp, "entry12.12A.MDP")


@pytest.mark.parametrize(
    "code",
    ("12A", "12B", "12C", "12D", "12E", "12F", "12G", "12H", "12I"),
)
def test_entry12_subentry_mat_loads_when_present(code: str) -> None:
    """Smoke: each subentry ``.mat`` loads under effective tag/out-dir when files exist."""
    tag = _effective_run_tag()
    od = _effective_out_dir()
    p = entry12_subentry_mat_path(tag, code, out_dir=od)
    if not p.is_file():
        pytest.skip(f"missing {p}")
    blob = load_entry12_subentry_mat(p)
    assert "OPTIONS" in blob and "meta" in blob
    if code == "12I":
        assert "OPTIONS" in blob and "meta" in blob
    if code == "12H":
        assert "PDP" in blob


def test_entry12_canonical_paths_documented() -> None:
    """Sanity: canonical tag resolves (no I/O)."""
    assert ENTRY12_CANONICAL_RUN_TAG
    p = entry12_subentry_mat_path(ENTRY12_CANONICAL_RUN_TAG, "12A")
    assert p.name.startswith("DEMAtariIII_entry12_")


def test_repo_root_contains_matlab_custom() -> None:
    assert (rgms_repo_root() / "matlab_custom").is_dir()
