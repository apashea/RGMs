"""MATLAB Engine: H init branch and id.iH proxy on FSL RDP."""
from __future__ import annotations

import matlab.engine

PATHS = (
    r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
    r"C:\Users\andre\.cursor\Atari_spm_dependencies",
    r"C:\Users\andre\.cursor\RGMs\matlab_src\toolbox\DEM",
)
MAT = r"C:/Users/andre/.cursor/RGMs/tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat"


def main() -> None:
    eng = matlab.engine.start_matlab()
    try:
        for p in PATHS:
            eng.addpath(p, nargout=0)
        eng.eval(f"load('{MAT}');", nargout=0)
        eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
        print("numel(rdp)", eng.eval("numel(rdp)", nargout=1))
        print("size(rdp)", eng.eval("size(rdp)", nargout=1))
        print("isfield(rdp,'H')", eng.eval("isfield(rdp,'H')", nargout=1))
        print("all(isfield(rdp,'H'))", eng.eval("double(all(isfield(rdp,'H')))", nargout=1))
        print("isfield(rdp,'h')", eng.eval("double(isfield(rdp,'h'))", nargout=1))
        print("numel(rdp.H{1})", eng.eval("numel(rdp.H{1})", nargout=1))
        print("nnz(rdp.H{1})", eng.eval("nnz(rdp.H{1})", nargout=1))
        print("issparse(rdp.H{1})", eng.eval("double(issparse(rdp.H{1}))", nargout=1))
        eng.eval(
            "m=1; f=1; "
            "if isfield(rdp,'h'), qh=rdp.h{f}; "
            "elseif isfield(rdp,'H'), qh=rdp.H{f}*512; "
            "else, qh=[]; end; "
            "Hn=spm_norm(qh);",
            nargout=0,
        )
        print("numel(Hn)", eng.eval("numel(Hn)", nargout=1))
        print("id_iH", eng.eval("find(arrayfun(@(ff) numel(Hn),1))", nargout=1))
    finally:
        eng.quit()


if __name__ == "__main__":
    main()
