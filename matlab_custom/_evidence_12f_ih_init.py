"""Compare PY vs MATLAB H init and id.iH proxy (no full VB)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp


def _py_init() -> None:
    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    models = vb._vb_models_after_checkx(rdp)
    nm = len(models)
    bundle = vb._vb_tensors_through_H(models, nm, float(models[0]["T"]))
    id0 = bundle["id"][0]
    H0 = bundle["H"][0][0]
    print("PY id.iH", id0.get("iH"))
    print("PY H[0][0] shape", np.asarray(H0).shape, "nnz", np.count_nonzero(np.asarray(H0)))


def _mat_init() -> None:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    paths = [
        r"C:\Users\andre\Documents\MATLAB\spm-main",
        r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
        r"C:\Users\andre\.cursor\Atari_spm_dependencies",
        str(ROOT / "matlab_src" / "toolbox" / "DEM"),
    ]
    try:
        for p in paths:
            eng.addpath(p, nargout=0)
        mat = str(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat")
        eng.eval(f"load('{mat.replace(chr(92), '/')}');", nargout=0)
        eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
        eng.eval(
            "m=1; f=1; "
            "if isfield(rdp,'h'), qh=rdp.h{f}; "
            "elseif isfield(rdp,'H'), qh=rdp.H{f}*512; "
            "else, qh=[]; end; "
            "Hn=spm_norm(qh);",
            nargout=0,
        )
        print("MAT numel(Hn)", eng.eval("numel(Hn)", nargout=1))
        print("MAT id_iH proxy", eng.eval("find(arrayfun(@(ff) numel(Hn),1))", nargout=1))
        print("MAT nnz(Hn)", eng.eval("nnz(Hn)", nargout=1))
    finally:
        eng.quit()


def main() -> None:
    print("=== Python ===")
    _py_init()
    print("=== MATLAB ===")
    _mat_init()


if __name__ == "__main__":
    main()
