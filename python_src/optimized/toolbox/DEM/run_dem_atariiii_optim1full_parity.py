"""OPTIM1FULL Product B — full driver with Model B scalar ledger replay (§ **11.7.2**)."""

from __future__ import annotations

import copy
import os
import sys
import time
from typing import Any

from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import (
    _dem_atari_ledger_hooks,
    _rgms_run_deadline_check,
    _rgms_run_set_last_label,
    _rgms_section_timing_print,
)
from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import (
    active_inference_nr_loop,
    assemble_rdp_vb_call1_preamble,
    attach_generative_process,
    atari_nr_replications,
    atari_ns_concentration,
    count_mdp_parameters,
)
from python_src.toolbox.DEM.entry12_atari_calls import (
    ENTRY12_ATARI_CALL1_TAG,
    ENTRY12_ATARI_CALL3_TAG,
    ENTRY12_ATARI_CALL4_TAG,
)
from python_src.toolbox.DEM.entry12_matlab_capture import rdp_for_vb_from_python_assembly
from tests.demo1.optim1full.optim1full_replay import atari_c_value
from tests.demo1.optim1full.optim1full_rand_ledger import (
    load_validated_optim1full_ledger,
    optim1full_rand_ledger_mat,
    optim1full_replay_matlab_draws,
    optim1full_vb_kwargs_provider_for_ledger_nr_loop,
    spm_mdp_vb_xxx_with_ledger_segment_reuse,
)
from tests.demo1.optim1full.optim1full_signoff_env import (
    OPTIM1FULL_CANONICAL_NR,
    optim1full_signoff_env,
)


