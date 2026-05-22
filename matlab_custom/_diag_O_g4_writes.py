"""Trace generate-path writes to O{m=1,g=4,t=2} (o_idx=3, t_idx=1)."""
from __future__ import annotations

import copy
import sys

import numpy as np

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_parents import spm_parents
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp


def main() -> None:
    captured: dict = {}

    def hook_g(models, bundle, t_idx, row):
        if t_idx == 1 and "bundle" not in captured:
            captured["models"] = models
            captured["bundle"] = bundle
        return orig_g(models, bundle, t_idx, row)

    orig_g = vb._vb_generate_outcomes_if_options_o
    vb._vb_generate_outcomes_if_options_o = hook_g
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb._vb_generate_outcomes_if_options_o = orig_g

    if "bundle" not in captured:
        print("capture failed")
        return
    models = captured["models"]
    bundle = captured["bundle"]
    mi = 0
    t_idx = 1
    md = models[mi]
    row = bundle["M_update"][t_idx, :]
    M_vec = np.asarray(row, dtype=np.int64).ravel()
    if 1 not in M_vec.tolist():
        print("model 1 not active at t=2", M_vec.tolist())
        return
    ID = bundle["ID"][mi]
    gpm = bundle["gp"][mi]
    O_shell = bundle["O"][mi]
    ng_loop = min(int(bundle["NG"][mi]), len(O_shell[mi]))
    s_col = np.asarray(md["s"][:, t_idx], dtype=np.float64).reshape(-1, 1)
    n_mat = np.asarray(md["n"], dtype=np.float64)
    if n_mat.ndim == 1:
        n_mat = n_mat.reshape(-1, 1)
    writes: list[tuple] = []
    o_idx = 3
    print("NG", bundle["NG"][mi], "ng_loop", ng_loop, "n[3,1]", float(n_mat[o_idx, t_idx]))
    for g_idx in range(ng_loop):
        g_1 = g_idx + 1
        j_p, i_ch = spm_parents(ID, g_1, s_col)
        i_vals = np.atleast_1d(np.asarray(i_ch, dtype=float)).ravel().tolist()
        has_o4 = (o_idx + 1) in [int(round(x)) for x in i_vals]
        print(f"g={g_1} i={i_vals} has_o4={has_o4}")
        if not has_o4:
            continue
        n_ot = float(n_mat[o_idx, t_idx])
        if n_ot > 0:
            path = "n>0"
        elif n_ot < 0:
            path = "n<0"
        else:
            Ag = np.asarray(vb._unwrap_gp_elem(gpm["A"][g_idx]), dtype=np.float64)
            j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
            ind = [
                int(round(float(md["s"][int(round(float(jx))) - 1, t_idx]))) - 1
                for jx in j_arr
            ]
            col = vb._vb_gp_A_outcome_column(Ag, ind).ravel()
            path = f"GP.A g={g_1} ind={ind} Ag_shape={Ag.shape}"
            writes.append((g_1, path, col.size, int(np.argmax(col) + 1), col[:4].tolist()))
    print("writes to o=4 from generate scan (g loop order):")
    for w in writes:
        print(w)
    if writes:
        print("last g", writes[-1][0])


if __name__ == "__main__":
    main()
