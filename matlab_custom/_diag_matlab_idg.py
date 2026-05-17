import matlab.engine

eng = matlab.engine.start_matlab()
for p in (
    r"C:\Users\andre\Documents\MATLAB\spm-main",
    r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
    r"C:\Users\andre\.cursor\RGMs\matlab_src\toolbox\DEM",
):
    eng.addpath(p, nargout=0)
mat_path = r"C:/Users/andre/.cursor/RGMs/tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat"
eng.eval(f"load('{mat_path}');", nargout=0)
eng.eval("rdp = RDP;", nargout=0)
eng.eval("rdp = spm_MDP_checkX(rdp);", nargout=0)
n = float(eng.eval("numel(rdp.id.g)", nargout=1))
print("matlab numel(rdp.id.g)", n)
if n >= 1:
    sz = eng.eval("size(rdp.id.g{1})", nargout=1)
    print("matlab size(rdp.id.g{1})", sz)
h1 = float(eng.eval("numel(rdp.H{1})", nargout=1))
print("matlab numel(rdp.H{1})", h1)