def run_optim1full_through_generate(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    OPTIM1FULL spine stop after ``spm_MDP_generate`` (``DEM_AtariIII.m`` Gameplay fence).

    Replays the Model **B** ``entries_1_11`` ledger prefix through
    ``run_dem_atariiii_optim(entry_stop=3)`` only — no Entry **4** Engine MI/eig,
    no ``vb_call1``, no NR. Consumes a prefix of ``entries_1_11`` draws (unused
    draws remain; that is expected for this early fence).
    """
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim

    seg11 = manifest.segment("entries_1_11")
    _t_gen = time.perf_counter()
    _rgms_run_set_last_label(
        "OPTIM1FULL parity: generate fence (run_dem_atariiii_optim entry_stop=3)"
    )
    with optim1full_replay_matlab_draws(
        buf, start_index=seg11.start, k_use=seg11.k, entries_11=True
    ) as ctr:
        ctx = run_dem_atariiii_optim(entry_stop=3)
    draws_gen = int(ctr[0])
    if draws_gen < 1:
        raise RuntimeError(
            f"OPTIM1FULL generate fence: expected >0 ledger draws, got {draws_gen}"
        )
    if "PDP" not in ctx:
        raise RuntimeError("OPTIM1FULL generate fence: entry_stop=3 did not set ctx['PDP']")
    _rgms_section_timing_print("OPTIM1FULL parity generate (entry_stop=3)", _t_gen)

    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "generate_draws": draws_gen,
        "stop_after": "generate",
        "deadline_minutes": deadline_minutes,
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_after_basin(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    OPTIM1FULL spine stop after Attractors basin (``DEM_AtariIII.m`` ``dem_attractors_basin``).

    Same Model **B** ``entries_1_11`` stack as Product **B`` through
    ``run_dem_atariiii_optim(entry_stop=9)`` with Entry **4** MATLAB MI/eig/link hooks —
    **without** Entry **10** sort (basin series ``NS``…``NH`` are pre-sort). Expects full
    ``entries_1_11`` draw exhaustion (same as ``mdp_pre`` prefix before Entry 10).
    """
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_entry4_matlab import (
        make_optim1full_link_dir_mi_fn,
        make_optim1full_rgm_eig_pair,
        make_optim1full_rgm_mi_override_fn,
        optim1full_entry4_link_dir_mi_enabled,
        optim1full_entry4_matlab_eig_enabled,
        optim1full_entry4_matlab_mi_enabled,
        validation_entry4_metadata,
    )

    if not optim1full_entry4_matlab_eig_enabled():
        raise RuntimeError(
            "OPTIM1FULL after_basin requires RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG=1"
        )
    if not optim1full_entry4_matlab_mi_enabled():
        raise RuntimeError(
            "OPTIM1FULL after_basin requires RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI=1"
        )

    seg11 = manifest.segment("entries_1_11")
    _t_basin = time.perf_counter()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, demo1_repo_root())
        entry4_eig = make_optim1full_rgm_eig_pair(eng)
        entry4_mi = make_optim1full_rgm_mi_override_fn(eng)
        entry4_link_mi = (
            make_optim1full_link_dir_mi_fn(eng)
            if optim1full_entry4_link_dir_mi_enabled()
            else None
        )
        with optim1full_replay_matlab_draws(
            buf, start_index=seg11.start, k_use=seg11.k, entries_11=True
        ) as ctr:
            _rgms_run_set_last_label(
                "OPTIM1FULL parity: after_basin (run_dem_atariiii_optim entry_stop=9)"
            )
            from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim

            ctx = run_dem_atariiii_optim(
                entry_stop=9,
                entry4_rgm_eig_pair=entry4_eig,
                entry4_rgm_mi_override_fn=entry4_mi,
                entry4_link_dir_mi_fn=entry4_link_mi,
            )
        draws_11 = int(ctr[0])
        if draws_11 != int(seg11.k):
            raise RuntimeError(
                f"OPTIM1FULL after_basin ledger audit: consumed {draws_11} draws, "
                f"expected k={seg11.k}"
            )
    finally:
        eng.quit()

    for key in ("NS", "NU", "NA", "NO", "NH"):
        if key not in ctx:
            raise RuntimeError(f"OPTIM1FULL after_basin: entry_stop=9 missing ctx[{key!r}]")
    _rgms_section_timing_print("OPTIM1FULL parity after_basin (entry_stop=9)", _t_basin)

    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "after_basin_draws": draws_11,
        "stop_after": "after_basin",
        "deadline_minutes": deadline_minutes,
        "validation": validation_entry4_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_after_post_sort(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    OPTIM1FULL spine stop after Attractors post-sort (``dem_attractors_mdp_post_sort``).

    Model **B** ``entries_1_11`` through Entry **10** (sort + ``spm_set_goals``) with
    Entry **4** MI/eig/link + Entry **10** MATLAB ``eig`` — same Product B spectral
    lane as ``run_optim1full_optim1_through_mdp_pre(..., stop_after='entries_11')``.
    Exposes fence payload fields ``b1`` / ``hid`` for spine export vs MATLAB authority.
    """
    import numpy as np

    ctx = run_optim1full_optim1_through_mdp_pre(
        buf,
        manifest,
        deadline_minutes=deadline_minutes,
        stop_after="entries_11",
    )
    mdp = ctx.get("MDP")
    if not isinstance(mdp, list) or not mdp:
        raise RuntimeError("OPTIM1FULL after_post_sort: missing ctx['MDP'] after Entry 10")
    nm = len(mdp)
    b1 = np.asarray(mdp[nm - 1]["b"][0][0], dtype=np.float64)
    hid = np.asarray(ctx.get("hid", []), dtype=np.int64).ravel(order="F")
    if hid.size == 0:
        hid_list = mdp[nm - 1].get("id", {}).get("hid", [])
        hid = (
            np.asarray(hid_list, dtype=np.int64).ravel(order="F")
            if hid_list is not None
            else np.zeros(0, dtype=np.int64)
        )
    ctx["b1"] = b1
    ctx["hid"] = hid
    ledger = ctx.get("_optim1full_optim1_segment_ledger")
    if not isinstance(ledger, dict):
        raise RuntimeError("OPTIM1FULL after_post_sort: missing segment ledger")
    ledger = dict(ledger)
    ledger["stop_after"] = "after_post_sort"
    ledger["after_post_sort_draws"] = int(ledger.get("entries_1_11_draws", ledger.get("entries_1_11_k", -1)))
    ctx["_optim1full_optim1_segment_ledger"] = ledger
    return ctx


def run_optim1full_optim1_through_mdp_pre(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
    stop_after: str = "mdp_pre",
) -> dict[str, Any]:
    """
    OPTIM1 Product **B** extent on the Model **B** ledger through ``MDP_pre``.

    Same stack on Model **B** ledger: ``entries_1_11`` =
    ``run_dem_atariiii_optim(entry_stop=9)`` with Entry **4** MATLAB MI/eig/link
    hooks + Engine ``eig`` Entry **10** (``RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG=1``);
    ``vb_call1`` ledger segment; GDP attach → ``MDP_pre``.

    ``stop_after``: ``entries_11`` | ``vb_call1`` | ``mdp_pre`` (default).
    """
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_entry4_matlab import (
        make_optim1full_link_dir_mi_fn,
        make_optim1full_rgm_eig_pair,
        make_optim1full_rgm_mi_override_fn,
        optim1full_entry4_link_dir_mi_enabled,
        optim1full_entry4_matlab_eig_enabled,
        optim1full_entry4_matlab_mi_enabled,
        validation_entry4_metadata,
    )
    from tests.demo1.optim1full.optim1full_entry10_matlab import (
        optim1full_entry10_matlab_eig_enabled,
        run_entry10_optim1full_parity,
        validation_entry10_metadata,
    )

    if not optim1full_entry10_matlab_eig_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG=1"
        )

    seg11 = manifest.segment("entries_1_11")
    _t_pre = time.perf_counter()
    if not optim1full_entry4_matlab_eig_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG=1"
        )
    if not optim1full_entry4_matlab_mi_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI=1"
        )

    # One Engine spans Entry 4 (MI + spectral eig + link MI reuse) and Entry 10 (eig):
    # these are the narrow MATLAB-reuse points for the parity version; structure-learning
    # control flow/group assembly stays native Python. Entry 4 hooks run inside ledger
    # replay but consume no Python draws, so the entries_1_11 draw audit is unaffected.
    eng_pre = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng_pre, demo1_repo_root())
        entry4_eig = (
            make_optim1full_rgm_eig_pair(eng_pre)
            if optim1full_entry4_matlab_eig_enabled()
            else None
        )
        entry4_mi = (
            make_optim1full_rgm_mi_override_fn(eng_pre)
            if optim1full_entry4_matlab_mi_enabled()
            else None
        )
        entry4_link_mi = (
            make_optim1full_link_dir_mi_fn(eng_pre)
            if optim1full_entry4_link_dir_mi_enabled()
            else None
        )

        with optim1full_replay_matlab_draws(
            buf, start_index=seg11.start, k_use=seg11.k, entries_11=True
        ) as ctr:
            _rgms_run_set_last_label(
                "OPTIM1FULL parity: entries_1_9 (run_dem_atariiii_optim, Entry 4 MATLAB MI/eig)"
            )
            from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim

            ctx = run_dem_atariiii_optim(
                entry_stop=9,
                entry4_rgm_eig_pair=entry4_eig,
                entry4_rgm_mi_override_fn=entry4_mi,
                entry4_link_dir_mi_fn=entry4_link_mi,
            )
        draws_11 = int(ctr[0])
        if draws_11 != int(seg11.k):
            raise RuntimeError(
                f"OPTIM1FULL entries_1_11 ledger audit: consumed {draws_11} draws, "
                f"expected k={seg11.k}"
            )
        _rgms_section_timing_print("OPTIM1FULL parity OPTIM1 segment (entries_1_9)", _t_pre)

        _t_e10 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL parity: Entry 10 (MATLAB eig)")
        run_entry10_optim1full_parity(ctx, eng_pre)
        _rgms_section_timing_print("OPTIM1FULL parity Entry 10 (MATLAB eig)", _t_e10)
    finally:
        eng_pre.quit()

    if stop_after == "entries_11":
        ctx["MDP_pre_active_inference"] = copy.deepcopy(ctx["MDP"])
        ctx["_optim1full_optim1_segment_ledger"] = {
            "entries_1_11_k": seg11.k,
            "entries_1_11_draws": draws_11,
            "stop_after": stop_after,
            "deadline_minutes": deadline_minutes,
            "validation": {**validation_entry10_metadata(), **validation_entry4_metadata()},
        }
        return ctx

    c_val = atari_c_value()
    _t_vb1 = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL parity: vb_call1 (ledger segment reuse)")
    rdp_call1 = assemble_rdp_vb_call1_preamble(ctx["MDP"], c_val)
    seg1 = manifest.segment("vb_call1")
    ctx["PDP"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
        rdp_for_vb_from_python_assembly(rdp_call1, tag=ENTRY12_ATARI_CALL1_TAG),
        buf,
        start=seg1.start,
        k=seg1.k,
        extra_vb_kwargs={"monitoring": False},
    )
    _rgms_section_timing_print("OPTIM1FULL parity vb_call1", _t_vb1)

    if stop_after == "vb_call1":
        ctx["MDP_pre_active_inference"] = copy.deepcopy(ctx["MDP"])
        ctx["_optim1full_optim1_segment_ledger"] = {
            "entries_1_11_k": seg11.k,
            "entries_1_11_draws": draws_11,
            "vb_call1_k": seg1.k,
            "stop_after": stop_after,
            "deadline_minutes": deadline_minutes,
            "validation": {**validation_entry10_metadata(), **validation_entry4_metadata()},
        }
        return ctx

    ctx["MDP"] = attach_generative_process(ctx["MDP"], ctx["GDP"])
    ctx["MDP_pre_active_inference"] = copy.deepcopy(ctx["MDP"])
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": seg11.k,
        "entries_1_11_draws": draws_11,
        "vb_call1_k": seg1.k,
        "stop_after": stop_after,
        "deadline_minutes": deadline_minutes,
        "validation": {**validation_entry10_metadata(), **validation_entry4_metadata()},
    }
    return ctx


def run_optim1full_nr_on_ctx(
    ctx: dict[str, Any],
    buf: Any,
    manifest: Any,
    *,
    on_nr_game_pdp: Any = None,
    on_nr_game_pre_merge: Any = None,
) -> dict[str, Any]:
    """NR loop on ``ctx['MDP']`` already through GDP attach (tier **3g** / capture B3)."""
    hooks = _dem_atari_ledger_hooks()
    c_val = atari_c_value()
    ne = int(ctx["Ne"])
    _t_post12 = time.perf_counter()
    _rgms_run_set_last_label("OPTIM1FULL parity: active-inference NR loop")
    _rgms_run_deadline_check()
    ctx["MDP"] = active_inference_nr_loop(
        ctx["MDP"],
        None,
        ne,
        c_val,
        hooks=hooks,
        fidelity_nr_assembly=True,
        vb_kwargs_for_game=optim1full_vb_kwargs_provider_for_ledger_nr_loop(buf, manifest),
        on_nr_game_pdp=on_nr_game_pdp,
        on_nr_game_pre_merge=on_nr_game_pre_merge,
    )
    ctx["MDP_post_nr"] = copy.deepcopy(ctx["MDP"])
    _rgms_section_timing_print("OPTIM1FULL parity active-inference NR loop", _t_post12)
    return ctx


def run_optim1full_through_nr_game32(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    OPTIM1FULL Product **B** through NR game **32** (row **5** / structure ``F`` fence).

    Runs ``entries_1_11`` + ``vb_call1`` + GDP attach + full NR loop; exposes
    ``ctx['PDP']`` from game ``i=NR`` and structure ``ctx['F']`` (6×NR).
    """
    import numpy as np

    from tests.demo1.optim1full.optim1full_entry10_matlab import validation_entry10_metadata
    from tests.demo1.optim1full.optim1full_rand_ledger import optim1full_nr_game_segment_id
    from tests.demo1.optim1full.optim1full_signoff_env import OPTIM1FULL_CANONICAL_NR
    from tests.demo1.optim1full.optim1full_structure_learning_f import (
        structure_learning_f_column,
    )

    nr_final = int(OPTIM1FULL_CANONICAL_NR)
    ctx = run_optim1full_optim1_through_mdp_pre(buf, manifest, deadline_minutes=deadline_minutes)

    captured: dict[str, Any] = {}
    F = np.full((6, nr_final), np.nan, dtype=np.float64)
    gdp = ctx.get("GDP")
    if not isinstance(gdp, dict) or "id" not in gdp:
        raise RuntimeError("OPTIM1FULL nr_game_32 missing ctx['GDP']['id'] for structure F")
    gdp_id = gdp["id"]

    def _on_nr_game_pdp(game_i: int, pdp: Any) -> None:
        if int(game_i) == nr_final:
            captured["PDP"] = copy.deepcopy(pdp)

    def _on_nr_game_pre_merge(game_i: int, pdp: Any, mdp: Any) -> None:
        F[:, int(game_i) - 1] = structure_learning_f_column(pdp, mdp, gdp_id)

    ctx = run_optim1full_nr_on_ctx(
        ctx,
        buf,
        manifest,
        on_nr_game_pdp=_on_nr_game_pdp,
        on_nr_game_pre_merge=_on_nr_game_pre_merge,
    )

    if "PDP" not in captured:
        raise RuntimeError(f"NR loop did not emit PDP at game {nr_final}")
    if np.isnan(F).any():
        raise RuntimeError("NR loop did not fill structure F for all games")

    ctx["PDP"] = captured["PDP"]
    ctx["F"] = F

    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1")
    seg_nr = manifest.segment(optim1full_nr_game_segment_id(nr_final))
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "vb_call1_k": int(seg1.k),
        "nr_game_32_k": int(seg_nr.k),
        "nr_game_i": nr_final,
        "stop_after": "nr_game_32",
        "deadline_minutes": deadline_minutes,
        "validation": validation_entry10_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_vb_call3(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    OPTIM1FULL Product **B** through post-NR VB call **3** (row **7** illustrate fence).

    Same stack as ``run_dem_atariiii_optim1full_parity`` through ``ctx['PDP_call3']``,
    exposed for spine export at ``vb_call3`` without call **4**.
    """
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call3_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
        validation_sort_metadata,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1"
        )

    ctx = run_optim1full_optim1_through_mdp_pre(buf, manifest, deadline_minutes=deadline_minutes)
    ctx = run_optim1full_nr_on_ctx(ctx, buf, manifest)

    repo = demo1_repo_root()
    sort_template = optim1full_mdp_post_nr_mat()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        ns = atari_ns_concentration()
        c_val = atari_c_value()

        _t_call3 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL spine: VB call 3 (assembly)")
        ctx["RDP_call3"] = assemble_rdp_call3_post_nr_optim1full_parity(
            eng,
            ctx["MDP"],
            c_val,
            ns,
            template_mat=sort_template,
            mat_var="MDP_post_nr",
        )
        _rgms_section_timing_print("OPTIM1FULL spine VB call 3 (assembly)", _t_call3)

        seg3 = manifest.segment("vb_call3")
        _t_vb3 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL spine: vb_call3 (ledger segment reuse)")
        ctx["PDP_call3"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
            rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG),
            buf,
            start=seg3.start,
            k=seg3.k,
            extra_vb_kwargs={"monitoring": False},
        )
        ctx["PDP"] = ctx["PDP_call3"]
        _rgms_section_timing_print("OPTIM1FULL spine vb_call3", _t_vb3)
    finally:
        eng.quit()

    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1")
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "vb_call1_k": int(seg1.k),
        "vb_call3_k": int(seg3.k),
        "stop_after": "vb_call3",
        "deadline_minutes": deadline_minutes,
        "validation": validation_sort_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_vb_call4(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    OPTIM1FULL Product **B** through post-NR VB call **4** (row **9** illustrate fence).

    Runs call **3** then call **4** (ledger segments are sequential). Exposes
    ``ctx['PDP_call4']`` as ``ctx['PDP']`` for spine export without further steps.
    """
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call3_post_nr_optim1full_parity,
        assemble_rdp_call4_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
        validation_sort_metadata,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1"
        )

    ctx = run_optim1full_optim1_through_mdp_pre(buf, manifest, deadline_minutes=deadline_minutes)
    ctx = run_optim1full_nr_on_ctx(ctx, buf, manifest)

    repo = demo1_repo_root()
    sort_template = optim1full_mdp_post_nr_mat()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        ns = atari_ns_concentration()
        c_val = atari_c_value()

        _t_call3 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL spine: VB call 3 (assembly)")
        ctx["RDP_call3"] = assemble_rdp_call3_post_nr_optim1full_parity(
            eng,
            ctx["MDP"],
            c_val,
            ns,
            template_mat=sort_template,
            mat_var="MDP_post_nr",
        )
        _rgms_section_timing_print("OPTIM1FULL spine VB call 3 (assembly)", _t_call3)

        seg3 = manifest.segment("vb_call3")
        _t_vb3 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL spine: vb_call3 (ledger segment reuse)")
        ctx["PDP_call3"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
            rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG),
            buf,
            start=seg3.start,
            k=seg3.k,
            extra_vb_kwargs={"monitoring": False},
        )
        _rgms_section_timing_print("OPTIM1FULL spine vb_call3", _t_vb3)

        _t_call4 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL spine: VB call 4 (assembly)")
        ctx["RDP_call4"] = assemble_rdp_call4_post_nr_optim1full_parity(
            eng,
            ctx["MDP"],
            c_val,
            ns,
            template_mat=sort_template,
            mat_var="MDP_post_nr",
        )
        _rgms_section_timing_print("OPTIM1FULL spine VB call 4 (assembly)", _t_call4)

        seg4 = manifest.segment("vb_call4")
        _t_vb4 = time.perf_counter()
        _rgms_run_set_last_label("OPTIM1FULL spine: vb_call4 (ledger segment reuse)")
        ctx["PDP_call4"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
            rdp_for_vb_from_python_assembly(ctx["RDP_call4"], tag=ENTRY12_ATARI_CALL4_TAG),
            buf,
            start=seg4.start,
            k=seg4.k,
            extra_vb_kwargs={"monitoring": False},
        )
        ctx["PDP"] = ctx["PDP_call4"]
        _rgms_section_timing_print("OPTIM1FULL spine vb_call4", _t_vb4)
    finally:
        eng.quit()

    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1")
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "vb_call1_k": int(seg1.k),
        "vb_call3_k": int(seg3.k),
        "vb_call4_k": int(seg4.k),
        "stop_after": "vb_call4",
        "deadline_minutes": deadline_minutes,
        "validation": validation_sort_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_nr_game32_from_authority(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    Row **5** / structure ``F`` spine export — resume from frozen ``MDP_pre_active_inference``.

    Skips Entries **1–11**, Entry **10**, and ``vb_call1``; runs NR loop only; captures
    game ``i=NR`` ``PDP`` and structure ``F`` (6×NR).
    """
    import numpy as np

    from tests.demo1.optim1full.optim1full_entry10_matlab import validation_entry10_metadata
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_plot import load_optim1full_plot_ctx
    from tests.demo1.optim1full.optim1full_rand_ledger import optim1full_nr_game_segment_id
    from tests.demo1.optim1full.optim1full_structure_learning_f import (
        structure_learning_f_column,
    )

    pre_mat = optim1full_mdp_pre_active_inference_mat()
    if not pre_mat.is_file():
        raise FileNotFoundError(
            f"missing authority for spine resume: {pre_mat} — run authority capture first"
        )

    nr_final = int(OPTIM1FULL_CANONICAL_NR)
    mdp_pre = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
    ne = load_ne_from_mat(pre_mat, "Ne")
    plot_ctx = load_optim1full_plot_ctx()
    gdp_id = plot_ctx["GDP"]["id"]
    ctx: dict[str, Any] = {
        "MDP": copy.deepcopy(mdp_pre),
        "Ne": ne,
        "MDP_pre_active_inference": mdp_pre,
        "GDP": plot_ctx["GDP"],
    }

    captured: dict[str, Any] = {}
    F = np.full((6, nr_final), np.nan, dtype=np.float64)

    def _on_nr_game_pdp(game_i: int, pdp: Any) -> None:
        if int(game_i) == nr_final:
            captured["PDP"] = copy.deepcopy(pdp)

    def _on_nr_game_pre_merge(game_i: int, pdp: Any, mdp: Any) -> None:
        F[:, int(game_i) - 1] = structure_learning_f_column(pdp, mdp, gdp_id)

    with optim1full_signoff_env(deadline_minutes=str(deadline_minutes)):
        ctx = run_optim1full_nr_on_ctx(
            ctx,
            buf,
            manifest,
            on_nr_game_pdp=_on_nr_game_pdp,
            on_nr_game_pre_merge=_on_nr_game_pre_merge,
        )

    if "PDP" not in captured:
        raise RuntimeError(f"NR loop did not emit PDP at game {nr_final}")
    if np.isnan(F).any():
        raise RuntimeError("NR loop did not fill structure F for all games")

    ctx["PDP"] = captured["PDP"]
    ctx["F"] = F

    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1")
    seg_nr = manifest.segment(optim1full_nr_game_segment_id(nr_final))
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "vb_call1_k": int(seg1.k),
        "nr_game_32_k": int(seg_nr.k),
        "nr_game_i": nr_final,
        "stop_after": "nr_game_32",
        "deadline_minutes": deadline_minutes,
        "resume_from": "mdp_pre_active_inference",
        "validation": validation_entry10_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_vb_call3_from_authority(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    Row **7** spine export — resume from frozen ``MDP_post_nr`` (tier **3g** witness).

    Skips Entries **1–11**, ``vb_call1``, and NR; runs post-NR call **3** assembly + VB only.
    """
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call3_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
        validation_sort_metadata,
    )
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1"
        )

    post_mat = optim1full_mdp_post_nr_mat()
    if not post_mat.is_file():
        raise FileNotFoundError(
            f"missing authority for spine resume: {post_mat} — run authority capture first"
        )

    mdp_post = load_mdp_from_mat(post_mat, "MDP_post_nr")
    ctx: dict[str, Any] = {"MDP": mdp_post}

    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        ns = atari_ns_concentration()
        c_val = atari_c_value()

        with optim1full_signoff_env(deadline_minutes=str(deadline_minutes)):
            _t_call3 = time.perf_counter()
            _rgms_run_set_last_label("OPTIM1FULL spine resume: VB call 3 (assembly)")
            ctx["RDP_call3"] = assemble_rdp_call3_post_nr_optim1full_parity(
                eng,
                ctx["MDP"],
                c_val,
                ns,
                template_mat=post_mat,
                mat_var="MDP_post_nr",
            )
            _rgms_section_timing_print("OPTIM1FULL spine resume VB call 3 (assembly)", _t_call3)

            seg3 = manifest.segment("vb_call3")
            _t_vb3 = time.perf_counter()
            _rgms_run_set_last_label("OPTIM1FULL spine resume: vb_call3 (ledger segment reuse)")
            ctx["PDP_call3"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
                rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG),
                buf,
                start=seg3.start,
                k=seg3.k,
                extra_vb_kwargs={"monitoring": False},
            )
            ctx["PDP"] = ctx["PDP_call3"]
            _rgms_section_timing_print("OPTIM1FULL spine resume vb_call3", _t_vb3)
    finally:
        eng.quit()

    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1")
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "vb_call1_k": int(seg1.k),
        "vb_call3_k": int(seg3.k),
        "stop_after": "vb_call3",
        "deadline_minutes": deadline_minutes,
        "resume_from": "mdp_post_nr",
        "validation": validation_sort_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def run_optim1full_through_vb_call4_from_authority(
    buf: Any,
    manifest: Any,
    *,
    deadline_minutes: str,
) -> dict[str, Any]:
    """
    Row **9** spine export — resume from frozen ``MDP_post_nr``.

    Skips Entries **1–11**, ``vb_call1``, and NR; runs post-NR call **3** + **4** assembly + VB.
    """
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call3_post_nr_optim1full_parity,
        assemble_rdp_call4_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
        validation_sort_metadata,
    )
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1"
        )

    post_mat = optim1full_mdp_post_nr_mat()
    if not post_mat.is_file():
        raise FileNotFoundError(
            f"missing authority for spine resume: {post_mat} — run authority capture first"
        )

    mdp_post = load_mdp_from_mat(post_mat, "MDP_post_nr")
    ctx: dict[str, Any] = {"MDP": mdp_post}

    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        ns = atari_ns_concentration()
        c_val = atari_c_value()

        with optim1full_signoff_env(deadline_minutes=str(deadline_minutes)):
            _t_call3 = time.perf_counter()
            _rgms_run_set_last_label("OPTIM1FULL spine resume: VB call 3 (assembly)")
            ctx["RDP_call3"] = assemble_rdp_call3_post_nr_optim1full_parity(
                eng,
                ctx["MDP"],
                c_val,
                ns,
                template_mat=post_mat,
                mat_var="MDP_post_nr",
            )
            _rgms_section_timing_print("OPTIM1FULL spine resume VB call 3 (assembly)", _t_call3)

            seg3 = manifest.segment("vb_call3")
            _t_vb3 = time.perf_counter()
            _rgms_run_set_last_label("OPTIM1FULL spine resume: vb_call3 (ledger segment reuse)")
            ctx["PDP_call3"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
                rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG),
                buf,
                start=seg3.start,
                k=seg3.k,
                extra_vb_kwargs={"monitoring": False},
            )
            _rgms_section_timing_print("OPTIM1FULL spine resume vb_call3", _t_vb3)

            _t_call4 = time.perf_counter()
            _rgms_run_set_last_label("OPTIM1FULL spine resume: VB call 4 (assembly)")
            ctx["RDP_call4"] = assemble_rdp_call4_post_nr_optim1full_parity(
                eng,
                ctx["MDP"],
                c_val,
                ns,
                template_mat=post_mat,
                mat_var="MDP_post_nr",
            )
            _rgms_section_timing_print("OPTIM1FULL spine resume VB call 4 (assembly)", _t_call4)

            seg4 = manifest.segment("vb_call4")
            _t_vb4 = time.perf_counter()
            _rgms_run_set_last_label("OPTIM1FULL spine resume: vb_call4 (ledger segment reuse)")
            ctx["PDP_call4"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
                rdp_for_vb_from_python_assembly(ctx["RDP_call4"], tag=ENTRY12_ATARI_CALL4_TAG),
                buf,
                start=seg4.start,
                k=seg4.k,
                extra_vb_kwargs={"monitoring": False},
            )
            ctx["PDP"] = ctx["PDP_call4"]
            _rgms_section_timing_print("OPTIM1FULL spine resume vb_call4", _t_vb4)
    finally:
        eng.quit()

    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1")
    ctx["_optim1full_optim1_segment_ledger"] = {
        "entries_1_11_k": int(seg11.k),
        "vb_call1_k": int(seg1.k),
        "vb_call3_k": int(seg3.k),
        "vb_call4_k": int(seg4.k),
        "stop_after": "vb_call4",
        "deadline_minutes": deadline_minutes,
        "resume_from": "mdp_post_nr",
        "validation": validation_sort_metadata(),
    }
    _rgms_run_deadline_check()
    return ctx


