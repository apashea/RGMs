"""W2 — optim VB entry orchestrator (bisect **0a** / **0d** / **0e**).

**0a FAIL:** nested ``checkX(mdp_in)`` in place → ``Q.E[0]`` ~1.04 (12F ~17.7 s).
**0d FAIL:** nested skip ``checkX`` → ``IndexError`` in ``_vb_tensors_through_H`` (12B).
**5-R-1 (active):** ws-only hot path; nested entry keeps **``Q`` deepcopy** (**0e**) for parity.

**4-N-1:** ``run_child_vb`` — nested hierarchical kernel; no ``spm_MDP_VB_XXX_optim`` re-entry.
**4-E-1:** ``run_optim_vb`` — canonical optim entry; cold bands via ``vb_cold_optim``; partial via ``vb_lifecycle_optim``.
**4-X-1:** patch layer deleted — hot path uses direct optim module calls only.

See ``OPTIM1FULL.md`` § W2 ledger **3-T1-0a** / **3-T1-0d** / **3-T1-0e** / **4-N-1** / **4-E-1** / **4-X-1**.
"""
from __future__ import annotations

import copy
import time
from typing import Any

from python_src.toolbox.DEM import spm_MDP_VB_XXX as _m
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM.vb_cold_optim import (
    vb_cold_assemble_12h,
    vb_cold_setup_12b,
    vb_cold_setup_12c,
    vb_cold_teardown_12g,
)
from python_src.optimized.toolbox.DEM.vb_lifecycle_optim import _vb_build_partial_output_optim
from python_src.optimized.toolbox.DEM.vb_rng_optim import VbRandContext
from python_src.optimized.toolbox.DEM.vb_t_loop_optim import _vb_run_partial_t_loop_optim
from python_src.optimized.toolbox.DEM.vb_workspace_optim import ws_from_bundle, ws_get, ws_to_bundle


def _vb_nested_entry_mdp_prepare(mdp_in: Any) -> Any:
    """
    Nested hierarchical VB — shallow shell; **``Q`` deepcopy** isolates child ``checkX`` (**0e**).

    Hot-path ``ws`` authority is unchanged; this clone is nested-entry only (~12E cost).
    """
    if not isinstance(mdp_in, dict):
        return spm_MDP_checkX(copy.deepcopy(mdp_in))
    mdp_work = dict(mdp_in)
    if "Q" in mdp_in:
        mdp_work["Q"] = copy.deepcopy(mdp_in["Q"])
    return spm_MDP_checkX(mdp_work)


