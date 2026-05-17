"""MATLAB rdp.id.hid / iH after checkX."""
import matlab.engine
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
eng = matlab.engine.start_matlab()
for p in (
    r"C:\Users\andre\Documents\MATLAB\spm-main",
    r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
    str(ROOT / "matlab_src" / "toolbox" / "DEM"),
):
    eng.addpath(p, nargout=0)
mat = str(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_rdp.mat").replace("\\", "/")
eng.eval(f"load('{mat}');", nargout=0)
eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
for expr in [
    "size(rdp.id.hid)",
    "size(rdp.id.cid)",
    "rdp.id.iH",
    "any(rdp.id.hid(:))",
]:
    try:
        print(expr, eng.eval(expr, nargout=1))
    except Exception as e:
        print(expr, "ERR", e)
eng.quit()
