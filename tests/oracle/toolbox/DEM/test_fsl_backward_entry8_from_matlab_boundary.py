"""FSL backward Entry 8 — merge-only loop from MATLAB-fed ``MDP_pre_entry9`` + ``PDP.O``.

Sign-off: isolated run + compare vs ``MDP_post_entry8`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.
See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from python_src.toolbox.DEM.fsl_backward_entry8 import run_entry8_from_boundary

_REPO = Path(__file__).resolve().parents[4]
_DEM = Path(__file__).resolve().parent
_PRE9 = _DEM / "fixtures" / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
_ISOLATED = _DEM / "fsl_backward_run_entry8_isolated.py"
_COMPARE = _DEM / "fsl_backward_compare_entry8_pkl_to_mat.py"


@pytest.fixture
def fsl_backward_pre9_boundary() -> dict:
    if not _PRE9.is_file():
        pytest.skip(
            f"missing {_PRE9} — run dump_MDP_pre_entry10.m then "
            "fsl_backward_materialize_mdp_pre_entry9_pkl.py"
        )
    with _PRE9.open("rb") as f:
        return pickle.load(f)


def test_fsl_backward_entry8_run_from_boundary_in_process(fsl_backward_pre9_boundary) -> None:
    """Library API: same ledger as isolated runner (no subprocess)."""
    out = run_entry8_from_boundary(fsl_backward_pre9_boundary)
    assert isinstance(out["mdp"], list)
    assert out["n_outer"] > 0


@pytest.mark.slow
def test_fsl_backward_entry8_matlab_boundary_compare():
    iso = subprocess.run(
        [sys.executable, str(_ISOLATED)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if iso.returncode != 0:
        raise AssertionError(
            f"fsl_backward_run_entry8_isolated exited {iso.returncode}\n"
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
            f"fsl_backward_compare_entry8 exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
