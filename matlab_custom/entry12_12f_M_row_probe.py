"""Log parent m=1 inclusion in M(t,:) across t (12F F drift)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_LOG: list[dict[str, object]] = []
_orig = vb._vb_run_partial_t_loop


def _wrap(models, bundle, alpha, recurse_partial, *, reuse_matlab_draws=False):
    t_int = int(bundle["T"])
    M_upd = bundle["M_update"]
    for t_idx in range(t_int):
        row = np.asarray(M_upd[t_idx, :], dtype=np.int64).ravel()
        _LOG.append(
            {
                "t_1based": t_idx + 1,
                "row": row.tolist(),
                "has_m1": bool(np.any(row == 1)),
            }
        )
    return _orig(
        models,
        bundle,
        alpha,
        recurse_partial,
        reuse_matlab_draws=reuse_matlab_draws,
    )


def main() -> None:
    vb._vb_run_partial_t_loop = _wrap
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb._vb_run_partial_t_loop = _orig
    out = ROOT / "matlab_custom" / "entry12_12f_M_row_probe.json"
    out.write_text(json.dumps(_LOG[:8], indent=2), encoding="utf-8")
    print(json.dumps(_LOG[:8], indent=2))


if __name__ == "__main__":
    main()
