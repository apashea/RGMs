"""Run MATLAB spm_induction on Python-frozen live inputs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        for p in (
            r"C:\Users\andre\Documents\MATLAB\spm-main",
            r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
            str(ROOT / "matlab_src" / "toolbox" / "DEM"),
            str(ROOT / "matlab_custom"),
        ):
            eng.addpath(p, nargout=0)
        mc = str(ROOT / "matlab_custom").replace("\\", "/")
        eng.eval(f"cd('{mc}');", nargout=0)
        eng.eval("entry12_12f_induction_compare;", nargout=0)
    finally:
        eng.quit()


if __name__ == "__main__":
    main()
