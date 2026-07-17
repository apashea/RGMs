"""DEM_AtariIII.m compute after first VB — OPTIM1FULL (``python_src/optimized``)."""

from __future__ import annotations

import copy
import os
import sys
import time
from typing import Any, Callable

import numpy as np

from python_src.optimized.toolbox.DEM.spm_merge_structure_learning_optim import (
    spm_merge_structure_learning_optim,
)
from python_src.optimized.toolbox.DEM.spm_RDP_basin_optim import spm_RDP_basin_optim
from python_src.optimized.toolbox.DEM.spm_RDP_sort_optim import spm_RDP_sort_optim
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim
from python_src.toolbox.DEM.dem_atariiii_ledger_hooks import DemAtariLedgerHooks
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_RDP_MI import spm_RDP_MI
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs

ATARI_NT_DEFAULT = 256
ATARI_NR_DEFAULT = 32
ATARI_NS_DEFAULT = 256


def atari_nt_game_length() -> int:
    raw = str(os.getenv("RGMS_ATARI_NT", str(ATARI_NT_DEFAULT))).strip()
    return max(int(raw), 1)


def atari_nr_replications() -> int:
    raw = str(os.getenv("RGMS_ATARI_NR", str(ATARI_NR_DEFAULT))).strip()
    return max(int(raw), 1)


def atari_ns_concentration() -> float:
    raw = str(os.getenv("RGMS_ATARI_NS", str(ATARI_NS_DEFAULT))).strip()
    return float(raw)


def attach_generative_process(mdp: list[dict[str, Any]], gdp: dict[str, Any]) -> list[dict[str, Any]]:
    out = copy.deepcopy(mdp)
    out[0]["GA"] = gdp["A"]
    out[0]["GB"] = gdp["B"]
    out[0]["GU"] = gdp["U"]
    out[0]["GD"] = gdp["D"]
    out[0]["ID"] = gdp["id"]
    out[0]["chi"] = 512.0
    return out


