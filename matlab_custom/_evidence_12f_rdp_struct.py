"""MATLAB checks on XXX_12_rdp after checkX."""
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
for stmt in (
    "numel(rdp)",
    "size(rdp)",
    "isfield(rdp,'H')",
    "isfield(rdp(1),'H')",
    "isfield(rdp(1),'h')",
    "numel(rdp.H{1})",
):
    print(stmt, eng.eval(stmt, nargout=1))
eng.quit()
