"""W2 — optim VB entry orchestrator (bisect **0a** / **0d** / **0e**).

**0a FAIL:** nested ``checkX(mdp_in)`` in place → ``Q.E[0]`` ~1.04 (12F ~17.7 s).
**0d FAIL:** nested skip ``checkX`` → ``IndexError`` in ``_vb_tensors_through_H`` (12B).
**5-C-arena:** nested child uses **checkX without ``Q`` clone** + shared ``Q`` alias (``.m`` ~1163–1165).

**4-N-1:** ``run_child_vb`` — nested hierarchical kernel; no ``spm_MDP_VB_XXX_optim`` re-entry.
**4-E-1:** ``run_optim_vb`` — canonical optim entry; cold bands via ``vb_cold_optim``; partial via ``vb_lifecycle_optim``.
**4-X-1:** patch layer deleted — hot path uses direct optim module calls only.

See ``OPTIM1FULL.md`` § W2 ledger **3-T1-0a** / **3-T1-0d** / **3-T1-0e** / **4-N-1** / **4-E-1** / **4-X-1** / **5-C-arena**.
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
    vb_cold_teardown_child_kernel_native,
)
from python_src.optimized.toolbox.DEM.vb_lifecycle_optim import _vb_build_partial_output_optim
from python_src.optimized.toolbox.DEM.vb_rng_optim import VbRandContext
from python_src.optimized.toolbox.DEM.vb_child_kernel_optim import child_bundle_acquire, child_ws_acquire
from python_src.optimized.toolbox.DEM.vb_run_arena_optim import VbRunArena, arena_attach, arena_get
from python_src.optimized.toolbox.DEM.vb_t_loop_optim import _vb_run_partial_t_loop_optim
from python_src.optimized.toolbox.DEM.vb_workspace_optim import ws_from_bundle, ws_get, ws_to_bundle


def _vb_child_mdp_checked(mdp_in: Any) -> list[dict[str, Any]]:
    """
    Nested ``checkX`` — **does not read or write ``Q``** (``.m`` / ``spm_MDP_checkX``).

    ``Q`` isolation for child VB is **hierarchical prep** (parent ``Q`` alias per ``.m`` ~1163–1165).
    """
    if not isinstance(mdp_in, dict):
        checked = spm_MDP_checkX(copy.deepcopy(mdp_in))
        return _m._vb_models_after_checkx(checked)
    checked = spm_MDP_checkX(dict(mdp_in))
    return _m._vb_models_after_checkx(checked)


def _vb_child_ab_cell_fp(value: Any) -> tuple[Any, ...]:
    """Stable fingerprint for one ``A``/``B``/``a``/``b`` cell (shape + dtype + sum)."""
    import numpy as np

    if value is None:
        return ("none",)
    if isinstance(value, list):
        if len(value) == 1 and not isinstance(value[0], list):
            return _vb_child_ab_cell_fp(value[0])
        return ("list", len(value), tuple(_vb_child_ab_cell_fp(x) for x in value))
    a = np.asarray(value)
    if a.dtype == object or a.ndim == 0:
        return ("obj", a.shape, str(a.dtype))
    try:
        af = np.asarray(a, dtype=np.float64)
        return (af.shape, str(af.dtype), float(np.sum(af)))
    except Exception:
        return ("fail", id(value))


def _vb_child_ab_fp(mdp_in: Any) -> tuple[Any, ...]:
    """Fingerprint ``a``/``b``/``A``/``B`` for C4n checked-child invalidation."""
    if isinstance(mdp_in, dict):
        models = [mdp_in]
    elif isinstance(mdp_in, list):
        models = list(mdp_in)
    else:
        return ("nonlist", type(mdp_in).__name__)
    parts: list[Any] = []
    for md in models:
        if not isinstance(md, dict):
            parts.append(("bad", type(md).__name__))
            continue
        for key in ("A", "B", "a", "b"):
            if key not in md:
                parts.append((key, "missing"))
            else:
                cell = md[key]
                if isinstance(cell, list):
                    parts.append((key, tuple(_vb_child_ab_cell_fp(x) for x in cell)))
                else:
                    parts.append((key, _vb_child_ab_cell_fp(cell)))
    return tuple(parts)


def _vb_nested_entry_mdp_prepare(mdp_in: Any) -> Any:
    """Legacy nested prepare — retained for non-arena fallback only."""
    if not isinstance(mdp_in, dict):
        return spm_MDP_checkX(copy.deepcopy(mdp_in))
    mdp_work = dict(mdp_in)
    if "Q" in mdp_in:
        mdp_work["Q"] = copy.deepcopy(mdp_in["Q"])
    return spm_MDP_checkX(mdp_work)


def _vb_run_child_pipeline(
    mdp_in: Any,
    options: Any | None,
    *,
    parent_bundle: dict[str, Any],
    parent_mi: int,
    t_idx: int,
    reuse_matlab_draws: bool,
) -> Any:
    """**ENDGAME-2** — nested child kernel: cached ``ws`` + slim partial teardown.

    **C4n:** after the first checked shell per ``parent_mi``, skip re-checkX and use
    D/E-only mutable refresh while ``a``/``b``/``A``/``B`` fingerprints match; invalidate
    on change (full checkX + full mutable refresh).
    """
    opts = _m._merge_options_vb(options)
    partial_ok = bool(int(opts.pop("_rgms_partial_ok", 0)))
    if _m._vb_has_multiple_epoch_columns(mdp_in):
        raise NotImplementedError(
            "spm_MDP_VB_XXX: multiple epochs (size(MDP,2)>1) are not translated yet"
        )
    arena = arena_get(parent_bundle)
    pmi = int(parent_mi)
    ab_fp = _vb_child_ab_fp(mdp_in)
    ab_stable = False
    if (
        arena is not None
        and arena.child_checkx_done.get(pmi)
        and arena.child_ab_fp.get(pmi) == ab_fp
    ):
        ab_stable = True
        models = [mdp_in] if isinstance(mdp_in, dict) else list(mdp_in)
    else:
        models = _vb_child_mdp_checked(mdp_in)
    nm = len(models)
    hp = _m._vb_hyperparameters_mdp1(models[0])
    t_h = float(models[0]["T"])
    if arena is not None:
        arena.child_checkx_done[pmi] = True
        arena.child_ab_fp[pmi] = ab_fp
        bundle = child_bundle_acquire(
            arena.child_bundle_slots,
            pmi,
            models,
            nm,
            t_h,
            opts,
            hp,
            ab_stable=ab_stable,
        )
        ws = child_ws_acquire(arena.child_ws_slots, pmi, models, nm, t_h, bundle)
    else:
        from python_src.optimized.toolbox.DEM.vb_cold_optim import vb_cold_setup_child_12bc_native

        bundle = vb_cold_setup_child_12bc_native(models, nm, t_h, opts, hp)
        ws = ws_from_bundle(bundle)
    bundle["_vb_workspace_optim"] = ws
    _vb_run_partial_t_loop_optim(
        models,
        bundle,
        float(hp["alpha"]),
        partial_ok,
        reuse_matlab_draws=reuse_matlab_draws,
    )
    ws_child = ws_get(bundle)
    if ws_child is not None:
        ws_to_bundle(ws_child, bundle)
    vb_cold_teardown_child_kernel_native(models, bundle, opts, hp)
    if partial_ok:
        return _vb_build_partial_output_optim(models, bundle)
    return models[0] if len(models) == 1 else models


def _vb_run_compute_pipeline(
    mdp_in: Any,
    options: Any | None,
    *,
    nested: bool,
    reuse_matlab_draws: bool,
    lean: bool,
    parent_bundle: dict[str, Any] | None = None,
    parent_mi: int | None = None,
    t_idx: int | None = None,
) -> Any:
    """Shared 12A–12H compute path for top-level entry and nested ``run_child_vb``."""
    if nested and parent_bundle is not None and parent_mi is not None and t_idx is not None:
        return _vb_run_child_pipeline(
            mdp_in,
            options,
            parent_bundle=parent_bundle,
            parent_mi=int(parent_mi),
            t_idx=int(t_idx),
            reuse_matlab_draws=reuse_matlab_draws,
        )

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
    if not nested:
        arena_attach(bundle, VbRunArena())
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
    # C4g: return the assembled model by reference — MATLAB spm_MDP_VB_XXX returns
    # MDP directly with no clone. models/bundle are call-local and discarded on
    # return, and ws_alloc_from_bundle allocates fresh arrays every call (no
    # cross-call pool), so out_final is the only surviving reference to its arrays;
    # the prior copy.deepcopy(models[0]) was a defensive fidelity-era safeguard
    # (~1.3 s, the single dominant deepcopy) with no live aliasing to protect.
    if len(models) == 1:
        out_final = models[0]
    else:
        out_final = models
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
    parent_bundle: dict[str, Any] | None = None,
    parent_mi: int | None = None,
    t_idx: int | None = None,
    reuse_matlab_draws: bool = False,
) -> Any:
    """
    **4-N-1** / **5-C-arena** nested hierarchical child VB kernel.

    Call only from ``vb_hierarchical_optim`` during parent ``run_optim_vb``.
    Does **not** re-enter ``spm_MDP_VB_XXX_optim``.
    """
    _inst._vb_timing_enter()
    try:
        return _vb_run_compute_pipeline(
            child_mdp,
            options,
            nested=True,
            reuse_matlab_draws=reuse_matlab_draws,
            lean=True,
            parent_bundle=parent_bundle,
            parent_mi=parent_mi,
            t_idx=t_idx,
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
    if _inst._VB_TIMING_DEPTH == 1:
        # Never carry inspection records across top-level calls. Resolve dump
        # state before probe activation so explicit Entry-12 captures retain
        # diagnostics while ordinary native calls leave them disabled.
        _inst._ENTRY12_VBX_ACC = {}
        _inst._VB_DUMP_SPEC = _inst._vb_dump_resolve_spec() if dump_subentries else None
        if dump_subentries:
            _inst._ENTRY12_PHASE_ACC = {}
    if monitoring and _inst._VB_TIMING_DEPTH == 1:
        _inst._VB_MONITOR_REQUESTED = True
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
