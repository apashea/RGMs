"""One-off: compare spm_VBX F on entry12_12f_vbx_t2_inputs.mat (py vs mat workspace)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.spm_VBX import spm_VBX

mat = loadmat(ROOT / "matlab_custom" / "entry12_12f_vbx_t2_inputs.mat", simplify_cells=True)
O = [np.asarray(mat["Orow"][i], dtype=np.float64) for i in range(len(mat["Orow"]))]
P = [np.asarray(mat["Prow"][i], dtype=np.float64) for i in range(len(mat["Prow"]))]
A = [np.asarray(mat["Arow"][i], dtype=np.float64) for i in range(len(mat["Arow"]))]
idm = dict(mat["idm"])
g = idm.get("g")
if isinstance(g, np.ndarray) and g.dtype == object:
    idm["g"] = [np.asarray(x).ravel().tolist() for x in g.ravel()]

_, F_py = spm_VBX(O, P, A, idm)
print("F_python", float(F_py))
