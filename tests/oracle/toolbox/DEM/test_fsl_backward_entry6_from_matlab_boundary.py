"""FSL backward Entry 6 — events and assimilation windows from MATLAB-fed ``PDP.o``.

Sign-off: isolated run + compare vs ``entry6_r``, ``entry6_c``, ``entry6_t_windows`` in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from python_src.toolbox.DEM.fsl_backward_entry6 import run_entry6_from_boundary

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_PRE6 = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry6.pkl"
_ISOLATED = _DEM / "fsl_backward_run_entry6_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry6_pkl_to_mat.py"


@pytest.fixture
def fsl_backward_pre6_boundary() -> dict:
    if not _PRE6.is_file():
        pytest.skip(
            f"missing {_PRE6} — run patch_entry6_authority or dump_MDP_pre_entry10.m then "
            "fsl_backward_materialize_mdp_pre_entry6_pkl.py"
        )
    with _PRE6.open("rb") as f:
        return pickle.load(f)


def test_fsl_backward_entry6_run_from_boundary_in_process(fsl_backward_pre6_boundary) -> None:
    """Library API: same ledger as isolated runner (no subprocess)."""
    out = run_entry6_from_boundary(fsl_backward_pre6_boundary)
    assert out["n_windows"] == len(out["entry6_windows"])
    assert out["n_windows"] > 0
    assert out["r"].size > 0
    assert out["c"].size > 0


@pytest.mark.slow
def test_fsl_backward_entry6_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry6_isolated exited {iso.returncode}\n"
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
            f"fsl_backward_compare_entry6 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
