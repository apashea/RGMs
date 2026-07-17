"""FSL backward Entry 11 — isolated assembly from MATLAB-fed MDP (not full driver 1–11)."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from python_src.toolbox.DEM.entry12_atari_calls import load_entry12_rdp_for_tag
from python_src.toolbox.DEM.fsl_backward_entry11 import (
    entry11_rdp_for_entry12_vb,
    run_entry11_assembly_from_mdp,
)
from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal


def _pre11_pkl() -> Path:
    return (
        Path(__file__).resolve().parent
        / "fixtures"
        / "DEMAtariIII_fsl_backward_MDP_pre_entry11.pkl"
    )


def _entry12_rdp_mat() -> Path:
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call_rdp_mat_path

    return entry12_atari_call_rdp_mat_path("rgms_canonical")


@pytest.fixture
def fsl_backward_pre11_boundary() -> dict:
    p = _pre11_pkl()
    if not p.is_file():
        pytest.skip(
            f"missing {p} — run dump_MDP_pre_entry11.m then "
            "fsl_backward_materialize_mdp_pre_entry11_pkl.py"
        )
    with p.open("rb") as f:
        return pickle.load(f)


@pytest.mark.slow
def test_fsl_backward_entry11_vb_rdp_matches_entry12_script3(fsl_backward_pre11_boundary) -> None:
    """Entry 11 VB-input lane vs ``load_entry12_rdp_for_tag`` (script **3**)."""
    mat_path = _entry12_rdp_mat()
    if not mat_path.is_file():
        pytest.skip(f"missing Entry 12 Call 1 spec: {mat_path}")

    py_vb = entry11_rdp_for_entry12_vb(
        run_entry11_assembly_from_mdp(
            fsl_backward_pre11_boundary["mdp"],
            c_val=float(fsl_backward_pre11_boundary["C"]),
        ),
    )
    _assert_nested_rdp_equal(py_vb, load_entry12_rdp_for_tag("rgms_canonical"), "RDP")
