#!/usr/bin/env python3
"""W2 diagnostic — count ``vb_optim_deepcopy`` stdlib fallbacks on one VB run.

Usage::

    python tests/demo1/optim1full/optim1full_vb_deepcopy_audit.py \\
        --tag rgms_atari_optim1full_call4 --lane optim
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL4_TAG,
    )
    from tests.demo1.optim1full.optim1full_vb_optim_equivalence import (
        _configure_entry12_fixture_env,
        _load_tag_rdp_and_buf,
        _run_vb_tag_lane,
    )
    from python_src.optimized.toolbox.DEM import vb_optim_deepcopy as _vbo

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", default=ENTRY12_OPTIM1FULL_CALL4_TAG)
    p.add_argument("--lane", choices=("fidelity", "optim"), default="optim")
    args = p.parse_args(argv)

    counts = {"stdlib_deepcopy": 0, "vb_optim_deepcopy": 0, "fallback_types": {}}
    orig_stdlib = copy.deepcopy
    orig_vb = _vbo.vb_optim_deepcopy

    def _counting_stdlib(obj, memo=None):
        counts["stdlib_deepcopy"] += 1
        return orig_stdlib(obj, memo)

    def _counting_vb(obj, memo=None):
        counts["vb_optim_deepcopy"] += 1
        return orig_vb(obj, memo)

    def _counting_vb_with_fallback_types(obj, memo=None):
        counts["vb_optim_deepcopy"] += 1
        if memo is None:
            memo = {}
        oid = id(obj)
        if oid in memo:
            return memo[oid]
        import numpy as np
        from scipy import sparse as sp

        if isinstance(obj, np.ndarray):
            return np.array(obj, dtype=obj.dtype, copy=True, order="K")
        if isinstance(obj, np.generic):
            return obj.item() if obj.ndim == 0 else np.array(obj, copy=True)
        if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
            return obj
        if sp.issparse(obj):
            return obj.copy()
        if isinstance(obj, dict):
            out = {}
            memo[oid] = out
            for key, val in obj.items():
                out[key] = _counting_vb_with_fallback_types(val, memo)
            return out
        if isinstance(obj, list):
            out_list = []
            memo[oid] = out_list
            for item in obj:
                out_list.append(_counting_vb_with_fallback_types(item, memo))
            return out_list
        if isinstance(obj, tuple):
            out_t = tuple(_counting_vb_with_fallback_types(item, memo) for item in obj)
            memo[oid] = out_t
            return out_t
        tname = f"{type(obj).__module__}.{type(obj).__qualname__}"
        counts["fallback_types"][tname] = counts["fallback_types"].get(tname, 0) + 1
        return orig_stdlib(obj, memo)

    tag = str(args.tag).strip()
    _configure_entry12_fixture_env(tag)
    rdp, _buf, k = _load_tag_rdp_and_buf(tag)

    copy.deepcopy = _counting_vb_with_fallback_types  # type: ignore[assignment]
    import python_src.toolbox.DEM.spm_MDP_VB_XXX as _vb_mod

    _vb_mod.copy.deepcopy = _counting_vb_with_fallback_types  # type: ignore[attr-defined]

    # Optim lane runs via dispatch → run_optim_vb (no patch layer since 4-X-1).
    t0 = time.perf_counter()
    if str(args.lane) == "optim":
        copy.deepcopy = _counting_vb_with_fallback_types  # type: ignore[assignment]
        _vb_mod.copy.deepcopy = _counting_vb_with_fallback_types  # type: ignore[attr-defined]
        _run_vb_tag_lane(rdp, lane="optim")
    else:
        copy.deepcopy = _counting_stdlib  # type: ignore[assignment]
        _vb_mod.copy.deepcopy = _counting_stdlib  # type: ignore[attr-defined]
        _run_vb_tag_lane(rdp, lane="fidelity")
    wall = time.perf_counter() - t0

    print(
        f"[optim1full_vb_deepcopy_audit] tag={tag!r} lane={args.lane!r} k={k} "
        f"wall_s={wall:.3f} vb_optim_deepcopy_calls={counts['vb_optim_deepcopy']} "
        f"stdlib_deepcopy_calls={counts['stdlib_deepcopy']} "
        f"fallback_types={dict(sorted(counts['fallback_types'].items(), key=lambda kv: -kv[1]))}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
