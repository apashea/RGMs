"""Compare MATLAB vs Python H / id.iH and 12F fixture G/v."""
from __future__ import annotations

import copy
import os
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py


def _py_h_branch(mdp_in: dict) -> None:
    mdp_checked = spm_MDP_checkX(copy.deepcopy(mdp_in))
    models = vb._vb_models_after_checkx(mdp_checked)
    md = models[0]
    print("PY models[0] has h,H:", "h" in md, "H" in md)
    nf = 1
    if "h" in md:
        qh = md["h"][0]
        qh = qh[0] if isinstance(qh, list) and len(qh) == 1 else qh
        print("  branch: lowercase h")
    elif "H" in md:
        Hg = vb._vb_mdp_factor_field(md, "H", 0)
        qh = vb._vb_as_float64_array(Hg) * 512.0
        print("  branch: uppercase H")
    else:
        qh = np.zeros((0, 0))
        print("  branch: empty")
    Hn = vb._spm_norm(qh) if np.asarray(qh).size else np.zeros((0, 0), dtype=np.float64)
    print("  qh numel", np.asarray(qh).size, "H norm numel", np.asarray(Hn).size)
    ih = vb._numel_like_matlab(Hn)
    print("  would set id.iH", np.array([1], dtype=np.int64) if ih else np.array([], dtype=np.int64))


def _mat_h_branch() -> None:
    import matlab.engine

    mat_path = ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat"
    eng = matlab.engine.start_matlab()
    try:
        for p in (
            ROOT / "matlab_src" / "toolbox" / "DEM",
            Path(r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM"),
        ):
            eng.addpath(str(p), nargout=0)
        eng.eval(f"load('{mat_path.as_posix()}');", nargout=0)
        eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
        for line in (
            "disp(['MAT isfield(rdp,''h'')=' num2str(isfield(rdp,''h''))]);",
            "disp(['MAT isfield(rdp,''H'')=' num2str(isfield(rdp,''H''))]);",
            "m=1; f=1;",
            "if isfield(rdp,'h'), disp('MAT branch: lowercase h'); qh=rdp.h{f};",
            "elseif isfield(rdp,'H'), disp('MAT branch: uppercase H'); qh=rdp.H{f}*512;",
            "else, disp('MAT branch: empty'); qh=[]; end;",
            "Hn = spm_norm(qh);",
            "disp(['MAT qh numel=' num2str(numel(qh)) ' Hn numel=' num2str(numel(Hn))]);",
            "disp(['MAT numel(H{1}) for id.iH=' num2str(numel(Hn))]);",
        ):
            eng.eval(line, nargout=0)
    finally:
        eng.quit()


def _compare_12f_out_t1() -> None:
    mat_raw = load_entry12_subentry_mat(
        ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.mat"
    )
    mat_ws = mat_nested_to_py(mat_raw)
    py_ws = pickle.load(
        open(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_canonical_12F.pkl", "rb")
    )
    snap_m = mat_ws["out_t1"]
    snap_p = py_ws["out_t1"]
    if isinstance(snap_m, list) and snap_m:
        snap_m = snap_m[0]
    def _mdp1(mdp: object) -> dict:
        if isinstance(mdp, list) and mdp:
            mdp = mdp[0]
        if not isinstance(mdp, dict):
            raise TypeError(f"expected MDP dict, got {type(mdp).__name__}")
        return mdp

    for label, snap in (("MAT", snap_m), ("PY", snap_p)):
        mdp = _mdp1(snap["MDP"])
        g = mdp.get("G")
        print(f"{label} out_t1 MDP keys has H:", "H" in mdp, "h" in mdp)
        if isinstance(g, list) and g:
            print(f"  G[0] ravel[:4] = {np.asarray(g[0], dtype=np.float64).ravel()[:4]}")
        elif g is not None:
            print(f"  G = {np.asarray(g, dtype=np.float64).ravel()[:4]}")
    v_m = np.asarray(snap_m.get("v"), dtype=np.float64).ravel()
    v_p = np.asarray(snap_p.get("v"), dtype=np.float64).ravel()
    if v_m.size and v_p.size:
        print("v mat", v_m[0], "py", v_p[0], "diff", float(v_p[0] - v_m[0]))


def main() -> None:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

    print("=== H init branch (pre-VB) ===")
    _py_h_branch(_load_xxx12_rdp())
    if os.getenv("RGMS_RUN_MATLAB_DIAG"):
        try:
            _mat_h_branch()
        except Exception as exc:
            print("MATLAB branch check failed:", exc)
    else:
        print("(set RGMS_RUN_MATLAB_DIAG=1 for MATLAB)")
    print("\n=== 12F out_t1 G/v ===")
    _compare_12f_out_t1()


if __name__ == "__main__":
    main()
