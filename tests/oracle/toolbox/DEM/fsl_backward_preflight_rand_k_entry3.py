#!/usr/bin/env python3
"""FSL backward Entry 3 preflight — count Python ``rand()`` draws through ``entry_stop=3``.

Writes ``fixtures/fsl_backward_entry3_K_py.mat``. Exit **0** when ``K_py`` is recorded;
optional ``RGMS_FSL_ENTRY3_ASSERT_K_MATLAB=1`` compares to ``K_3`` in the rand-buf fixture
(only when that scalar is present from an extended **1b** capture).

See ``Atari_example.md`` § **Entry 3 — FSL backward sign-off lane**.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _assert_k_matlab_enabled() -> bool:
    import os

    return str(os.getenv("RGMS_FSL_ENTRY3_ASSERT_K_MATLAB", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def main() -> int:
    from scipy.io import loadmat, savemat

    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        default_rand_buf_mat,
        entry3_k_py_mat,
        fsl_backward_count_native_draws,
        fsl_entry3_driver_env,
    )

    with fsl_entry3_driver_env(deadline_minutes="45"):
        with fsl_backward_count_native_draws() as ctr:
            run_dem_atariiii(entry_stop=3)
        k_py = int(ctr[0])

    out = entry3_k_py_mat()
    out.parent.mkdir(parents=True, exist_ok=True)
    savemat(str(out), {"K_py": np.array([[float(k_py)]], dtype=np.float64)})
    print(f"[FSL backward Entry 3 preflight] K_py={k_py}", file=sys.stderr)
    print(f"[FSL backward Entry 3 preflight] wrote {out}", file=sys.stderr)

    if _assert_k_matlab_enabled():
        mat_p = default_rand_buf_mat()
        raw = loadmat(str(mat_p))
        if "K_3" not in raw:
            print(
                f"[FSL backward Entry 3 preflight] WARN: {mat_p} has no K_3 — "
                "skip MATLAB K assert (extend capture_dem_atari_rand_buf for K_3)",
                file=sys.stderr,
            )
            return 0
        k_mat = int(np.asarray(raw["K_3"], dtype=np.float64).reshape(-1)[0])
        if k_mat != k_py:
            print(
                f"[FSL backward Entry 3 preflight] FAIL: K_py ({k_py}) != K_3 ({k_mat})",
                file=sys.stderr,
            )
            return 1
        print("[FSL backward Entry 3 preflight] K_py matches K_3 from 1b", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
