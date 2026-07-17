"""W2 — optim ``_vb_run_partial_t_loop`` (12F hot path).

**3-O-2:** path/state + share via ``vb_orchestrator_optim.py`` (``.m`` ~796–909).
**3-O-3:** outcomes block via same module (``.m`` ~911–1009).
**3-O-4:** hierarchical + ``BP``/``IP`` via same module (``.m`` ~1011–1259).
**3-O-5:** post-forwards belief via same module (``.m`` ~1264–1409).
**3-O-6:** ``id.ig``/``sn`` + terminal trim via same module (``.m`` ~1418–1443).
**3-O-7:** entry calls this module directly (no fidelity ``_vb_run_partial_t_loop`` patch).
**Pa alias:** ``MDP(m).Pa = Pa`` in place (line ~1500).

See ``XXX_optim.md`` § Phase 3-O.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np

import python_src.optimized.toolbox.DEM.vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM.vb_forwards_optim import _forwards_ws
from python_src.optimized.toolbox.DEM.vb_workspace_optim import ws_get, ws_to_bundle
from python_src.optimized.toolbox.DEM.vb_orchestrator_optim import (
    vb_orchestrator_active_learning_in_loop,
    vb_orchestrator_belief_after_forwards,
    vb_orchestrator_ensure_per_t_traces,
    vb_orchestrator_fill_BP_IP_at_t,
    vb_orchestrator_fill_O_empty_from_realized_o_at_t,
    vb_orchestrator_generate_outcomes_if_options_o,
    vb_orchestrator_generation_paths_states,
    vb_orchestrator_hierarchical_subordinate_outcomes,
    vb_orchestrator_in_loop_id_ig_and_sn,
    vb_orchestrator_share_states_one_t,
    vb_orchestrator_shared_probabilistic_outcomes,
    vb_orchestrator_trim_mdp_o_s_u_at_terminal_horizon,
)


def _vb_run_partial_t_loop_optim(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    alpha: float,
    recurse_partial: bool,
    *,
    reuse_matlab_draws: bool = False,
) -> None:
    """Per ``t``: same as fidelity except ``Pa`` writeback matches ``.m`` (no clone)."""
    M_upd = bundle["M_update"]
    t_int = int(bundle["T"])
    n_depth = int(bundle["N_policy_depth"])
    if _inst._vb_dump_active():
        bundle["entry12_D"] = {
            "in": _inst._entry12_snap_12d(models, bundle, 0, M_upd[0, :]),
        }
        bundle["entry12_E"] = {
            "in": _inst._entry12_snap_12e(models, bundle, 0),
        }
        bundle["entry12_F"] = {
            "in": _inst._entry12_snap_12f(models, bundle, 0, include_policy_traces=False),
        }
    for t_idx in range(t_int):
        t_iter = time.perf_counter()
        row = M_upd[t_idx, :]
        t_1based = t_idx + 1
        vb_orchestrator_generation_paths_states(models, bundle, t_idx, row)
        if _inst._vb_dump_active():
            _inst._entry12_assign_t_boundary(
                bundle["entry12_D"],
                _inst._entry12_snap_12d(models, bundle, t_1based, row),
                t_1based,
                t_int,
            )
        vb_orchestrator_share_states_one_t(models, bundle, t_idx, row)
        if _inst._vb_dump_active():
            for mm in np.asarray(row, dtype=np.int64).ravel():
                mi_s = int(mm) - 1
                if mi_s >= 0:
                    _inst._entry12_record_phase(mi_s, t_idx + 1, "post_share", bundle)
        vb_orchestrator_generate_outcomes_if_options_o(models, bundle, t_idx, row)
        vb_orchestrator_shared_probabilistic_outcomes(models, bundle, t_idx, row)
        vb_orchestrator_hierarchical_subordinate_outcomes(
            models,
            bundle,
            t_idx,
            row,
            recurse_partial,
            reuse_matlab_draws=reuse_matlab_draws,
        )
        vb_orchestrator_fill_O_empty_from_realized_o_at_t(models, bundle, t_idx, row)
        if _inst._vb_dump_active():
            snap_e = _inst._entry12_snap_12e(models, bundle, t_1based, t_idx=t_idx)
            _inst._entry12_attach_phase_log_to_snap(snap_e, bundle, t_1based, row)
            _inst._entry12_assign_t_boundary(
                bundle["entry12_E"],
                snap_e,
                t_1based,
                t_int,
            )
        vb_orchestrator_fill_BP_IP_at_t(bundle, t_idx)
        t_m = t_idx + 1
        n_horiz = int(min(t_int, t_m + n_depth))
        qa_b = bundle.get("qa")
        for mm in np.asarray(row, dtype=np.int64).ravel():
            if int(mm) < 1:
                continue
            mi = int(mm) - 1
            idm = bundle["id"][mi]
            if _inst._vb_dump_active():
                ex: dict[str, Any] = {"A_peaks": _inst._entry12_a_peaks_for_model(bundle["A"], mi)}
                for key in ("fp", "fu", "iH"):
                    if key in idm:
                        ex[f"id_{key}"] = np.asarray(idm[key], dtype=np.int64).ravel().tolist()
                _inst._entry12_record_phase(mi, t_m, "pre_forwards", bundle, extra=ex)
            ws_fwd = ws_get(bundle)
            if ws_fwd is None:
                raise RuntimeError("optim t-loop requires bundle['_vb_workspace_optim'] (Phase 4-W-1)")
            G_m, _, F_elbo, _, Pa_step = _forwards_ws(
                ws_fwd,
                mi,
                bundle,
                bundle["O"],
                bundle["Q"],
                bundle["A"],
                bundle["BP"],
                bundle["C"],
                bundle["H"],
                bundle["K"],
                bundle["W"],
                bundle["IP"],
                t_m,
                t_int,
                n_horiz,
                int(mm),
                bundle["id"],
                bundle["pA"],
                qa_b,
            )
            if _inst._vb_dump_active():
                _inst._entry12_record_phase(
                    mi, t_m, "post_forwards", bundle, extra={"F_after_fwd": float(F_elbo)}
                )
            _inst._entry12_attach_vbx_to_model(models, mi, t_m)
            Gw, Zt = vb_orchestrator_belief_after_forwards(
                mi, bundle, t_m, t_idx, np.asarray(G_m, dtype=np.float64), float(alpha)
            )
            vb_orchestrator_active_learning_in_loop(mi, models, bundle, t_idx, t_m)
            vb_orchestrator_ensure_per_t_traces(models, mi, t_int)
            models[mi]["F"][t_idx] = float(F_elbo)
            if _inst._vb_dump_active():
                _inst._entry12_record_phase(
                    mi, t_m, "post_mdp_F", bundle, extra={"F_mdp_slot": float(F_elbo)}
                )
            if isinstance(Gw, (int, float)):
                models[mi]["G"][t_idx] = float(Gw)
            else:
                models[mi]["G"][t_idx] = np.asarray(Gw, dtype=np.float64).copy()
            models[mi]["Z"][t_idx] = float(Zt)
            # MATLAB ~1500: MDP(m).Pa = Pa — alias, not deepcopy
            models[mi]["Pa"] = Pa_step
            vb_orchestrator_in_loop_id_ig_and_sn(mi, bundle, t_idx)
            if _inst._vb_monitoring_active():
                t_1based = t_idx + 1
                if t_1based == 1:
                    _inst._vb_monitor_snapshot("12F", models[mi], mi + 1, t_1based, "first")
                if t_1based == t_int:
                    _inst._vb_monitor_snapshot("12F", models[mi], mi + 1, t_1based, "last")

        if _inst._vb_dump_active():
            ws_dump_t = ws_get(bundle)
            if ws_dump_t is not None:
                ws_to_bundle(ws_dump_t, bundle)
            snap_f = _inst._entry12_snap_12f(models, bundle, t_1based, include_policy_traces=True)
            _inst._entry12_attach_phase_log_to_snap(snap_f, bundle, t_1based, row)
            _inst._entry12_assign_t_boundary(
                bundle["entry12_F"],
                snap_f,
                t_1based,
                t_int,
            )
        if t_idx + 1 == t_int:
            vb_orchestrator_trim_mdp_o_s_u_at_terminal_horizon(models, bundle)
        _inst._vb_timing_add_12f(time.perf_counter() - t_iter)
