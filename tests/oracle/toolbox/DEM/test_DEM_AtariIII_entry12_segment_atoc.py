"""Entry 12_Segment_AtoC isolate test.

Integrated check for subentries 12A→12B→12C in DEM_AtariIII Entry-12 context:
- build Atari nested ``RDP`` through ``run_dem_atariiii(entry_stop=11)``,
- call ``spm_MDP_VB_XXX(RDP)`` in full mode,
- verify the interconnected A/B/C I/O contract before moving to 12D.
"""

from __future__ import annotations

import copy
import os

import numpy as np

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX


def test_entry12_segment_atoc_interconnected_in_dem_atariiii_context() -> None:
    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        ctx11 = run_dem_atariiii(entry_stop=11)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    assert "RDP" in ctx11 and isinstance(ctx11["RDP"], dict)
    rdp = copy.deepcopy(ctx11["RDP"])

    out = spm_MDP_VB_XXX(rdp)
    pdp = out[0] if isinstance(out, list) else out
    assert isinstance(pdp, dict)
    assert "_rgms_partial_v" not in pdp

    # A-side contract: full-mode single-epoch path yields assembled output.
    assert float(pdp["T"]) == 64.0
    assert "X" in pdp and isinstance(pdp["X"], list) and len(pdp["X"]) > 0
    assert "P" in pdp and isinstance(pdp["P"], list) and len(pdp["P"]) > 0
    assert "O" in pdp

    # B/C-side contract: domains and controllability bookkeeping present.
    assert "id" in pdp and isinstance(pdp["id"], dict)
    for k in ("fu", "fp", "A"):
        assert k in pdp["id"], f"missing id.{k}"
    fu = np.asarray(pdp["id"]["fu"]).ravel()
    fp = np.asarray(pdp["id"]["fp"]).ravel()
    assert fu.size + fp.size >= 1
