"""MATLAB spm_log KL on Qf,Hf saved from Python forwards."""
import matlab.engine
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
npz = ROOT / "matlab_custom" / "_diag_12f_qf_hf.npz"
d = np.load(npz)
Qf = d["Qf"]
Hf = d["Hf"]
print("PY ih_term saved", float(d["ih_term"]))

eng = matlab.engine.start_matlab()
for p in (
    r"C:\Users\andre\Documents\MATLAB\spm-main",
    r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
):
    eng.addpath(p, nargout=0)
eng.workspace["Qf"] = matlab.double(Qf.reshape(-1, 1).tolist())
eng.workspace["Hf"] = matlab.double(Hf.reshape(-1, 1).tolist())
eng.eval("term = Qf'*(spm_log(Qf) - spm_log(Hf));", nargout=0)
term = float(eng.eval("term", nargout=1))
print("MAT term", term)
eng.quit()