def _optim1full_plot_witness_requested() -> bool:
    """W1-B / W1-E plot witness — default off so compute gates avoid matplotlib import."""
    return os.getenv("RGMS_OPTIM1FULL_PLOT", "").strip().lower() in ("1", "true", "yes")


def _optim1full_nr_final_plot_hook(plot_ctx: dict[str, Any]):
    """NR game ``i=NR`` only — §13 ``dem_active_inference_nr`` (not game 1 / call2)."""
    from tests.demo1.optim1full.optim1full_plot import (
        DEM_ACTIVE_INFERENCE_NR,
        assert_optim1full_live_site_plot_oracles,
    )
    from tests.demo1.optim1full.optim1full_signoff_env import OPTIM1FULL_CANONICAL_NR

    nr_final = int(OPTIM1FULL_CANONICAL_NR)

    def _hook(game_index: int, pdp: dict[str, Any]) -> None:
        if int(game_index) != nr_final:
            return
        assert_optim1full_live_site_plot_oracles(
            DEM_ACTIVE_INFERENCE_NR,
            pdp,
            plot_ctx,
            site_label="full-flow dem_active_inference_nr (i=NR)",
        )

    return _hook


def run_dem_atariiii_optim1full_parity(
    *,
    deadline_minutes: str = "180",
    stop_after_nr: bool = False,
) -> dict[str, Any]:
    """
    OPTIM1FULL Product B — full script under one ``rng(2)`` ledger.

    OPTIM1 extent: ``entries_1_11`` ledger replay + ``vb_call1`` segment ``reuse_matlab_draws``
    + GDP attach. NR uses ``gdp=None`` when MDP already has generative-process attach (tier **3g** lane).
    Post-NR VB calls **3**/**4** use per-segment ``reuse_matlab_draws``.

    When ``RGMS_OPTIM1FULL_PLOT=1`` (W1-E), asserts live §13 plot oracles at:
    ``dem_generative_ai`` (after ``vb_call1``), ``dem_active_inference_nr`` (``i=NR``),
    ``dem_before_compression_rgb`` (+ orbits-before paths) after call **3**, and
    ``dem_with_compression_rgb`` (+ orbits-after paths) after call **4**. Default off.
    """
    import sys

    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call3_post_nr_optim1full_parity,
        assemble_rdp_call4_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
        validation_sort_metadata,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1"
        )

    buf, manifest = load_validated_optim1full_ledger()

    # W1-E: load matplotlib / plot asserts **before** any MATLAB Engine session.
    # On Windows, importing pyexpat/matplotlib after Engine start/quit can fail with
    # ``DLL load failed while importing pyexpat``.
    plot_witness_enabled = _optim1full_plot_witness_requested()
    _live_site_assert = None
    _assert_plot_fixtures = None
    _assert_w1e_oracles = None
    _load_plot_ctx = None
    _DEM_GENERATIVE_AI = None
    _DEM_ACTIVE_INFERENCE_NR = None
    _DEM_BEFORE_COMPRESSION_RGB = None
    _DEM_WITH_COMPRESSION_RGB = None
    _DEM_ORBITS_BEFORE = None
    _DEM_ORBITS_AFTER = None
    plot_ctx_live: dict[str, Any] | None = None
    if plot_witness_enabled:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401 — force load before Engine

        from tests.demo1.optim1full.optim1full_plot import (
            DEM_ACTIVE_INFERENCE_NR as _DEM_ACTIVE_INFERENCE_NR,
            DEM_BEFORE_COMPRESSION_RGB as _DEM_BEFORE_COMPRESSION_RGB,
            DEM_GENERATIVE_AI as _DEM_GENERATIVE_AI,
            DEM_ORBITS_AFTER as _DEM_ORBITS_AFTER,
            DEM_ORBITS_BEFORE as _DEM_ORBITS_BEFORE,
            DEM_WITH_COMPRESSION_RGB as _DEM_WITH_COMPRESSION_RGB,
            assert_optim1full_live_site_plot_oracles as _live_site_assert,
            assert_optim1full_plot_fixtures_present as _assert_plot_fixtures,
            assert_optim1full_w1e_plot_oracles_present as _assert_w1e_oracles,
            load_optim1full_plot_ctx as _load_plot_ctx,
        )

        _assert_plot_fixtures()
        _assert_w1e_oracles()
        # Same ``plot_ctx.mat`` used to mint spine oracles / ``--plot-parity`` (RGB palette).
        # Live ``ctx['RGB']`` can differ in structure/content from that fixture; W1-E proves
        # **live fence PDP** plot numerics against oracles, not plot_ctx remint.
        plot_ctx_live = _load_plot_ctx()
        print(
            "[OPTIM1FULL parity] W1-E plot witness enabled (RGMS_OPTIM1FULL_PLOT=1) "
            f"sites={[_DEM_GENERATIVE_AI, _DEM_ACTIVE_INFERENCE_NR, _DEM_BEFORE_COMPRESSION_RGB, _DEM_WITH_COMPRESSION_RGB]}",
            file=sys.stderr,
            flush=True,
        )

    _t_full = time.perf_counter()
    with optim1full_signoff_env(deadline_minutes=deadline_minutes):
        if atari_nr_replications() != OPTIM1FULL_CANONICAL_NR:
            raise RuntimeError(
                f"sign-off env failed: NR={atari_nr_replications()} expected {OPTIM1FULL_CANONICAL_NR}"
            )

        ctx = run_optim1full_optim1_through_mdp_pre(buf, manifest, deadline_minutes=deadline_minutes)
        _rgms_section_timing_print("OPTIM1FULL parity OPTIM1 segment (through MDP_pre)", _t_full)

        from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
            ENTRY12_OPTIM1FULL_CALL3_TAG,
            ENTRY12_OPTIM1FULL_CALL4_TAG,
        )

        nr_plot_hook = None
        witness_sites: list[str] = []
        if plot_witness_enabled:
            assert _live_site_assert is not None and plot_ctx_live is not None
            # §13 row 4 — Generative AI after vb_call1 (ctx['PDP'] still call1 here).
            _live_site_assert(
                _DEM_GENERATIVE_AI,
                ctx["PDP"],
                plot_ctx_live,
                site_label="full-flow dem_generative_ai (vb_call1)",
            )
            ctx["PDP_call1"] = copy.deepcopy(ctx["PDP"])
            witness_sites.append(str(_DEM_GENERATIVE_AI))
            nr_plot_hook = _optim1full_nr_final_plot_hook(plot_ctx_live)

        repo = demo1_repo_root()
        sort_template = optim1full_mdp_post_nr_mat()
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, repo)

            ns = atari_ns_concentration()
            c_val = atari_c_value()

            ctx = run_optim1full_nr_on_ctx(ctx, buf, manifest, on_nr_game_pdp=nr_plot_hook)
            if plot_witness_enabled:
                witness_sites.append(str(_DEM_ACTIVE_INFERENCE_NR))

            if stop_after_nr:
                if plot_witness_enabled:
                    ctx["_optim1full_plot_witness"] = {
                        "enabled": True,
                        "sites": list(witness_sites),
                        "skipped": [
                            str(_DEM_BEFORE_COMPRESSION_RGB),
                            str(_DEM_WITH_COMPRESSION_RGB),
                        ],
                    }
                eng.quit()
                ctx["optim1full_np"] = count_mdp_parameters(ctx["MDP"])
                ctx["_optim1full_parity_lane"] = "product_b"
                ctx["_optim1full_ledger"] = {
                    "k_total": manifest.k_total,
                    "protocol": manifest.protocol,
                    "buf_path": str(optim1full_rand_ledger_mat().resolve()),
                }
                _rgms_run_set_last_label("run_dem_atariiii_optim1full_parity: stop_after_nr")
                _rgms_run_deadline_check()
                return ctx

            _t_call3 = time.perf_counter()
            ctx["RDP_call3"] = assemble_rdp_call3_post_nr_optim1full_parity(
                eng,
                ctx["MDP"],
                c_val,
                ns,
                template_mat=sort_template,
                mat_var="MDP_post_nr",
            )
            _rgms_section_timing_print("OPTIM1FULL parity VB call 3 (assembly)", _t_call3)

            seg3 = manifest.segment("vb_call3")
            ctx["PDP_call3"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
                rdp_for_vb_from_python_assembly(ctx["RDP_call3"], tag=ENTRY12_ATARI_CALL3_TAG),
                buf,
                start=seg3.start,
                k=seg3.k,
                extra_vb_kwargs={"monitoring": False},
            )
            if plot_witness_enabled and plot_ctx_live is not None:
                assert _live_site_assert is not None
                _live_site_assert(
                    _DEM_BEFORE_COMPRESSION_RGB,
                    ctx["PDP_call3"],
                    plot_ctx_live,
                    include_paths_site_id=_DEM_ORBITS_BEFORE,
                    site_label="full-flow dem_before_compression_rgb (+ orbits_before paths)",
                )
                witness_sites.append(str(_DEM_BEFORE_COMPRESSION_RGB))

            ctx["RDP_call4"] = assemble_rdp_call4_post_nr_optim1full_parity(
                eng,
                ctx["MDP"],
                c_val,
                ns,
                template_mat=sort_template,
                mat_var="MDP_post_nr",
            )
            seg4 = manifest.segment("vb_call4")
            ctx["PDP_call4"] = spm_mdp_vb_xxx_with_ledger_segment_reuse(
                rdp_for_vb_from_python_assembly(ctx["RDP_call4"], tag=ENTRY12_ATARI_CALL4_TAG),
                buf,
                start=seg4.start,
                k=seg4.k,
                extra_vb_kwargs={"monitoring": False},
            )
            if plot_witness_enabled and plot_ctx_live is not None:
                assert _live_site_assert is not None
                _live_site_assert(
                    _DEM_WITH_COMPRESSION_RGB,
                    ctx["PDP_call4"],
                    plot_ctx_live,
                    include_paths_site_id=_DEM_ORBITS_AFTER,
                    site_label="full-flow dem_with_compression_rgb (+ orbits_after paths)",
                )
                witness_sites.append(str(_DEM_WITH_COMPRESSION_RGB))
        finally:
            eng.quit()

    ctx["optim1full_np"] = count_mdp_parameters(ctx["MDP"])
    ctx["_optim1full_parity_lane"] = "product_b"
    if plot_witness_enabled:
        ctx["_optim1full_plot_witness"] = {
            "enabled": True,
            "sites": list(witness_sites),
        }
    ctx["_optim1full_validation"] = validation_sort_metadata()
    ctx["_optim1full_ledger"] = {
        "k_total": manifest.k_total,
        "protocol": manifest.protocol,
        "buf_path": str(optim1full_rand_ledger_mat().resolve()),
    }
    _rgms_run_set_last_label("run_dem_atariiii_optim1full_parity: complete")
    _rgms_run_deadline_check()
    return ctx


__all__ = [
    "run_dem_atariiii_optim1full_parity",
    "run_optim1full_optim1_through_mdp_pre",
    "run_optim1full_through_generate",
    "run_optim1full_through_after_basin",
    "run_optim1full_through_after_post_sort",
    "run_optim1full_nr_on_ctx",
    "run_optim1full_through_nr_game32",
    "run_optim1full_through_vb_call3",
    "run_optim1full_through_vb_call4",
]
