"""Phase 1b: call-2 Entry 12 oracle (skip until MATLAB 1b + Python 3 fixtures exist)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from python_src.toolbox.DEM.entry12_atari_calls import (
    ENTRY12_ATARI_CALL2_TAG,
    entry12_atari_call_pdp_artifact_paths,
    entry12_atari_call_rdp_mat_path,
)

_REPO = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def call2_artifacts_ready() -> dict[str, Path]:
    paths = entry12_atari_call_pdp_artifact_paths(ENTRY12_ATARI_CALL2_TAG)
    rdp_build = entry12_atari_call_rdp_mat_path(ENTRY12_ATARI_CALL2_TAG)
    missing = [p for p in (rdp_build, paths["pdp_mat"], paths["pdp_pkl"]) if not p.is_file()]
    if missing:
        pytest.skip(
            "call-2 fixtures missing — run script 1b "
            "(DEMAtariIII_entry12_dump_all_subentries.m, inline ledger + call 2) "
            f"(need: {[m.name for m in missing]})"
        )
    return paths


def test_call2_rdp_build_mat_exists() -> None:
    p = entry12_atari_call_rdp_mat_path(ENTRY12_ATARI_CALL2_TAG)
    if not p.is_file():
        pytest.skip(f"run script 1b (extended dump) first: {p}")


@pytest.mark.skipif(
    not str(os.getenv("RGMS_ATARI_RUN_XXX_12", "")).strip().lower() in ("1", "true", "yes", "on"),
    reason="set RGMS_ATARI_RUN_XXX_12=1 to run script 3",
)
def test_call2_script3_generates_tagged_pkl(call2_artifacts_ready: dict[str, Path]) -> None:
    env = os.environ.copy()
    env["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = ENTRY12_ATARI_CALL2_TAG
    env["RGMS_ATARI_RUN_XXX_12"] = "1"
    env["RGMS_XXX_12_PDP_PKL_PATH"] = str(call2_artifacts_ready["pdp_pkl"])
    subprocess.run(
        [sys.executable, "-m", "pytest", str(Path(__file__).parent / "test_DEM_AtariIII_XXX_12.py"), "-q"],
        cwd=str(_REPO),
        env=env,
        check=True,
        timeout=7200,
    )
    assert call2_artifacts_ready["pdp_pkl"].is_file()


def test_call2_validation12_compare(call2_artifacts_ready: dict[str, Path]) -> None:
    env = os.environ.copy()
    env["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = ENTRY12_ATARI_CALL2_TAG
    env["RGMS_XXX_12_PDP_PKL_PATH"] = str(call2_artifacts_ready["pdp_pkl"])
    env["RGMS_XXX_12_PDP_MAT_PATH"] = str(call2_artifacts_ready["pdp_mat"])
    env["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = str(call2_artifacts_ready["pdp_mat"].parent)
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent / "XXX_12_compare_pdp_pkl_to_mat.py"),
            "--coerce-sparse-to-dense-for-compare",
        ],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        timeout=7200,
    )
    assert proc.returncode == 0, proc.stderr[-2000:] if proc.stderr else proc.stdout[-2000:]
