"""FSL backward Entry 5 — parameter forgetting from MATLAB-fed ``MDP_pre_entry5``.

Sign-off: isolated run + compare vs ``MDP_pre_entry7`` (post–Entry 5) in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from python_src.toolbox.DEM.fsl_backward_entry5 import run_entry5_from_boundary

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_PRE5 = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry5.pkl"
_ISOLATED = _DEM / "fsl_backward_run_entry5_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry5_pkl_to_mat.py"


@pytest.fixture
def fsl_backward_pre5_boundary() -> dict:
    if not _PRE5.is_file():
        pytest.skip(
            f"missing {_PRE5} — run patch_mdp_pre_entry5_to_pre_entry10_mat.m then "
            "fsl_backward_materialize_mdp_pre_entry5_pkl.py"
        )
    with _PRE5.open("rb") as f:
        return pickle.load(f)


def test_fsl_backward_entry5_run_from_boundary_in_process(fsl_backward_pre5_boundary) -> None:
    """Library API: same ledger as isolated runner (no subprocess)."""
    out = run_entry5_from_boundary(fsl_backward_pre5_boundary)
    assert isinstance(out["mdp"], list)
    assert out["Nm"] == len(out["mdp"])
    assert out["Ne"] == max(2 ** (out["Nm"] - 1), 1)
    import numpy as np

    for lev in out["mdp"]:
        for g in range(len(lev["a"])):
            assert np.asarray(lev["a"][g]).size == 0
        for f in range(len(lev["b"])):
            assert np.asarray(lev["b"][f]).size == 0


@pytest.mark.slow
def test_fsl_backward_entry5_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry5_isolated exited {iso.returncode}\n"
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
            f"fsl_backward_compare_entry5 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
