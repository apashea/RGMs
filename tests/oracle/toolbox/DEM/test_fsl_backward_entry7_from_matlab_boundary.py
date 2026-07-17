"""FSL backward Entry 7 — hit/miss assimilations from MATLAB-fed boundary.

Sign-off: isolated run + compare vs ``MDP_pre_entry9`` in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from python_src.toolbox.DEM.fsl_backward_entry7 import run_entry7_from_boundary

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_PRE7 = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl"
_ISOLATED = _DEM / "fsl_backward_run_entry7_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry7_pkl_to_mat.py"


@pytest.fixture
def fsl_backward_pre7_boundary() -> dict:
    if not _PRE7.is_file():
        pytest.skip(
            f"missing {_PRE7} — run dump_MDP_pre_entry10.m then "
            "fsl_backward_materialize_mdp_pre_entry7_pkl.py"
        )
    with _PRE7.open("rb") as f:
        return pickle.load(f)


def test_fsl_backward_entry7_run_from_boundary_in_process(fsl_backward_pre7_boundary) -> None:
    """Library API: same ledger as isolated runner (no subprocess)."""
    out = run_entry7_from_boundary(fsl_backward_pre7_boundary)
    assert isinstance(out["mdp"], list)
    assert out["n_windows"] == len(out["entry6_windows"])
    assert out["n_windows"] > 0


@pytest.mark.slow
def test_fsl_backward_entry7_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry7_isolated exited {iso.returncode}\n"
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
            f"fsl_backward_compare_entry7 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
