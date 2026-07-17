#!/usr/bin/env python3
"""Re-save XXX_matlab-6 MATLAB PDP from v7.3 to v7 for scipy.io.loadmat."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
import matlab.engine

TAG = "rgms_atari_optim1full_call4"
src = _REPO / "logs" / f"xxx_matlab_6_{TAG}_matlab_pdp.mat"
dst = _REPO / "logs" / f"xxx_matlab_6_{TAG}_matlab_pdp_v7.mat"


def main() -> int:
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        eng.workspace["src"] = str(src)
        eng.workspace["dst"] = str(dst)
        eng.eval("S=load(src); PDP=S.PDP; meta=S.meta; save(dst,'PDP','meta','-v7');", nargout=0)
        print(f"[XM6] wrote {dst}", flush=True)
    finally:
        eng.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
