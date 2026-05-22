"""Child state immediately before/after second hierarchical VB (parent t=2)."""
from __future__ import annotations

import copy
import sys

import numpy as np

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

F_PATH = 1  # P{2}


def _peak(v):
    a = np.asarray(v, dtype=float).ravel()
    return a.size, int(np.argmax(a) + 1), float(a[0]), a[:5].tolist()


def main() -> None:
    pre: dict = {}
    post: dict = {}

    orig = vb._vb_hierarchical_subordinate_outcomes

    def hook(models, bundle, t_idx, M_row, recurse_partial, **kw):
        if t_idx == 1 and vb._VB_TIMING_DEPTH == 1:
            mi = int(np.asarray(M_row, dtype=np.int64).ravel()[0]) - 1
            parent = models[mi]
            mdp_field = parent["MDP"]
            child = mdp_field[0] if isinstance(mdp_field, list) else mdp_field
            pre["E"] = copy.deepcopy(np.asarray(child["E"][F_PATH]).ravel())
            pre["D"] = copy.deepcopy(np.asarray(child["D"][F_PATH]).ravel())
            pre["P"] = copy.deepcopy(np.asarray(child["P"][F_PATH]))
            if "S" in child:
                pre["S_shape"] = np.asarray(child["S"]).shape
            if isinstance(child.get("Q"), dict) and "O" in child["Q"]:
                oc = child["Q"]["O"]
                L = max(1, int(np.asarray(child.get("L", 1)).ravel()[0]))
                ol = oc[L - 1] if len(oc) >= L else None
                pre["QO_ncol"] = vb._vb_hierarchical_q_O_prev_ncols(
                    ol, ng=len(child.get("A", []))
                )
        out = orig(models, bundle, t_idx, M_row, recurse_partial, **kw)
        if t_idx == 1 and vb._VB_TIMING_DEPTH == 1:
            mi = int(np.asarray(M_row, dtype=np.int64).ravel()[0]) - 1
            child_upd = models[mi]["MDP"]
            if isinstance(child_upd, list):
                child_upd = child_upd[0]
            post["P"] = copy.deepcopy(np.asarray(child_upd["P"][F_PATH]))
            post["E"] = copy.deepcopy(np.asarray(child_upd["E"][F_PATH]).ravel())
        return out

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

    print("pre E", _peak(pre.get("E", [])))
    print("pre D", _peak(pre.get("D", [])))
    print("pre P cols", np.asarray(pre.get("P", np.zeros((0, 0)))).shape)
    if "P" in pre:
        for c in range(np.asarray(pre["P"]).shape[1]):
            print(f"  pre P(:,{c+1})", _peak(np.asarray(pre["P"])[:, c]))
    print("pre Q.O ncol", pre.get("QO_ncol"), "S_shape", pre.get("S_shape"))
    print("post P cols", np.asarray(post.get("P", np.zeros((0, 0)))).shape)
    if "P" in post:
        for c in range(np.asarray(post["P"]).shape[1]):
            print(f"  post P(:,{c+1})", _peak(np.asarray(post["P"])[:, c]))


if __name__ == "__main__":
    main()
