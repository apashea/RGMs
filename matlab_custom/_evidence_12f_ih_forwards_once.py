"""Run one XXX12-style VB; print iH term once at parent t=1 (env-gated in spm_forwards)."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["RGMS_DIAG_12F_IH_ONCE"] = "1"

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX, _default_options_vb
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp


def main() -> None:
    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    opts = _default_options_vb()
    opts["monitoring"] = 0
    spm_MDP_VB_XXX(rdp, options=opts, reuse_matlab_draws=True)


if __name__ == "__main__":
    main()
