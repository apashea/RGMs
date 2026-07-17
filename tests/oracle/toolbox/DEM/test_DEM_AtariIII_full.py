"""ENTRY DEMO2 lane A — real verification only (no mocks).

Oracle / fixture tests for DEMO2. See ``Atari_example.md`` § **DEMO2 testing policy**.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from python_src.toolbox.DEM.entry12_atari_calls import (
    ENTRY12_ATARI_CALL3_TAG,
    ENTRY12_ATARI_CALL4_TAG,
    load_entry12_rdp_for_tag,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX


@pytest.mark.slow
def test_demo2_call3_fixture_vb_regression() -> None:
    """Frozen ``rgms_atari_call3`` RDP runs VB via unchanged ``python_src`` solver."""
    try:
        rdp = load_entry12_rdp_for_tag(ENTRY12_ATARI_CALL3_TAG)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    pdp = spm_MDP_VB_XXX(copy.deepcopy(rdp))
    assert isinstance(pdp, dict)
    t = int(np.asarray(pdp.get("T", 0), dtype=np.float64).reshape(-1)[0])
    assert t == 128


@pytest.mark.slow
def test_demo2_call4_fixture_vb_regression() -> None:
    """Frozen ``rgms_atari_call4`` RDP runs VB via unchanged ``python_src`` solver."""
    try:
        rdp = load_entry12_rdp_for_tag(ENTRY12_ATARI_CALL4_TAG)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    pdp = spm_MDP_VB_XXX(copy.deepcopy(rdp))
    assert isinstance(pdp, dict)
    t = int(np.asarray(pdp.get("T", 0), dtype=np.float64).reshape(-1)[0])
    assert t == 128