def _vb_run_compute_pipeline(
    mdp_in: Any,
    options: Any | None,
    *,
    nested: bool,
    reuse_matlab_draws: bool,
    lean: bool,
) -> Any:
    """Shared 12A–12H compute path for top-level entry and nested ``run_child_vb``."""
    t_band = time.perf_counter()
    opts = _m._merge_options_vb(options)
    partial_ok = bool(int(opts.pop("_rgms_partial_ok", 0)))
    if _m._vb_has_multiple_epoch_columns(mdp_in):
        raise NotImplementedError(
            "spm_MDP_VB_XXX: multiple epochs (size(MDP,2)>1) are not translated yet"
        )
    if nested:
        mdp_checked = _vb_nested_entry_mdp_prepare(mdp_in)
    else:
        mdp_checked = spm_MDP_checkX(copy.deepcopy(mdp_in))
    models = _m._vb_models_after_checkx(mdp_checked)
    if not lean and _m._vb_dump_active():
        _m._vb_dump_save("12A", opts, {"note": "post-checkX"}, {"MDP": _m._vb_dump_mdp_payload(models)})
    _inst._vb_timing_set_band_wall("12A", time.perf_counter() - t_band)
    nm = len(models)
    if not lean and _m._vb_monitoring_active():
        for mi in range(nm):
            _m._vb_monitor_snapshot("12A", models[mi], mi + 1, None, "once")
    hp = _m._vb_hyperparameters_mdp1(models[0])
    t_h = float(models[0]["T"])
    t_band = time.perf_counter()
    bundle = vb_cold_setup_12b(models, nm, t_h, opts, hp)
    bundle["_vb_workspace_optim"] = ws_from_bundle(bundle)
    _inst._vb_timing_set_band_wall("12B", time.perf_counter() - t_band)
    if not lean and _m._vb_dump_active():
        _m._vb_dump_save(
            "12B",
            opts,
            {"note": "post-setup"},
            {
                "process": copy.deepcopy(bundle["process"]),
                "GP": copy.deepcopy(bundle["gp"]),
                "id": copy.deepcopy(bundle["id"]),
                "ID": copy.deepcopy(bundle["ID"]),
                "Ng": copy.deepcopy(bundle["Ng"]),
                "Nf": copy.deepcopy(bundle["Nf"]),
                "No": copy.deepcopy(bundle["No"]),
                "Ns": copy.deepcopy(bundle["Ns"]),
                "Nu": copy.deepcopy(bundle["Nu"]),
                "NG": copy.deepcopy(bundle["NG"]),
                "NF": copy.deepcopy(bundle["NF"]),
                "NS": copy.deepcopy(bundle["NS"]),
                "NU": copy.deepcopy(bundle["NU"]),
                "Nm": int(bundle["Nm"]),
                "T": int(bundle["T"]),
                "MDP": _m._vb_dump_mdp_payload(models),
            },
        )
    t_band = time.perf_counter()
    bundle = vb_cold_setup_12c(models, bundle, opts, hp)
    _inst._vb_timing_set_band_wall("12C", time.perf_counter() - t_band)
    if not lean and _m._vb_dump_active():
        _m._vb_dump_save(
            "12C",
            opts,
            {"note": "before for t"},
            {
                "M": copy.deepcopy(bundle["M_update"]),
                "N": int(bundle["N_policy_depth"]),
                "MDP": _m._vb_dump_mdp_payload(models),
                "O": copy.deepcopy(bundle["O"]),
                "A": copy.deepcopy(bundle["A"]),
                "B": copy.deepcopy(bundle["B"]),
                "BP": copy.deepcopy(bundle["BP"]),
                "IP": copy.deepcopy(bundle["IP"]),
            },
        )
    if not lean and _m._vb_monitoring_active():
        for mi in range(nm):
            _m._vb_monitor_snapshot("12C", models[mi], mi + 1, None, "once")
    _vb_run_partial_t_loop_optim(
        models,
        bundle,
        float(hp["alpha"]),
        partial_ok,
        reuse_matlab_draws=reuse_matlab_draws,
    )
    if not lean and _m._vb_dump_active():
        ws_dump = ws_get(bundle)
        if ws_dump is not None:
            ws_to_bundle(ws_dump, bundle)
        opts_loop = bundle.get("options_vb", opts)
        _m._vb_dump_save(
            "12D",
            opts_loop,
            {"note": "early band boundaries"},
            copy.deepcopy(bundle.get("entry12_D", {})),
        )
        _m._vb_dump_save(
            "12E",
            opts_loop,
            {"note": "outcomes/hierarchical boundaries"},
            copy.deepcopy(bundle.get("entry12_E", {})),
        )
        _m._vb_dump_save(
            "12F",
            opts_loop,
            {"note": "belief-update boundaries"},
            copy.deepcopy(bundle.get("entry12_F", {})),
        )
        _m._vb_dump_save(
            "12G",
            opts_loop,
            {"note": "after time loop"},
            {
                "Q": copy.deepcopy(bundle["Q"]),
                "P": copy.deepcopy(bundle["P"]),
                "O": copy.deepcopy(bundle["O"]),
                "R": copy.deepcopy(bundle["R_policy"]),
                "v": copy.deepcopy(bundle["v_policy"]),
                "w": copy.deepcopy(bundle["w_policy"]),
                "id": copy.deepcopy(bundle["id"]),
                "MDP": _m._vb_dump_mdp_payload(models),
            },
        )
    t_band = time.perf_counter()
    ws_teardown = ws_get(bundle)
    if ws_teardown is not None:
        ws_to_bundle(ws_teardown, bundle)
    if not lean and _m._vb_monitoring_active():
        for mi in range(nm):
            _m._vb_monitor_snapshot("12G", models[mi], mi + 1, None, "first")
    vb_cold_teardown_12g(models, bundle, opts, hp)
    if not lean and _m._vb_monitoring_active():
        for mi in range(nm):
            _m._vb_monitor_snapshot("12G", models[mi], mi + 1, None, "last")
    _inst._vb_timing_set_band_wall("12G", time.perf_counter() - t_band)
    t_band = time.perf_counter()
    vb_cold_assemble_12h(models, bundle)
    _inst._vb_timing_set_band_wall("12H", time.perf_counter() - t_band)
    if partial_ok:
        return _vb_build_partial_output_optim(models, bundle)
    if len(models) == 1:
        out_final = copy.deepcopy(models[0])
    else:
        out_final = copy.deepcopy(models)
    if not lean and _m._vb_dump_active():
        _m._vb_dump_save("12H", opts, {"subentry": "12H"}, {"PDP": copy.deepcopy(out_final)})
        _m._vb_dump_save(
            "12I",
            opts,
            {"subentry": "12I"},
            {
                "spine": {
                    "T": int(bundle["T"]),
                    "Nm": int(bundle["Nm"]),
                    "N": int(bundle["N_policy_depth"]),
                }
            },
        )
    return out_final


