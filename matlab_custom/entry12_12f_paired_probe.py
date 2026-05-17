"""Step 1 plan: paired parent t=1 probe (Python replay + MATLAB entry12_dump)."""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp


def _run_python_probe() -> dict:
    vb._PROBE_12F_PARENT = None
    os.environ["RGMS_PROBE_12F_PARENT_T1"] = "1"
    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    pdp = vb.spm_MDP_VB_XXX(
        rdp, {}, monitoring=False, dump_subentries=False, reuse_matlab_draws=True
    )
    probe = vb._PROBE_12F_PARENT or {}
    import numpy as np

    g1 = float(np.asarray(pdp["G"][0], dtype=np.float64).ravel()[0])
    out = dict(probe)
    out["PDP_G1"] = g1
    return out


def _run_matlab_probe() -> dict:
    import matlab.engine
    import numpy as np

    eng = matlab.engine.start_matlab()
    try:
        for p in (
            r"C:\Users\andre\Documents\MATLAB\spm-main",
            r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
            str(ROOT / "matlab_src" / "toolbox" / "DEM"),
            str(ROOT / "matlab_custom" / "entry12"),
        ):
            eng.addpath(p, nargout=0)
        mat = str(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_rdp.mat").replace(
            "\\", "/"
        )
        eng.eval("global RGMS_PROBE_12F; RGMS_PROBE_12F = struct();", nargout=0)
        eng.eval(f"load('{mat}');", nargout=0)
        eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
        eng.eval(
            "pdp = spm_MDP_VB_XXX_entry12_dump(rdp, struct('monitoring', false, 'dump_subentries', false));",
            nargout=0,
        )
        g1 = float(np.asarray(eng.eval("pdp.G{1}(1)", nargout=1)).reshape(-1)[0])
        fields = [
            "G_before_iH",
            "ih_term",
            "G_after_iH",
            "spm_dot_R_Q",
            "G_after_dot",
        ]
        out: dict[str, float] = {"PDP_G1": g1}
        for f in fields:
            try:
                out[f] = float(eng.eval(f"RGMS_PROBE_12F.{f}", nargout=1))
            except Exception:
                out[f] = float("nan")
        return out
    finally:
        eng.quit()


def main() -> None:
    import numpy as np

    py = _run_python_probe()
    print("=== Python (rand replay) ===")
    print(json.dumps(py, indent=2))
    print("=== MATLAB (native RNG, entry12_dump) ===")
    mat = _run_matlab_probe()
    print(json.dumps(mat, indent=2))
    print("=== Delta (PY - MAT) ===")
    for k in sorted(set(py) | set(mat)):
        if k == "PDP_G1" or k in py and k in mat:
            try:
                d = float(py[k]) - float(mat[k])
                print(f"  {k}: {d:+.6f}")
            except (TypeError, KeyError):
                pass
    out_path = ROOT / "matlab_custom" / "entry12_12f_paired_probe_results.json"
    out_path.write_text(json.dumps({"python": py, "matlab": mat}, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
