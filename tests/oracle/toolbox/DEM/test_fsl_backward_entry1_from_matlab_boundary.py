"""FSL backward Entry 1 — snippet constants on ``rng(2)`` ledger."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_ISOLATED = _DEM / "fsl_backward_run_entry1_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry1_pkl_to_mat.py"
_MAT = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def test_fsl_backward_entry1_constants_in_process() -> None:
    from python_src.toolbox.DEM.fsl_backward_entry1 import run_entry1_from_boundary

    out = run_entry1_from_boundary({})
    assert int(out["Nr"]) == 12
    assert int(out["C"]) == 32


@pytest.mark.slow
def test_fsl_backward_entry1_driver_replay_in_process() -> None:
    from tests.oracle.toolbox.DEM.fsl_backward_preflight_rand_k_entry1 import main as preflight_main

    from python_src.toolbox.DEM.fsl_backward_entry1 import run_entry1_driver_ledger_replay

    if not _MAT.is_file():
        pytest.skip(f"missing {_MAT}")

    if preflight_main() != 0:
        pytest.fail("fsl_backward_preflight_rand_k_entry1 failed")

    out = run_entry1_driver_ledger_replay()
    assert out.get("validation_lane") == "driver_ledger_replay"


def test_fsl_backward_entry1_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry1_isolated exited {iso.returncode}\n"
            f"stdout:\n{iso.stdout}\nstderr:\n{iso.stderr}"
        )
    proc = subprocess.run(
        [sys.executable, str(_COMPARE)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"fsl_backward_compare_entry1 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
