"""MATLAB: after checkX, inspect H / id.iH init path (no full VB)."""
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
    "isfield(RDP,'H')",
    "isfield(RDP,'h')",
    "isfield(rdp,'H')",
    "isfield(rdp,'h')",
    "numel(rdp.H{1})",
    "size(rdp.H{1})",
]:
    try:
        print(expr, eng.eval(expr, nargout=1))
    except Exception as e:
        print(expr, "ERR", e)
eng.quit()
