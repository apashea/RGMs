#!/usr/bin/env python3
"""DEPRECATED for routine Entry 11 sign-off — runs full ``entry_stop=11`` (~30+ min).

Use ``fsl_backward_run_entry11_isolated.py`` + MATLAB ``dump_MDP_pre_entry11.m`` instead.

FSL backward 1a — count Python scalar ``rand()`` draws through Entry 11.

Writes ``fixtures/fsl_backward_entry11_K_py.mat``. Exit **0** only if ``K_py == K_11``
from FSL backward **1b** (``dem_atari_rand_buf_through_entry11.mat``).

See ``Atari_example.md`` § **FSL backward validation (Entry 11 → 1)**.
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
        fsl_backward_count_native_draws,
        fsl_entry11_driver_env,
        fixtures_dir,
        load_dem_atari_rand_buf,
    )

    with fsl_entry11_driver_env(deadline_minutes="60"):
        with fsl_backward_count_native_draws() as ctr:
            run_dem_atariiii(entry_stop=11)
        k_py = int(ctr[0])

    out = fixtures_dir() / "fsl_backward_entry11_K_py.mat"
    out.parent.mkdir(parents=True, exist_ok=True)
    savemat(str(out), {"K_py": np.array([[float(k_py)]], dtype=np.float64)})
    print(f"[FSL backward 1a] K_py={k_py}", file=sys.stderr)
    print(f"[FSL backward 1a] wrote {out}", file=sys.stderr)

    _, k_mat = load_dem_atari_rand_buf()
    if k_mat == k_py:
        print("[FSL backward 1a] K_py matches K_11 from FSL backward 1b", file=sys.stderr)
        return 0
    print(
        f"[FSL backward 1a] FAIL: K_py ({k_py}) != K_11 ({k_mat}) — "
        "draw sites differ between MATLAB ledger log and Python path",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
