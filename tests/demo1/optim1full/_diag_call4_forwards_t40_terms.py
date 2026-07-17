#!/usr/bin/env python3
"""Phase B — fidelity ledger call4 VB with RGMS_OPTIM1FULL_PROBE_FORWARDS_T=41.

Dumps per-policy G term stages to matlab_custom/optim1full_call4_forwards_t40_terms.json
(name keeps historical 't40' = 0-based cell index; probe uses MATLAB t=41).
"""
from __future__ import annotations

import copy
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    # MATLAB 1-based timestep of diverge (PDP.G cell index 40).
    os.environ["RGMS_OPTIM1FULL_PROBE_FORWARDS_T"] = "41"

    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb_mod
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_call4_rdp_pkl,
        optim1full_plot_fence_matlab_pdp_mat,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        spm_mdp_vb_xxx_with_ledger_segment_reuse,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_mat_pdp_for_value_assert

    out_json = _REPO / "matlab_custom" / "optim1full_call4_forwards_t40_terms.json"
    report = _REPO / "matlab_custom" / "optim1full_call4_forwards_t40_terms_diag.txt"
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        lines.append(msg)

    with optim1full_call4_rdp_pkl().open("rb") as f:
        rdp = pickle.load(f)["rdp"]
    buf, manifest = load_validated_optim1full_ledger()
    seg = manifest.segment("vb_call4")
    log(f"probe MATLAB t={os.environ['RGMS_OPTIM1FULL_PROBE_FORWARDS_T']} lane=fidelity k={seg.k}")

    vb_mod._OPTIM1FULL_FORWARDS_T_PROBE = None
    pdp = spm_mdp_vb_xxx_with_ledger_segment_reuse(
        copy.deepcopy(rdp),
        buf,
        start=seg.start,
        k=seg.k,
        extra_vb_kwargs={"monitoring": False},
        vb_lane="fidelity",
    )
    probe = vb_mod._OPTIM1FULL_FORWARDS_T_PROBE
    if not isinstance(probe, dict) or not probe.get("policies"):
        log("FAIL: probe dict empty — env gate did not fire")
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 2

    mat_raw = _load_matlab_pdp(optim1full_plot_fence_matlab_pdp_mat("dem_with_compression_rgb"))
    mat_cmp = entry12_mat_pdp_for_value_assert(copy.deepcopy(mat_raw))
    g_mat_cell = mat_cmp["G"]
    if isinstance(g_mat_cell, list):
        g_mat = np.squeeze(np.asarray(g_mat_cell[40], dtype=float)).ravel()
    else:
        g_mat = np.squeeze(np.asarray(g_mat_cell, dtype=float))[40].ravel()

    g_py_store = pdp.get("G")
    if isinstance(g_py_store, list):
        g_py = np.squeeze(np.asarray(g_py_store[40], dtype=float)).ravel()
    else:
        g_py = np.squeeze(np.asarray(g_py_store, dtype=float))[40].ravel()

    probe["matlab_G_cell40"] = g_mat.tolist()
    probe["python_stored_G_cell40"] = g_py.tolist()
    probe["G_final_vs_matlab"] = (np.asarray(probe.get("G_final"), float).ravel()[:4] - g_mat[:4]).tolist()

    log(f"N={probe.get('N')} T={probe.get('T')} recursive={probe.get('recursive')}")
    log(f"G_final={probe.get('G_final')}")
    log(f"matlab_G_cell40={g_mat.tolist()}")
    log(f"python_stored_G_cell40={g_py.tolist()}")
    log("--- per-policy stages (scalar G[:,0] after select usually) ---")
    for pol in probe["policies"]:
        k = pol["k"]
        stages = {name: (v[0] if isinstance(v, list) and v else v) for name, v in pol.get("stages", {}).items()}
        log(
            f"  k={k} ih_sum={pol.get('ih_sum')} iI_sum={pol.get('iI_sum')} "
            f"g_risk={pol.get('g_risk')} rec={pol.get('recursive_efe_added')} stages={stages}"
        )

    # Stage-wise first diverge between policies vs identifying which stage differs most from mat
    log("--- stage after_outcomes vs after_recursive (policy0 vs policy1) ---")
    p0, p1 = probe["policies"][0], probe["policies"][1]
    for st in ("after_iH", "after_iI", "after_risk", "after_outcomes", "after_recursive"):
        a = p0.get("stages", {}).get(st)
        b = p1.get("stages", {}).get(st)
        if a is None or b is None:
            log(f"  {st}: missing")
            continue
        log(f"  {st}: k0={a} k1={b} d0_1={np.asarray(a,float)-np.asarray(b,float)}")

    out_json.write_text(json.dumps(probe, indent=2), encoding="utf-8")
    log(f"wrote {out_json}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
