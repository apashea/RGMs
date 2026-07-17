#!/usr/bin/env python3
"""One-shot C4c-2 audit: classify vb_contract_optim dot fast-path vs spm_dot fallback.

Runs one full optim-wall (XXX_comp lane) with monkeypatched counters.
Does not modify Tier A source files.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import python_src.optimized.toolbox.DEM.vb_contract_optim as _vc


def _dense_ndarray(x: Any) -> bool:
    import numpy as np

    return isinstance(x, np.ndarray) and x.dtype != object


def _install_counters() -> dict[str, Counter[str]]:
    stats: dict[str, Counter[str]] = {
        "forwards_dot_A_qj": Counter(),
        "forwards_dot_R_qcells": Counter(),
        "forwards_dot_vec_match": Counter(),
    }
    orig_a = _vc.forwards_dot_A_qj
    orig_r = _vc.forwards_dot_R_qcells
    orig_v = _vc.forwards_dot_vec_match
    orig_chain = _vc.forwards_dot_cell_chain

    def _classify_a(a: Any, qj: list[Any]) -> str:
        if not _dense_ndarray(a):
            return "a_not_dense"
        for q in qj:
            if not _dense_ndarray(q):
                return "q_not_dense"
        try:
            orig_chain(a, qj)
            return "native_cell_chain"
        except (ValueError, IndexError):
            return "axis_mismatch_fallback"

    def _wrap_a(a: Any, qj: list[Any]) -> Any:
        reason = _classify_a(a, qj)
        stats["forwards_dot_A_qj"][reason] += 1
        return orig_a(a, qj)

    def _wrap_r(r: Any, q_cells: list[Any]) -> Any:
        if not _dense_ndarray(r):
            stats["forwards_dot_R_qcells"]["r_not_dense"] += 1
        else:
            for q in q_cells:
                if not _dense_ndarray(q):
                    stats["forwards_dot_R_qcells"]["q_not_dense"] += 1
                    break
            else:
                try:
                    orig_chain(r, q_cells)
                    stats["forwards_dot_R_qcells"]["native_cell_chain"] += 1
                except (ValueError, IndexError):
                    stats["forwards_dot_R_qcells"]["axis_mismatch_fallback"] += 1
        return orig_r(r, q_cells)

    def _wrap_v(x: Any, q: Any) -> Any:
        import numpy as np

        if not _dense_ndarray(x) or not _dense_ndarray(q):
            stats["forwards_dot_vec_match"]["not_dense"] += 1
        else:
            xa = np.asarray(x, dtype=np.float64)
            qa = q.reshape(-1, order="F") if isinstance(q, np.ndarray) else np.asarray(q).reshape(-1)
            if qa.size == 1:
                stats["forwards_dot_vec_match"]["scalar"] += 1
            else:
                matches = np.where(np.array(xa.shape, dtype=np.int64) == int(qa.size))[0]
                if matches.size == 0:
                    stats["forwards_dot_vec_match"]["no_dim_match_fallback"] += 1
                else:
                    stats["forwards_dot_vec_match"]["native_tensordot"] += 1
        return orig_v(x, q)

    _vc.forwards_dot_A_qj = _wrap_a
    _vc.forwards_dot_R_qcells = _wrap_r
    _vc.forwards_dot_vec_match = _wrap_v
    return stats


def main() -> int:
    stats = _install_counters()
    from tests.demo1.optim1full import xxx_comp_call4 as xc

    print("[C4c-2 audit] running one optim-wall with fallback counters...", flush=True)
    payload = xc.run_optim_wall(xc.TAG)
    wall = float(payload["optim_wall_s"])
    print(f"[C4c-2 audit] optim_wall_s={wall:.6f}", flush=True)
    print("--- forwards_dot_A_qj ---", flush=True)
    for k, v in stats["forwards_dot_A_qj"].most_common():
        print(f"  {k}: {v}", flush=True)
    print("--- forwards_dot_R_qcells ---", flush=True)
    for k, v in stats["forwards_dot_R_qcells"].most_common():
        print(f"  {k}: {v}", flush=True)
    print("--- forwards_dot_vec_match ---", flush=True)
    for k, v in stats["forwards_dot_vec_match"].most_common():
        print(f"  {k}: {v}", flush=True)
    a_total = sum(stats["forwards_dot_A_qj"].values())
    a_native = stats["forwards_dot_A_qj"].get("native_cell_chain", 0)
    if a_total:
        print(
            f"[C4c-2 audit] A_qj native_rate={a_native / a_total:.3f} ({a_native}/{a_total})",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
