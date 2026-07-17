#!/usr/bin/env python3
"""One-shot audit: count sparse vs dense ``Bf`` paths in ``ind_backward_paths_into``."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import python_src.optimized.toolbox.DEM.vb_contract_optim as contract
import scipy.sparse as sp

_COUNTS = {"sparse": 0, "dense_blas": 0, "dense_rowslice": 0, "other": 0}
_orig = contract.ind_backward_paths_into


def _wrapped(pf_col, bf_prop, horizon_n, i_big, prev_f, next_f=None):
    if sp.issparse(bf_prop):
        _COUNTS["sparse"] += 1
    elif isinstance(bf_prop, contract.np.ndarray):
        nrows = int(i_big.shape[0])
        # mirror contract branch predicate on first step column
        prev = i_big[:, 0] if i_big.shape[1] > 0 else contract.np.zeros(0, dtype=bool)
        nnz = int(contract.np.count_nonzero(prev)) if prev.size else 0
        if nnz > max(nrows // 4, 48):
            _COUNTS["dense_blas"] += 1
        else:
            _COUNTS["dense_rowslice"] += 1
    else:
        _COUNTS["other"] += 1
    return _orig(pf_col, bf_prop, horizon_n, i_big, prev_f, next_f)


def main() -> int:
    from tests.demo1.optim1full.optim1full_vb_optim_equivalence import (
        _configure_entry12_fixture_env,
        _load_tag_rdp_and_buf,
        _run_vb_tag_lane,
    )
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready

    tag = "rgms_atari_optim1full_call4"
    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "0")
    _configure_entry12_fixture_env(tag)
    assert_entry12_vb_tag_ready(tag)
    rdp, _buf, k = _load_tag_rdp_and_buf(tag)
    contract.ind_backward_paths_into = _wrapped
    print(f"[backward_path_audit] tag={tag!r} k={k}", flush=True)
    _run_vb_tag_lane(rdp, lane="optim")
    contract.ind_backward_paths_into = _orig
    total = sum(_COUNTS.values())
    print(f"[backward_path_audit] calls={total} counts={_COUNTS}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
