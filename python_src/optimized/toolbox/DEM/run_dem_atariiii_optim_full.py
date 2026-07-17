"""OPTIM1FULL Product A (W3 native) — preamble + post–12 compute (+ optional plots)."""

from __future__ import annotations

import sys
import time
from typing import Any

from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import (
    _dem_atari_ledger_hooks,
    _rgms_run_deadline_check,
    _rgms_run_set_last_label,
    _rgms_section_timing_print,
    run_dem_atariiii_optim,
)
from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
    active_inference_nr_loop,
    assemble_rdp_call3_post_nr_loop,
    assemble_rdp_call4_post_nr_loop,
    atari_ns_concentration,
    count_mdp_parameters,
)
from python_src.optimized.toolbox.DEM.spm_MDP_VB_XXX_optim import spm_MDP_VB_XXX_optim
from python_src.toolbox.DEM.entry12_atari_calls import ENTRY12_ATARI_CALL3_TAG, ENTRY12_ATARI_CALL4_TAG
from python_src.toolbox.DEM.entry12_matlab_capture import rdp_for_vb_from_python_assembly


def run_dem_atariiii_optim_full() -> dict[str, Any]:
    """
    OPTIM1FULL Product A (W3 native) compute — ``run_dem_atariiii_optim(12)`` then post–12.

    Uses ``spm_MDP_VB_XXX_optim`` for VB (same optim stack as parity).
    No Model B ledger; no Engine MI/eig/sort injects. See ``OPTIM1FULL.md``
    § **W3 NATIVE + COLAB1 — plan and living status**.

    When ``RGMS_OPTIM1FULL_NATIVE_PLOT=1``, writes final-frame PNGs via library
    ``dem_atariiii_plot_*`` (no MATLAB plot oracles / Engine plot injects).

    Returns context with ``optim1full_np`` and optional ``PDP_call3`` / ``PDP_call4``.
    """
    from python_src.optimized.toolbox.DEM.optim1full_native_plot import (
        attach_native_plot_hooks,
        native_nr_structure_f_hook,
        optim1full_native_plot_requested,
        run_native_plots_post_call3,
        run_native_plots_post_call4,
    )

    # Load matplotlib Agg before any heavy work when plots requested (Windows pyexpat).
    plot_enabled = optim1full_native_plot_requested()
    if plot_enabled:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401

        print(
            "[OPTIM1FULL native] final-frame plots enabled "
            "(RGMS_OPTIM1FULL_NATIVE_PLOT=1)",
            file=sys.stderr,
            flush=True,
        )

    _t_full = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL: preamble Entries 1-12")
    ctx = run_dem_atariiii_optim(entry_stop=12)
    _rgms_section_timing_print("OPTIM1FULL preamble (Entries 1-12)", _t_full)

    on_nr_pre = None
    on_nr_pdp = None
    if plot_enabled:
        ctx = attach_native_plot_hooks(ctx)
        on_nr_pre, on_nr_pdp = native_nr_structure_f_hook(ctx)

    hooks = _dem_atari_ledger_hooks()
    ns = atari_ns_concentration()
    c_val = float(ctx["C"])
    ne = int(ctx["Ne"])

    _t_post12 = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL: active-inference NR loop")
    _rgms_run_deadline_check()
    ctx["MDP"] = active_inference_nr_loop(
        ctx["MDP"],
        ctx["GDP"],
        ne,
        c_val,
        hooks=hooks,
        on_nr_game_pre_merge=on_nr_pre,
        on_nr_game_pdp=on_nr_pdp,
    )
    _rgms_section_timing_print("OPTIM1FULL active-inference NR loop", _t_post12)

    _t_call3 = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL: VB call 3 assembly")
    _rgms_run_deadline_check()
    ctx["RDP_call3"] = assemble_rdp_call3_post_nr_loop(ctx["MDP"], c_val, ns)
    _rgms_section_timing_print("OPTIM1FULL VB call 3 (assembly)", _t_call3)

    _t_call3_vb = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL: VB call 3 spm_MDP_VB_XXX_optim")
    _rgms_run_deadline_check()
    ctx["PDP_call3"] = spm_MDP_VB_XXX_optim(
        rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG)
    )
    _rgms_section_timing_print("OPTIM1FULL VB call 3 (spm_MDP_VB_XXX_optim)", _t_call3_vb)
    if plot_enabled:
        run_native_plots_post_call3(ctx)

    _t_call4 = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL: VB call 4 assembly")
    _rgms_run_deadline_check()
    ctx["RDP_call4"] = assemble_rdp_call4_post_nr_loop(ctx["MDP"], c_val, ns)
    _rgms_section_timing_print("OPTIM1FULL VB call 4 (assembly)", _t_call4)

    _t_call4_vb = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL: VB call 4 spm_MDP_VB_XXX_optim")
    _rgms_run_deadline_check()
    ctx["PDP_call4"] = spm_MDP_VB_XXX_optim(
        rdp_for_vb_from_python_assembly(ctx["RDP_call4"], tag=ENTRY12_ATARI_CALL4_TAG)
    )
    _rgms_section_timing_print("OPTIM1FULL VB call 4 (spm_MDP_VB_XXX_optim)", _t_call4_vb)
    if plot_enabled:
        run_native_plots_post_call4(ctx)

    ctx["optim1full_np"] = count_mdp_parameters(ctx["MDP"])
    _rgms_section_timing_print("OPTIM1FULL post-12 (NR loop + VB calls 3-4 + np)", _t_post12)
    _rgms_run_set_last_label("run_dem_atariiii_optim_full: complete")
    _rgms_run_deadline_check()
    if plot_enabled and "_optim1full_native_plot" in ctx:
        n_png = len(ctx["_optim1full_native_plot"].get("pngs", []))
        print(
            f"[OPTIM1FULL native] plots complete png_count={n_png}",
            file=sys.stderr,
            flush=True,
        )
    return ctx


__all__ = ["run_dem_atariiii_optim_full"]
