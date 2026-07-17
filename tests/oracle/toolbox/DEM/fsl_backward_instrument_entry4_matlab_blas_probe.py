#!/usr/bin/env python3
"""Query MATLAB BLAS/LAPACK build info via Engine (``eig.md`` §29)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    try:
        import matlab.engine
    except ImportError:
        print("[matlab blas probe] matlab.engine not available", file=sys.stderr)
        return 2

    eng = matlab.engine.start_matlab()
    try:
        payload = {
            "utc": datetime.now(timezone.utc).isoformat(),
            "blas": str(eng.eval("version('-blas')", nargout=1)),
            "lapack": str(eng.eval("version('-lapack')", nargout=1)),
            "release": str(eng.eval("version('-release')", nargout=1)),
            "eig_which": str(eng.eval("which('eig')", nargout=1)),
        }
    finally:
        eng.quit()

    out = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "DEMAtariIII_fsl_backward_entry4_matlab_blas_probe.json"
    )
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[matlab blas probe] wrote {out}")
    for k, v in payload.items():
        if k != "utc":
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
