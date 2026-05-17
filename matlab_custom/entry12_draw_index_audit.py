"""
Draw-index audit for Entry 12 Phase 1 (v5 ``vb_rand_buf`` replay).

Records scalar ``np.random.rand()`` consumption through parent ``t=1`` ``spm_forwards``
under ``reuse_matlab_draws=True``. Does **not** set NumPy/MATLAB seeds; replay injects
MATLAB ``rand(K,1)`` scalars directly (twister alignment is irrelevant for replay parity).

Coherence checks:
- total draws == K (no unused / no early exhaust)
- ``spm_sample`` call count replay vs native (same code path)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.entry12_matlab_capture import default_entry12_vb_matlab_rand_buf_mat_path
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_load_matlab_rand_buf, spm_MDP_VB_XXX
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_OUT = ROOT / "matlab_custom" / "entry12_draw_index_audit_results.json"


class _CountingReplay:
    """Wrap ``_VbMatlabRandReplay`` and expose draw index + history."""

    def __init__(self, buf: np.ndarray) -> None:
        self._buf = np.asarray(buf, dtype=np.float64).ravel(order="F")
        self._idx = 0
        self._orig = np.random.rand
        self.history: list[tuple[int, float]] = []

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("only scalar np.random.rand() supported")
        if self._idx >= self._buf.size:
            raise RuntimeError(f"exhausted buf at index {self._idx} (K={self._buf.size})")
        v = float(self._buf[self._idx])
        self.history.append((self._idx, v))
        self._idx += 1
        return v

    @property
    def index(self) -> int:
        return self._idx

    def __enter__(self) -> _CountingReplay:
        np.random.rand = self._shim  # type: ignore[method-assign]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        np.random.rand = self._orig  # type: ignore[method-assign]


def _run_replay_with_hook() -> dict[str, Any]:
    buf = _vb_load_matlab_rand_buf()
    k = int(buf.size)
    audit: dict[str, Any] = {"K": k, "buf_path": str(default_entry12_vb_matlab_rand_buf_mat_path())}
    sample_log: list[dict[str, Any]] = []
    orig_sample = vb._spm_sample

    def _logged_sample(p: Any) -> int:
        i0 = replay.index
        out = int(orig_sample(p))
        kind = "logical"
        k_mask = 0
        if isinstance(p, np.ndarray) and p.dtype == bool:
            k_mask = int(np.count_nonzero(p))
        else:
            kind = "numeric"
        sample_log.append({"draw_start": i0, "draw_end": replay.index, "kind": kind, "k": k_mask, "out": out})
        return out

    parent: dict[str, Any] = {}
    orig_fwd = vb.spm_forwards

    def _hook(*args, **kw):
        t, m = args[9], args[12]
        mi = int(m) - 1
        nk = len(args[3][mi][0])
        if t == 1 and m == 1 and nk >= 6 and "draw_start" not in parent:
            P = args[1]
            Pf = np.asarray(P[mi][0][0], dtype=np.float64).reshape(-1)
            parent.update(
                {
                    "draw_start": replay.index,
                    "P_argmax_1b": int(np.argmax(Pf) + 1),
                    "P_top_mass": float(np.max(Pf)),
                }
            )
        G, P2, F, id2, Pa = orig_fwd(*args, **kw)
        if t == 1 and m == 1 and nk >= 6:
            parent.setdefault("draw_after_forwards", replay.index)
            G0 = float(np.asarray(G, dtype=np.float64).reshape(-1)[0])
            parent["G00"] = G0
        return G, P2, F, id2, Pa

    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    with _CountingReplay(buf) as replay:
        vb._spm_sample = _logged_sample
        vb.spm_forwards = _hook
        try:
            pdp = spm_MDP_VB_XXX(
                rdp,
                {},
                monitoring=False,
                dump_subentries=False,
                reuse_matlab_draws=False,
            )
        finally:
            vb._spm_sample = orig_sample
            vb.spm_forwards = orig_fwd

    audit["replay"] = {
        **parent,
        "total_draws": replay.index,
        "unused_draws": k - replay.index,
        "PDP_G1": float(np.asarray(pdp["G"][0], dtype=np.float64).ravel()[0]),
        "spm_sample_calls": len(sample_log),
        "spm_sample_last8": sample_log[-8:],
    }
    # draws consumed in window around parent forwards
    ds = int(parent.get("draw_start", 0))
    de = int(parent.get("draw_after_forwards", ds))
    audit["replay"]["draw_window"] = [(i, float(v)) for i, v in replay.history if ds <= i < min(de + 3, k)]
    return audit


def _run_native_sample_count() -> dict[str, int]:
    """Native RNG: count ``spm_sample`` calls only (not draw values)."""
    n = [0]
    orig = vb._spm_sample

    def _count(p: Any) -> int:
        n[0] += 1
        return int(orig(p))

    rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
    vb._spm_sample = _count
    try:
        spm_MDP_VB_XXX(rdp, {}, monitoring=False, dump_subentries=False, reuse_matlab_draws=False)
    finally:
        vb._spm_sample = orig
    return {"native_spm_sample_calls": n[0]}


def main() -> None:
    out = _run_replay_with_hook()
    out["native"] = _run_native_sample_count()
    out["coherence"] = {
        "protocol": "entry12_v5_preamble_rewind (buf from MATLAB post-rewind rand(K,1))",
        "note": (
            "Replay injects MATLAB scalars; NumPy twister seed is NOT used. "
            "Twister/seed parity applies only to native rand() vs MATLAB rand(), not replay."
        ),
        "sample_calls_match": out["replay"]["spm_sample_calls"]
        == out["native"]["native_spm_sample_calls"],
    }
    _OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"wrote {_OUT}")


if __name__ == "__main__":
    main()
