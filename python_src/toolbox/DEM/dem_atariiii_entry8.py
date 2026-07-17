"""DEM_AtariIII Entry 8 — training-window merge loop (no basin step)."""

from __future__ import annotations

import copy
import os
import sys
import time
from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_ledger_hooks import DemAtariLedgerHooks
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning


def entry8_outer_loop_count() -> int:
    """MATLAB ``for i = 1:128``; env ``RGMS_ATARI_ENTRY8_OUTER`` for harness speed only."""
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "128")).strip()
    try:
        n = int(raw)
    except ValueError as exc:
        raise ValueError(f"RGMS_ATARI_ENTRY8_OUTER must be int-like, got {raw!r}") from exc
    return int(np.clip(n, 1, 128))


def _entry8_timing_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_ENTRY8_TIMING", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def training_window_assimilations(
    pdp_o_cells: list[list[Any]],
    mdp: list[dict[str, Any]],
    ne: int,
    nt: int = 100,
    n_outer: int = 128,
    *,
    hooks: DemAtariLedgerHooks | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """
    ENTRY 8 ledger: repeated ``spm_merge_structure_learning`` on scheduled columns.

    Returns ``(mdp_out, total_merge_loop_s)``.
    """
    h = hooks or DemAtariLedgerHooks.noop()
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    ne_i = int(ne)
    nt_i = int(nt)
    timing = _entry8_timing_enabled()
    total_merge_loop_s = 0.0
    for i in range(1, int(n_outer) + 1):
        h.set_label(f"ENTRY8: outer i={i}/{int(n_outer)}")
        h.deadline_check()
        t_outer = time.perf_counter()
        offset = int(np.remainder(i, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        t_merge = time.perf_counter()
        for s in range(1, ne_i + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
            h.deadline_check()
        total_merge_loop_s += time.perf_counter() - t_merge
        if timing:
            print(
                f"[DEM_AtariIII entry8] outer {i}/{int(n_outer)} wall_s={time.perf_counter() - t_outer:.6f}",
                file=sys.stderr,
                flush=True,
            )
    return mdp_out, total_merge_loop_s
