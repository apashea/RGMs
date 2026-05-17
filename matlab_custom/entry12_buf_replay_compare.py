"""
MATLAB vs Python G{1} under the same vb_rand_buf replay (v5 lane).

MATLAB: entry12_dump fork, dumps off, rand.m shadow (no twister seed).
Python: spm_MDP_VB_XXX, dump_subentries=False, reuse_matlab_draws=True.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_OUT = ROOT / "matlab_custom" / "entry12_buf_replay_compare_results.json"


def _py_g1() -> dict:
    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    pdp = spm_MDP_VB_XXX(
        rdp,
        {},
        monitoring=False,
        dump_subentries=False,
        reuse_matlab_draws=True,
    )
    g1 = float(np.asarray(pdp["G"][0], dtype=np.float64).ravel()[0])
    return {"G1": g1, "lane": "python spm_MDP_VB_XXX dump_subentries=False reuse_matlab_draws=True"}


def _mat_g1(script: str) -> dict:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        mc = str(ROOT / "matlab_custom" / "entry12").replace("\\", "/")
        eng.eval(f"cd('{mc}');", nargout=0)
        eng.eval(f"out = {script};", nargout=0)
        g1 = float(np.asarray(eng.eval("out.G1", nargout=1)).reshape(-1)[0])
        used = int(np.asarray(eng.eval("out.draws_used", nargout=1)).reshape(-1)[0])
        unused = int(np.asarray(eng.eval("out.unused_draws", nargout=1)).reshape(-1)[0])
        k = int(np.asarray(eng.eval("out.K", nargout=1)).reshape(-1)[0])
        return {
            "G1": g1,
            "K": k,
            "draws_used": used,
            "unused_draws": unused,
            "lane": str(eng.eval("out.lane", nargout=1)),
        }
    finally:
        eng.quit()


def main() -> None:
    py = _py_g1()
    results: dict = {"python": py}
    for script in ("entry12_VB_matlab_src_buf_replay", "entry12_VB_matlab_buf_replay"):
        try:
            results[script] = _mat_g1(script)
        except Exception as e:
            results[script] = {"error": str(e)}
    canonical_g1 = -32.4054651081035  # rgms_canonical 12F MAT reference
    mat_src = results.get("entry12_VB_matlab_src_buf_replay", {})
    g_mat = mat_src.get("G1") if isinstance(mat_src, dict) else None
    out = {
        **results,
        "canonical_mat_12F_G1": canonical_g1,
        "delta_canonical_minus_py": float(canonical_g1 - py["G1"]),
    }
    if isinstance(g_mat, (int, float)):
        out["delta_mat_src_replay_minus_py"] = float(g_mat - py["G1"])
        out["delta_canonical_minus_mat_src_replay"] = float(canonical_g1 - g_mat)
    _OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"wrote {_OUT}")


if __name__ == "__main__":
    main()
