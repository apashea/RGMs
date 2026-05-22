#!/usr/bin/env python3
"""Preflight: count scalar ``numpy.random.rand()`` draws for Entry 12 VB oracle.

Writes ``fixtures/entry12_vb_rand_K.mat`` (variable ``K``) for
``DEMAtariIII_entry12_dump_all_subentries.m`` (script 1a of the four-script lane).

**Validation coherence:** ``K`` and ``vb_rand_buf`` are only meaningful when the full
chain runs together: **1a** (this script) → **1b** (MATLAB dump driver + fork) → **3**
(XXX 12) → **4** (Validation 12). Do not pair ``K`` from one preflight with ``.mat``/``.pkl``
from another run, tag, or capture script.

Count uses the same VB flags as Phase 1 oracle: ``OPTIONS={}``, ``monitoring=False``,
``dump_subentries=True``, ``reuse_matlab_draws=False``.

Run from repo root with ``conda activate rgms`` before script **1b**.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    default_entry12_vb_rand_k_mat_path,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp


def count_vb_rand_draws_on_rdp(rdp: dict[str, Any]) -> int:
    ctr = [0]
    real_rand = np.random.rand

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("count_vb_rand_draws: only scalar np.random.rand() supported")
        ctr[0] += 1
        return float(real_rand())

    with patch("numpy.random.rand", side_effect=shim):
        spm_MDP_VB_XXX(
            copy.deepcopy(rdp),
            {},
            monitoring=False,
            dump_subentries=True,
            reuse_matlab_draws=False,
        )
    return int(ctr[0])


def main() -> int:
    rdp = _load_xxx12_rdp()
    k = count_vb_rand_draws_on_rdp(rdp)
    out = default_entry12_vb_rand_k_mat_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    from scipy.io import savemat

    savemat(str(out), {"K": np.array([[float(k)]], dtype=np.float64)})
    print(f"[entry12 preflight] K={k}", file=sys.stderr)
    print(f"[entry12 preflight] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