def run_child_vb(
    child_mdp: Any,
    options: Any | None = None,
    *,
    reuse_matlab_draws: bool = False,
) -> Any:
    """
    **4-N-1** nested hierarchical child VB kernel.

    Call only from ``vb_hierarchical_optim`` during parent ``run_optim_vb``.
    Does **not** re-enter ``spm_MDP_VB_XXX_optim``.
    RNG stream is inherited from the parent top-level ``VbRandContext``.
    """
    _inst._vb_timing_enter()
    try:
        return _vb_run_compute_pipeline(
            child_mdp,
            options,
            nested=True,
            reuse_matlab_draws=reuse_matlab_draws,
            lean=True,
        )
    finally:
        _inst._vb_timing_leave()


def run_optim_vb(
    mdp_in: Any,
    options: Any | None = None,
    *,
    monitoring: bool = False,
    dump_subentries: bool = False,
    reuse_matlab_draws: bool = False,
) -> Any:
    """
    **4-E-1** canonical optim VB entry — ``run_optim_vb(RDP, OPTIONS)``.

    Cold bands via ``vb_cold_optim``; hot **12F** via ``vb_t_loop_optim``; partial return
    via ``vb_lifecycle_optim``. No runtime monkey-patches on fidelity (**4-X-1**).
    """
    _inst._vb_timing_enter()
    if _inst._VB_TIMING_DEPTH == 1 and _inst._vb_capture_y_probe_active():
        _inst._ENTRY12_VBX_ACC = {}
    if _inst._VB_TIMING_DEPTH == 1 and dump_subentries:
        _inst._ENTRY12_PHASE_ACC = {}
    if monitoring and _inst._VB_TIMING_DEPTH == 1:
        _inst._VB_MONITOR_REQUESTED = True
    if dump_subentries and _inst._VB_TIMING_DEPTH == 1:
        _inst._VB_DUMP_SPEC = _inst._vb_dump_resolve_spec()
    try:
        with VbRandContext(reuse_matlab_draws=reuse_matlab_draws):
            return _vb_run_compute_pipeline(
                mdp_in,
                options,
                nested=_inst._VB_TIMING_DEPTH != 1,
                reuse_matlab_draws=reuse_matlab_draws,
                lean=False,
            )
    finally:
        _inst._vb_timing_leave()
        if _inst._VB_TIMING_DEPTH == 0:
            _inst._VB_MONITOR_REQUESTED = False
            _inst._VB_DUMP_SPEC = None


def run_spm_MDP_VB_XXX_optim_entry(
    mdp_in: Any,
    options: Any | None = None,
    *,
    monitoring: bool = False,
    dump_subentries: bool = False,
    reuse_matlab_draws: bool = False,
) -> Any:
    """Deprecated alias — use ``run_optim_vb`` (**4-E-1**)."""
    return run_optim_vb(
        mdp_in,
        options,
        monitoring=monitoring,
        dump_subentries=dump_subentries,
        reuse_matlab_draws=reuse_matlab_draws,
    )