def assemble_rdp_vb_call1_preamble(
    mdp: list[dict[str, Any]],
    c_val: float,
) -> dict[str, Any]:
    """MATLAB ``capture_optim1full_rand_ledger`` — ``vb_call1`` RDP (lines 254–257)."""
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
    from python_src.toolbox.DEM.spm_set_goals import spm_set_goals

    rdp = spm_set_goals(mdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_mdp2rdp(rdp)
    rdp["T"] = 64
    return rdp


def assemble_rdp_call3_post_nr_loop(
    mdp: list[dict[str, Any]],
    c_val: float,
    ns: float,
    *,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> dict[str, Any]:
    rdp, _j = spm_RDP_sort_optim(mdp, eig=eig)
    rdp = spm_set_goals_optim(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_mdp2rdp(rdp, 0, 1.0 / float(ns))
    rdp["T"] = 128
    return rdp


def assemble_rdp_call4_post_nr_loop(
    mdp: list[dict[str, Any]],
    c_val: float,
    ns: float,
    *,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> dict[str, Any]:
    rdp, _j = spm_RDP_sort_optim(mdp, eig=eig)
    rdp = spm_RDP_MI(rdp)
    rdp = spm_set_goals_optim(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_mdp2rdp(rdp, 0, 1.0 / float(ns))
    rdp["T"] = 128
    return rdp


def count_mdp_parameters(mdp: list[dict[str, Any]]) -> int:
    """``DEM_AtariIII.m`` lines 429–439 — MI on unsorted post-NR MDP, then ``nnz`` over ``a``/``b``."""
    pdp = spm_RDP_MI(mdp)
    nm = len(pdp)
    total = 0
    for n in range(nm):
        mdp_n = pdp[n]
        for g in range(len(mdp_n.get("a", []))):
            arr = mdp_n["a"][g]
            if isinstance(arr, list):
                arr = arr[0]
            total += int(np.count_nonzero(np.asarray(arr, dtype=np.float64)))
        for f in range(len(mdp_n.get("b", []))):
            arr = mdp_n["b"][f]
            if isinstance(arr, list):
                arr = arr[0]
            total += int(np.count_nonzero(np.asarray(arr, dtype=np.float64)))
    return total


def active_inference_nr_loop(
    mdp: list[dict[str, Any]],
    gdp: dict[str, Any] | None,
    ne: int,
    c_val: float,
    *,
    nt: int | None = None,
    nr: int | None = None,
    ns: float | None = None,
    hooks: DemAtariLedgerHooks | None = None,
    vb_game1_kwargs: dict[str, Any] | None = None,
    vb_kwargs_for_game: Callable[[int], dict[str, Any] | None] | None = None,
    fidelity_nr_assembly: bool = False,
    on_nr_game_pdp: Callable[[int, dict[str, Any]], None] | None = None,
    on_nr_game_pre_merge: Callable[[int, dict[str, Any], list[dict[str, Any]]], None]
    | None = None,
) -> list[dict[str, Any]]:
    h = hooks or DemAtariLedgerHooks.noop()
    nt_i = int(nt if nt is not None else atari_nt_game_length())
    nr_i = int(nr if nr is not None else atari_nr_replications())
    ns_f = float(ns if ns is not None else atari_ns_concentration())
    ne_i = int(ne)

    if gdp is not None:
        mdp_out = attach_generative_process(mdp, gdp)
    elif mdp and isinstance(mdp[0], dict) and "GA" in mdp[0]:
        mdp_out = copy.deepcopy(mdp)
    else:
        raise ValueError("active_inference_nr_loop requires GDP or MDP with generative-process attach")

    from python_src.toolbox.DEM.spm_set_goals import spm_set_goals

    def _vb_kwargs(game_index: int) -> dict[str, Any] | None:
        if vb_kwargs_for_game is not None:
            return vb_kwargs_for_game(game_index)
        if game_index == 1 and vb_game1_kwargs:
            return vb_game1_kwargs
        return None

    for i in range(1, nr_i + 1):
        t_game = time.perf_counter()
        h.set_label(f"OPTIM1FULL: active-inference game {i}/{nr_i}")
        h.deadline_check()

        vb_kw = _vb_kwargs(i)
        use_fidelity_goals = bool(vb_kw or fidelity_nr_assembly)
        if use_fidelity_goals:
            rdp = spm_set_goals(mdp_out, [2, 3], [float(c_val), -float(c_val)])
        else:
            rdp = spm_set_goals_optim(mdp_out, [2, 3], [float(c_val), -float(c_val)])
        rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
        rdp = spm_mdp2rdp(rdp, 0, 1.0 / ns_f)
        rdp["T"] = float(int(nt_i / ne_i))

        if vb_kw and "_optim1full_ledger_segment" in vb_kw:
            from tests.demo1.optim1full.optim1full_rand_ledger import (
                spm_mdp_vb_xxx_with_ledger_segment_reuse,
            )

            seg_info = vb_kw["_optim1full_ledger_segment"]
            pdp = spm_mdp_vb_xxx_with_ledger_segment_reuse(
                rdp,
                seg_info["buf"],
                start=int(seg_info["start"]),
                k=int(seg_info["k"]),
            )
        elif vb_kw:
            # Parity / diagnostic kwargs without ledger segment — keep dispatch.
            from tests.demo1.optim1full.optim1full_vb_dispatch import (
                spm_mdp_vb_xxx_callable,
            )

            vb_fn = spm_mdp_vb_xxx_callable("dispatch")
            pdp = vb_fn(rdp, {}, **vb_kw)
        else:
            # Native / Product A default: optim VB, no test-harness dispatch import.
            from python_src.optimized.toolbox.DEM.spm_MDP_VB_XXX_optim import (
                spm_MDP_VB_XXX_optim,
            )

            pdp = spm_MDP_VB_XXX_optim(rdp, {})
        # Structure ``F`` rows use pre-merge ``MDP`` (DEM_AtariIII.m L288–293).
        if on_nr_game_pre_merge is not None:
            on_nr_game_pre_merge(int(i), pdp, mdp_out)
        if on_nr_game_pdp is not None:
            on_nr_game_pdp(int(i), pdp)
        pdp_o_cells = _pdp_q_o_level1_cells(pdp)
        ng = len(pdp_o_cells)
        t_idx = np.arange(0, nt_i - ne_i + 1, dtype=np.int64)

        for s in range(1, ne_i + 1):
            cols = (t_idx + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            if fidelity_nr_assembly:
                mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
            else:
                mdp_out = spm_merge_structure_learning_optim(o_seg, mdp_out)
            h.deadline_check()

        if fidelity_nr_assembly:
            mdp_out, _d, _o, _hids, _ = spm_RDP_basin(
                mdp_out, [2, 3], [float(c_val), -float(c_val)]
            )
        else:
            mdp_out, _d, _o, _hids, _ = spm_RDP_basin_optim(
                mdp_out, [2, 3], [float(c_val), -float(c_val)]
            )

        if str(os.getenv("RGMS_ATARI_NR_GAME_TIMING", "1")).strip().lower() not in (
            "0",
            "false",
            "no",
        ):
            print(
                f"[DEM_AtariIII timing] OPTIM1FULL NR game {i}/{nr_i}: game_s={time.perf_counter() - t_game:.6f}",
                file=sys.stderr,
                flush=True,
            )

    return mdp_out


def _pdp_q_o_level1_cells(pdp: dict[str, Any]) -> list[list[Any]]:
    q = pdp.get("Q", {})
    o_levels = q.get("O")
    if o_levels is None:
        o_levels = q.get("o")
    if not isinstance(o_levels, list) or not o_levels:
        raise ValueError("PDP.Q.O missing for active-inference merge loop")
    level1 = o_levels[0]
    out: list[list[Any]] = []
    for row in level1:
        r: list[Any] = []
        for col in row:
            arr = np.asarray(col, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape((-1, 1), order="F")
            elif arr.ndim == 0:
                arr = np.reshape(arr, (1, 1), order="F")
            r.append(arr)
        out.append(r)
    return out
