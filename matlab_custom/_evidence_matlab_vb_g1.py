"""MATLAB spm_MDP_VB_XXX on XXX_12_rdp (native RNG): read G{1} after VB."""
import matlab.engine
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
eng = matlab.engine.start_matlab()
paths = (
    r"C:\Users\andre\Documents\MATLAB\spm-main",
    r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
    str(ROOT / "matlab_src" / "toolbox" / "DEM"),
    str(ROOT / "matlab_custom" / "entry12"),
)
for p in paths:
    eng.addpath(p, nargout=0)
mat = str(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_rdp.mat").replace("\\", "/")
eng.eval(f"load('{mat}');", nargout=0)
eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
# Use instrumented dump entry (same as 12F capture) if on path
try:
    eng.eval("pdp = spm_MDP_VB_XXX_entry12_dump(rdp, struct('monitoring', false, 'dump_subentries', false));", nargout=0)
    which = "entry12_dump"
except Exception:
    eng.eval("pdp = spm_MDP_VB_XXX(rdp);", nargout=0)
    which = "matlab_src"
G1 = np.asarray(eng.eval("pdp.G{1}"), dtype=np.float64).ravel()
print("which", which, "G1[:6]", G1[:6])
try:
    iH = eng.eval("pdp.id.iH", nargout=1)
    print("pdp.id.iH", iH)
except Exception as e:
    print("id.iH unavailable", e)
eng.quit()
