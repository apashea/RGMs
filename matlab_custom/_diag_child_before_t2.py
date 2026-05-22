"""Capture py child MDP immediately before hierarchical VB at parent t=2."""
from __future__ import annotations

import copy
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

OUT = ROOT / "matlab_custom" / "_tmp_child_before_t2.pkl"
saved: dict = {}


def hook(models, bundle, t_idx, M_row, recurse_partial, **kw):
    if t_idx == 1 and vb._VB_TIMING_DEPTH == 1 and "child" not in saved:
        M_vec = np.asarray(M_row, dtype=np.int64).ravel()
        mi = int(M_vec[0]) - 1
        parent = models[mi]
        mdp_field = parent["MDP"]
        child = copy.deepcopy(mdp_field[0] if isinstance(mdp_field, list) else mdp_field)
        saved["child"] = child
        saved["parent_Q_t"] = [copy.deepcopy(bundle["Q"][mi][f][t_idx]) for f in range(len(bundle["Q"][mi]))]
    return orig(models, bundle, t_idx, M_row, recurse_partial, **kw)


orig = vb._vb_hierarchical_subordinate_outcomes


def main() -> None:
    vb._vb_hierarchical_subordinate_outcomes = hook
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb._vb_hierarchical_subordinate_outcomes = orig
    with open(OUT, "wb") as f:
        pickle.dump(saved, f)
    c = saved["child"]
    f = 1
    print("child P{f} shape", np.asarray(c["P"][f]).shape)
    print("child P{f}(:,end)", np.asarray(c["P"][f])[:, -1].ravel()[:6])
    print("child E{f}", np.asarray(c["E"][f]).ravel()[:6])
    print("child D{f}", np.asarray(c["D"][f]).ravel()[:6])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
