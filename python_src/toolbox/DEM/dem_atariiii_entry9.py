"""DEM_AtariIII Entry 8+9 — merge outer loop with ``spm_RDP_basin`` and break."""

from __future__ import annotations

import copy
import time
from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_ledger_hooks import DemAtariLedgerHooks
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin


def basin_training_loop(
    pdp_o_cells: list[list[Any]],
    mdp: list[dict[str, Any]],
    ne: int,
    c_value: float,
    nt: int = 100,
    n_outer: int = 128,
    *,
    hooks: DemAtariLedgerHooks | None = None,
) -> dict[str, Any]:
    """MATLAB combined Entry 8+9 outer loop (merges then basin until ``all(d)``)."""
    h = hooks or DemAtariLedgerHooks.noop()
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    ne_i = int(ne)
    nt_i = int(nt)

    ns_hist: list[int] = []
    nu_hist: list[int] = []
    na_hist: list[int] = []
    no_hist: list[int] = []
    nh_hist: list[int] = []
    entry8_loop_s = 0.0
    entry9_loop_s = 0.0

    for i in range(1, int(n_outer) + 1):
        h.set_label(f"ENTRY9: outer i={i}/{int(n_outer)}")
        h.deadline_check()
        offset = int(np.remainder(i, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        t_merge = time.perf_counter()
        for s in range(1, ne_i + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
            h.deadline_check()
        entry8_loop_s += time.perf_counter() - t_merge

        h.set_label(f"ENTRY9: spm_RDP_basin outer i={i}/{int(n_outer)}")
        h.deadline_check()
        t_basin = time.perf_counter()
        mdp_out, d, o, hids, _ = spm_RDP_basin(
            mdp_out, [2, 3], [float(c_value), -float(c_value)]
        )
        b1 = np.asarray(mdp_out[len(mdp_out) - 1]["b"][0][0], dtype=np.float64)
        ns_hist.append(int(b1.shape[1]) if b1.ndim >= 2 else 1)
        nu_hist.append(int(b1.shape[2]) if b1.ndim >= 3 else 1)
        na_hist.append(int(np.sum(~np.asarray(d, dtype=bool).ravel(order="F"))))
        no_hist.append(int(np.sum(~np.asarray(o, dtype=bool).ravel(order="F"))))
        nh_hist.append(int(np.asarray(hids, dtype=np.int64).ravel(order="F").size))
        entry9_loop_s += time.perf_counter() - t_basin
        if np.all(np.asarray(d, dtype=bool).ravel(order="F")):
            break

    return {
        "MDP": mdp_out,
        "NS": ns_hist,
        "NU": nu_hist,
        "NA": na_hist,
        "NO": no_hist,
        "NH": nh_hist,
        "entry8_loop_s": entry8_loop_s,
        "entry9_loop_s": entry9_loop_s,
    }
