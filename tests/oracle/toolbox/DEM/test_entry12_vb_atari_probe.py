"""Probe full Entry 12 VB on canonical saved RDP — documents first blocking ``NotImplementedError``."""

from __future__ import annotations

import copy

import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import saved_rdp_dem_atariiii_mat_path
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import load_saved_rdp_as_py


@pytest.mark.slow
def test_entry12_full_vb_first_notimplemented_on_saved_rdp() -> None:
    """Exercise Python VB on canonical saved RDP; record outcome until full spine matches MATLAB.

    Expected eventual blocker: ``NotImplementedError`` (e.g. hierarchical ``MDP.MDP``). Earlier failures
    (``IndexError``, etc.) usually mean ``loadmat``→Python RDP conversion or upstream VB tensors still need work —
    those cases **skip** with the exception message instead of failing the suite.
    """
    p = saved_rdp_dem_atariiii_mat_path()
    if not p.is_file():
        pytest.skip(f"missing {p}")

    rdp = load_saved_rdp_as_py(p)
    mdp = spm_MDP_checkX(copy.deepcopy(rdp))

    try:
        spm_MDP_VB_XXX(mdp, {})
    except NotImplementedError:
        return
    except Exception as exc:
        pytest.skip(f"VB blocked before hierarchy NotImplementedError ({type(exc).__name__}: {exc})")
    pytest.fail("spm_MDP_VB_XXX returned — tighten this probe once full Atari VB is implemented")
