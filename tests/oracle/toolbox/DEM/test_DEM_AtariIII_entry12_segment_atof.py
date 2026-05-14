"""Entry 12_Segment_AtoF isolate test.

Integrated check for subentries 12A→12F in DEM_AtariIII Entry-12 context:
- build Atari nested ``RDP`` through ``run_dem_atariiii(entry_stop=11)``,
- call ``spm_MDP_VB_XXX(RDP)`` in full mode,
- verify interconnected A..F contract fields before moving to 12G.

RDP source modes (same file):
- ``python`` (default): derive ``RDP`` from Python ``run_dem_atariiii(entry_stop=11)``.
- ``matlab``: MATLAB Engine pull of nested ``RDP`` at Entry 12 input (same as handoff capture).
"""

from __future__ import annotations

import copy
import os

import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry12_handoff_capture import (
    entry12_handoff_capture_driver_params,
    load_matlab_rdp_at_entry12_input,
)


def _segment_atof_rdp_source() -> str:
    raw = str(os.getenv("RGMS_ENTRY12_SEGMENT_ATOF_RDP_SOURCE", "python")).strip().lower()
    return raw if raw in {"python", "matlab"} else "python"


def test_entry12_segment_atof_interconnected_in_dem_atariiii_context(request: pytest.FixtureRequest) -> None:
    source = _segment_atof_rdp_source()

    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    if source == "python":
        os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
        os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        if source == "matlab":
            dem_eng = request.getfixturevalue("dem_eng_entry12")
            training_t, n_outer = entry12_handoff_capture_driver_params()
            rdp = load_matlab_rdp_at_entry12_input(dem_eng, training_t, n_outer)
        else:
            ctx11 = run_dem_atariiii(entry_stop=11)
            assert "RDP" in ctx11 and isinstance(ctx11["RDP"], dict)
            rdp = copy.deepcopy(ctx11["RDP"])
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    out = spm_MDP_VB_XXX(rdp)
    pdp = out[0] if isinstance(out, list) else out

    assert isinstance(pdp, dict)
    assert "_rgms_partial_v" not in pdp
    assert float(pdp["T"]) == 64.0

    # A..C contract fields
    assert "X" in pdp and isinstance(pdp["X"], list) and len(pdp["X"]) > 0
    assert "P" in pdp and isinstance(pdp["P"], list) and len(pdp["P"]) > 0
    assert "O" in pdp
    assert "id" in pdp and isinstance(pdp["id"], dict)
    for k in ("fu", "fp", "A"):
        assert k in pdp["id"], f"missing id.{k}"

    # D..F in-loop contract fields
    assert "R" in pdp and np.asarray(pdp["R"]).ndim == 2
    assert "v" in pdp and np.asarray(pdp["v"]).ndim == 2
    assert "w" in pdp and np.asarray(pdp["w"]).ndim == 2
    assert "F" in pdp and np.asarray(pdp["F"]).size > 0
    assert "G" in pdp and isinstance(pdp["G"], list) and len(pdp["G"]) >= 1
    assert "Z" in pdp and np.asarray(pdp["Z"]).size > 0
