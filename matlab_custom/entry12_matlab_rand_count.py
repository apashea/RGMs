"""Run entry12_matlab_count_rand_draws.m and write JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_OUT = ROOT / "matlab_custom" / "entry12_matlab_rand_count_results.json"


def main() -> None:
    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        mc = str(ROOT / "matlab_custom" / "entry12").replace("\\", "/")
        eng.eval(f"cd('{mc}');", nargout=0)
        eng.eval("out = entry12_matlab_count_rand_draws();", nargout=0)
        k = int(np.asarray(eng.eval("out.K_preflight", nargout=1)).reshape(-1)[0])
        nd = int(np.asarray(eng.eval("out.dump_subentries_true.rand_calls", nargout=1)).reshape(-1)[0])
        ns = int(np.asarray(eng.eval("out.dump_subentries_false.rand_calls", nargout=1)).reshape(-1)[0])
        g_dump = float(np.asarray(eng.eval("out.dump_subentries_true.G1", nargout=1)).reshape(-1)[0])
        g_src = float(np.asarray(eng.eval("out.dump_subentries_false.G1", nargout=1)).reshape(-1)[0])
        result = {
            "K_preflight": k,
            "matlab_dump_true_rand_calls": nd,
            "matlab_dump_false_rand_calls": ns,
            "delta_dump_minus_src": nd - ns,
            "delta_dump_minus_K": nd - k,
            "delta_src_minus_K": ns - k,
            "G1_dump_true": g_dump,
            "G1_dump_false": g_src,
        }
    finally:
        eng.quit()
    _OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {_OUT}")


if __name__ == "__main__":
    main()
