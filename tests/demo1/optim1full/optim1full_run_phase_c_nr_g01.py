#!/usr/bin/env python3
"""OPTIM1FULL Phase C — full Entry **12** chain on ledger-context NR game **1**.

Steps: MATLAB **1b** capture → Python **1a** K verify → script **3** → draw audit → script **4**.

Does **not** re-capture the Model **B** ledger. Live ``spm_MDP_VB_XXX.py`` edits only if script **4**
reports causal **12D–12F** red (compare to backup ``spm_MDP_VB_XXX_bkp_2026-06-24.py``).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_TAG = "rgms_atari_optim1full_nr_g01"
_PREFLIGHT = _REPO / "tests" / "oracle" / "toolbox" / "DEM" / "entry12_preflight_vb_rand_k.py"
_CAPTURE = _REPO / "tests" / "demo1" / "optim1full" / "optim1full_capture_nr_g01_ledger.py"


def main() -> int:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_NR_G01_TAG,
    )
    from tests.demo1.optim1full.optim1full_parity_phases import run_entry12_vb_gate
    from tests.demo1.optim1full.optim1full_rng_authority import optim1full_entry12_subprocess_env

    if ENTRY12_OPTIM1FULL_NR_G01_TAG != _TAG:
        raise RuntimeError(f"tag constant drift: {ENTRY12_OPTIM1FULL_NR_G01_TAG!r} != {_TAG!r}")

    t0 = time.perf_counter()
    print(f"[optim1full Phase C] MATLAB 1b capture tag={_TAG!r}", file=sys.stderr, flush=True)
    subprocess.run([sys.executable, str(_CAPTURE)], cwd=str(_REPO), check=True)

    env = optim1full_entry12_subprocess_env(_TAG)
    print(f"[optim1full Phase C] Python 1a K verify tag={_TAG!r}", file=sys.stderr, flush=True)
    subprocess.run([sys.executable, str(_PREFLIGHT)], cwd=str(_REPO), env=env, check=True)

    wall = run_entry12_vb_gate(_TAG, label="OPTIM1FULL Phase C NR g01 ledger")
    print(
        f"[optim1full Phase C] PASS tag={_TAG!r} total_wall_s={time.perf_counter() - t0:.3f} "
        f"gate_wall_s={wall:.3f}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
