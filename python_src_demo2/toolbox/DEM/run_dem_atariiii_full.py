"""DEMO2 full driver — post–Entry 12 compute (does not modify ``python_src`` driver)."""

from __future__ import annotations

import time
from typing import Any

from python_src.toolbox.DEM.DEM_AtariIII import (
    _dem_atari_ledger_hooks,
    _rgms_run_deadline_check,
    _rgms_run_set_last_label,
    _rgms_section_timing_print,
)
from python_src.toolbox.DEM.entry12_atari_calls import ENTRY12_ATARI_CALL3_TAG, ENTRY12_ATARI_CALL4_TAG
from python_src.toolbox.DEM.entry12_matlab_capture import rdp_for_vb_from_python_assembly
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src_demo2.toolbox.DEM.demo2_preamble_ctx import acquire_demo2_preamble_ctx
from python_src_demo2.toolbox.DEM.demo2_preflight import run_demo2_preflight
from python_src_demo2.toolbox.DEM.dem_atariiii_post12 import (
    active_inference_nr_loop,
    assemble_rdp_call3_post_nr_loop,
    assemble_rdp_call4_post_nr_loop,
    atari_ns_concentration,
    count_mdp_parameters,
)


def run_dem_atariiii_full() -> dict[str, Any]:
    """
    ENTRY DEMO2 lane A — full ``DEM_AtariIII.m`` compute (preamble + post–Entry 12).

    Preamble via ``run_dem_atariiii(entry_stop=12)`` unless ``RGMS_DEMO2_LOAD_PREAMBLE_CTX=1``
    loads a prior dump (see ``demo2_preamble_ctx.py``). Post–12 via ``python_src_demo2``.

    Runs ``demo2_preflight`` first (mode from ``RGMS_DEMO2_PREFLIGHT_MODE`` or env).
    """
    _rgms_run_set_last_label("DEMO2: preflight fixtures")
    run_demo2_preflight()
    _t_demo2_post12 = time.perf_counter()
    ctx, resumed = acquire_demo2_preamble_ctx(source="run_dem_atariiii_full")
    if resumed:
        _rgms_run_set_last_label("DEMO2: resumed from preamble ctx PKL")
        _rgms_section_timing_print("DEMO2 preamble (loaded PKL, skipped Entries 1-12)", _t_demo2_post12)
        _t_demo2_post12 = time.perf_counter()

    hooks = _dem_atari_ledger_hooks()
    ns = atari_ns_concentration()
    c_val = float(ctx["C"])
    ne = int(ctx["Ne"])

    _t_nr = time.perf_counter()
    _rgms_run_set_last_label("DEMO2: active-inference NR loop")
    _rgms_run_deadline_check()
    ctx["MDP"] = active_inference_nr_loop(ctx["MDP"], ctx["GDP"], ne, c_val, hooks=hooks)
    _rgms_section_timing_print("Active inference NR loop", _t_nr)

    _t_call3 = time.perf_counter()
    _rgms_run_set_last_label("DEMO2: VB call 3 assembly")
    _rgms_run_deadline_check()
    ctx["RDP_call3"] = assemble_rdp_call3_post_nr_loop(ctx["MDP"], c_val, ns)
    _rgms_section_timing_print("DEMO2 VB call 3 (assembly)", _t_call3)

    _t_call3_vb = time.perf_counter()
    _rgms_run_set_last_label("DEMO2: VB call 3 spm_MDP_VB_XXX")
    _rgms_run_deadline_check()
    ctx["PDP_call3"] = spm_MDP_VB_XXX(
        rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG)
    )
    _rgms_section_timing_print("DEMO2 VB call 3 (spm_MDP_VB_XXX)", _t_call3_vb)

    _t_call4 = time.perf_counter()
    _rgms_run_set_last_label("DEMO2: VB call 4 assembly")
    _rgms_run_deadline_check()
    ctx["RDP_call4"] = assemble_rdp_call4_post_nr_loop(ctx["MDP"], c_val, ns)
    _rgms_section_timing_print("DEMO2 VB call 4 (assembly)", _t_call4)

    _t_call4_vb = time.perf_counter()
    _rgms_run_set_last_label("DEMO2: VB call 4 spm_MDP_VB_XXX")
    _rgms_run_deadline_check()
    ctx["PDP_call4"] = spm_MDP_VB_XXX(
        rdp_for_vb_from_python_assembly(ctx["RDP_call4"], tag=ENTRY12_ATARI_CALL4_TAG)
    )
    _rgms_section_timing_print("DEMO2 VB call 4 (spm_MDP_VB_XXX)", _t_call4_vb)

    ctx["demo2_np"] = count_mdp_parameters(ctx["MDP"])
    _rgms_section_timing_print("DEMO2 post-12 (NR loop + VB calls 3-4)", _t_demo2_post12)
    _rgms_run_set_last_label("run_dem_atariiii_full: complete")
    _rgms_run_deadline_check()
    return ctx
