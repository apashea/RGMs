#!/usr/bin/env python3
"""FSL backward Entry 2 preflight — count Python ``rand()`` draws through ``entry_stop=2``.

Writes ``fixtures/fsl_backward_entry2_K_py.mat``.

See ``Atari_example.md`` § **Entry 2 — FSL backward sign-off lane**.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from scipy.io import savemat

    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        entry2_k_py_mat,
        fsl_backward_count_native_draws,
        fsl_entry2_driver_env,
    )

    with fsl_entry2_driver_env(deadline_minutes="15"):
        with fsl_backward_count_native_draws() as ctr:
            run_dem_atariiii(entry_stop=2)
        k_py = int(ctr[0])

    out = entry2_k_py_mat()
    out.parent.mkdir(parents=True, exist_ok=True)
    savemat(str(out), {"K_py": np.array([[float(k_py)]], dtype=np.float64)})
    print(f"[FSL backward Entry 2 preflight] K_py={k_py}", file=sys.stderr)
    print(f"[FSL backward Entry 2 preflight] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
