"""W2 Phase 4-E-1 — optim cold bands (12A–12C setup, 12G–12H teardown).

**6-A:** ``vb_cold_setup_12b`` uses ``vb_native_init_qxsp_outcomes_and_process`` (no fidelity
``_vb_init_QXSP_*`` ``deepcopy(D/E)`` per ``t``). Teardown still calls fidelity helpers until **6-E**.
"""
from __future__ import annotations

import copy
from typing import Any

import numpy as np

from python_src.toolbox.DEM import spm_MDP_VB_XXX as _vb_fidelity
from python_src.toolbox.DEM.spm_parents import spm_parents
from python_src.optimized.toolbox.DEM.vb_cold_native_optim import (
    vb_native_init_qxsp_outcomes_and_process,
    vb_native_refresh_qxsp_priors_only,
)
from python_src.optimized.toolbox.DEM.vb_contract_optim import forwards_dot_A_qj


def vb_cold_setup_12b(
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """12B: tensors through ``H``, init ``Q/X/S/P`` / process (**6-A** native ``Q``/``P`` init)."""
    bundle = _vb_fidelity._vb_tensors_through_H(models, nm, t_h)
    post = vb_native_init_qxsp_outcomes_and_process(
        models, bundle, opts, float(hp["chi"])
    )
    bundle.update(post)
    return bundle


def vb_cold_setup_12c(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """12C: policy depth + ``M``."""
    bundle.update(_vb_fidelity._vb_policy_depth_and_get_M(models, bundle, hp))
    bundle["options_vb"] = opts
    return bundle


def vb_cold_setup_12bc(
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """12B + 12C — convenience wrapper."""
    bundle = vb_cold_setup_12b(models, nm, t_h, opts, hp)
    return vb_cold_setup_12c(models, bundle, opts, hp)


def vb_cold_teardown_12g(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """12G: backwards replay, learning, ``Y``, ``X/S`` layout, neural responses."""
    _vb_fidelity._vb_optional_backwards_replay(models, bundle, opts)
    _vb_fidelity._vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
    _vb_fidelity._vb_posterior_predictive_Y(models, bundle, opts)
    _vb_fidelity._vb_reorganize_X_S_from_QP(bundle)
    _vb_fidelity._vb_options_N_neural_simulated_responses(models, bundle, opts)


def vb_cold_assemble_12h(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> None:
    """12H: assemble final ``MDP`` result fields on ``models``."""
    _vb_fidelity._vb_assemble_mdp_results_1691(models, bundle)


def vb_cold_teardown_12gh(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """12G + 12H — convenience wrapper for nested lean child path."""
    vb_cold_teardown_12g(models, bundle, opts, hp)
    vb_cold_assemble_12h(models, bundle)


def vb_cold_setup_child_12bc_native(
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """**5-C-arena** — nested child 12B/C setup (optim cold bridge; no top-level re-entry)."""
    return vb_cold_setup_12bc(models, nm, t_h, opts, hp)


def _vb_reset_bundle_O_shell(bundle: dict[str, Any]) -> None:
    """Clear outcome cells before native re-init (``OPTIONS.O`` resample each child call)."""
    t_int = int(bundle["T"])
    for m in range(int(bundle["Nm"])):
        for g_idx in range(len(bundle["O"][m])):
            for t_idx in range(t_int):
                bundle["O"][m][g_idx][t_idx] = None


def _vb_copy_gp_de_field(value: Any) -> Any:
    """Copy ``gp`` ``D``/``E`` leaves — NumPy arrays only, no stdlib ``deepcopy`` tree."""
    if isinstance(value, list):
        out: list[Any] = []
        for item in value:
            if isinstance(item, list):
                out.append(
                    [np.asarray(x, dtype=np.float64).copy(order="F") for x in item]
                )
            elif isinstance(item, np.ndarray):
                out.append(np.asarray(item, dtype=np.float64).copy(order="F"))
            else:
                out.append(item)
        return out
    if isinstance(value, np.ndarray):
        return np.asarray(value, dtype=np.float64).copy(order="F")
    return value


def vb_refresh_child_bundle_mutable(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> None:
    """
    **ENDGAME-2 tranche 2** — refresh hierarchical-prep fields on a cached child bundle.

    Skips full ``_vb_tensors_through_H`` when ``A``/``B`` layout is unchanged; updates
    ``D``/``E`` priors, Dirichlet ``a``/``b`` tensors, and ``gp`` D/E from current ``models``.
    """
    import numpy as np

    nm = int(bundle["Nm"])
    Ng = bundle["Ng"]
    Nf = bundle["Nf"]
    Ns = bundle["Ns"]
    Nu = bundle["Nu"]
    gp = bundle["gp"]
    proc = bundle["process"]

    _a_colon_s_coerce_likelihood_ = _vb_fidelity._a_colon_s_coerce_likelihood_
    _any_u_factor_cols = _vb_fidelity._any_u_factor_cols
    _spm_hnorm = _vb_fidelity._spm_hnorm
    _spm_norm = _vb_fidelity._spm_norm
    _spm_norm_inplace = _vb_fidelity._spm_norm_inplace
    _spm_wnorm = _vb_fidelity._spm_wnorm
    _unwrap_id_a_entry = _vb_fidelity._unwrap_id_a_entry
    _vb_as_float64_array = _vb_fidelity._vb_as_float64_array
    _vb_mdp_U_as_float_array = _vb_fidelity._vb_mdp_U_as_float_array
    _vb_workspace_A_like_mdp_shape = _vb_fidelity._vb_workspace_A_like_mdp_shape

    for m in range(nm):
        md = models[m]
        gpm = gp[m]
        ng_m = int(Ng[m])
        nf_m = int(Nf[m])

        if float(proc[m]) <= 0:
            gpm["D"] = _vb_copy_gp_de_field(md["D"])
            gpm["E"] = _vb_copy_gp_de_field(md["E"])

        U_arr = _vb_mdp_U_as_float_array(md)

        for g_idx in range(ng_m):
            id_ag = _unwrap_id_a_entry(md["id"]["A"][g_idx])
            f_parents = np.asarray(id_ag, dtype=np.int64).ravel()

            if "a" in md:
                qa_mg = md["a"][g_idx]
                qa_mg = qa_mg[0] if isinstance(qa_mg, list) and len(qa_mg) == 1 else qa_mg
            else:
                Ag = md["A"][g_idx]
                Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
                Ag_col = _a_colon_s_coerce_likelihood_(Ag)
                qa_mg = _vb_as_float64_array(Ag_col) * 512.0

            qa_ws = np.asarray(qa_mg, dtype=np.float64)
            if not qa_ws.flags.writeable:
                qa_ws = np.asarray(qa_mg, dtype=np.float64).copy(order="F")
            _spm_norm_inplace(qa_ws)
            if "A" in md:
                Agf = md["A"][g_idx]
                Agf = Agf[0] if isinstance(Agf, list) and len(Agf) == 1 else Agf
                if isinstance(Agf, np.ndarray) and Agf.dtype == bool:
                    qa_ws = qa_ws.astype(bool)
            if "a" in md:
                slot = md["a"][g_idx]
                if isinstance(slot, list) and len(slot) == 1:
                    slot[0] = qa_ws
                else:
                    md["a"][g_idx] = qa_ws
            bundle["pa"][m][g_idx] = qa_ws
            bundle["qa"][m][g_idx] = qa_ws
            if "A" in md:
                bundle["A"][m][g_idx] = _vb_workspace_A_like_mdp_shape(qa_ws, md["A"][g_idx])
            elif "a" in md:
                bundle["A"][m][g_idx] = _vb_workspace_A_like_mdp_shape(qa_ws, md["a"][g_idx])
            else:
                bundle["A"][m][g_idx] = qa_ws

            if _any_u_factor_cols(U_arr, f_parents):
                bundle["K"][m][g_idx] = _spm_hnorm(qa_ws)
                if "a" in md:
                    bundle["W"][m][g_idx] = _spm_wnorm(qa_ws)

        for f_idx in range(nf_m):
            if "b" in md:
                qb_m = md["b"][f_idx]
                qb_m = qb_m[0] if isinstance(qb_m, list) and len(qb_m) == 1 else qb_m
            else:
                Bg = md["B"][f_idx]
                Bg = Bg[0] if isinstance(Bg, list) and len(Bg) == 1 else Bg
                qb_m = _vb_as_float64_array(Bg) * 512.0

            bundle["qb"][m][f_idx] = qb_m
            bundle["pb"][m][f_idx] = qb_m
            B_norm = _spm_norm(qb_m)
            if "B" in md:
                Bgf = md["B"][f_idx]
                Bgf = Bgf[0] if isinstance(Bgf, list) and len(Bgf) == 1 else Bgf
                if isinstance(Bgf, np.ndarray) and Bgf.dtype == bool:
                    B_norm = B_norm.astype(bool)
            bundle["B"][m][f_idx] = B_norm

            if "b" in md and bool(np.any(U_arr[:, f_idx])):
                qb_src = md["b"][f_idx]
                qb_src = qb_src[0] if isinstance(qb_src, list) and len(qb_src) == 1 else qb_src
                bundle["I"][m][f_idx] = _spm_wnorm(qb_src)

            if "d" in md:
                qd_m = md["d"][f_idx]
                qd_m = qd_m[0] if isinstance(qd_m, list) and len(qd_m) == 1 else qd_m
            elif "D" in md:
                Dg = md["D"][f_idx]
                Dg = Dg[0] if isinstance(Dg, list) and len(Dg) == 1 else Dg
                qd_m = _vb_as_float64_array(Dg) * 512.0
            else:
                qd_m = np.ones((int(Ns[m, f_idx]), 1), dtype=np.float64)

            bundle["qd"][m][f_idx] = qd_m
            bundle["pd"][m][f_idx] = qd_m
            bundle["D"][m][f_idx] = _spm_norm(qd_m)

            if "e" in md:
                qe_m = md["e"][f_idx]
                qe_m = qe_m[0] if isinstance(qe_m, list) and len(qe_m) == 1 else qe_m
            elif "E" in md:
                Eg = md["E"][f_idx]
                Eg = Eg[0] if isinstance(Eg, list) and len(Eg) == 1 else Eg
                qe_m = _vb_as_float64_array(Eg) * 512.0
            else:
                qe_m = np.ones((int(Nu[m, f_idx]), 1), dtype=np.float64)

            bundle["qe"][m][f_idx] = qe_m
            bundle["pe"][m][f_idx] = qe_m
            bundle["E"][m][f_idx] = _spm_norm(qe_m)

    _vb_reset_bundle_O_shell(bundle)


def vb_cold_refresh_child_12bc(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """**ENDGAME-2 tranche 2** — mutable tensor refresh + in-place Q/X/S/P + 12C on cached bundle."""
    vb_refresh_child_bundle_mutable(models, bundle)
    vb_native_refresh_qxsp_priors_only(models, bundle, opts, float(hp["chi"]))
    return vb_cold_setup_12c(models, bundle, opts, hp)


def vb_cold_teardown_child_partial_native(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """**5-C-arena** — nested child partial teardown (12G learning + 12H assemble)."""
    vb_cold_teardown_12gh(models, bundle, opts, hp)


def vb_posterior_predictive_Y_child_optim(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
) -> None:
    """MATLAB ~1591–1606 on nested child path — native ``forwards_dot_A_qj``; Entry12 Yfill probe when active."""
    if int(opts.get("Y", 0)) == 0:
        return
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        if ng_m <= 0:
            continue
        md["Y"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        md["j"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        md["i"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        id_m = bundle["id"][mi]
        for g_1b in range(1, ng_m + 1):
            g_idx = g_1b - 1
            Ag = _vb_fidelity._vb_ag_for_posterior_predictive(md, bundle, mi, g_idx)
            for t_idx in range(t_int):
                Qrow = _vb_fidelity._vb_q_row_for_parents(bundle["Q"][mi], t_idx)
                j, i_ch = spm_parents(id_m, g_1b, Qrow)
                j_store = _vb_fidelity._unwrap_id_a_entry(j)
                j_arr = np.atleast_1d(np.asarray(j_store, dtype=np.float64).ravel())
                if j_arr.size == 1:
                    md["j"][g_idx][t_idx] = float(j_arr[0])
                else:
                    md["j"][g_idx][t_idx] = copy.deepcopy(j_store)
                i_arr = np.atleast_1d(np.asarray(i_ch, dtype=np.float64).ravel())
                if i_arr.size == 1:
                    md["i"][g_idx][t_idx] = float(i_arr[0])
                else:
                    md["i"][g_idx][t_idx] = copy.deepcopy(i_ch)
                q_list = _vb_fidelity._vb_q_list_at_mt(bundle["Q"][mi], j, t_idx)
                pred = np.asarray(forwards_dot_A_qj(Ag, q_list), dtype=np.float64).reshape(-1, 1)
                for o in i_arr.tolist():
                    o_int = int(np.round(float(o)))
                    if o_int < 1 or o_int > ng_m:
                        continue
                    md["Y"][o_int - 1][t_idx] = pred.copy()
    _vb_fidelity._entry12_probe_y_fill_all(models, bundle, opts)


def vb_cold_teardown_child_kernel_native(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """
    **ENDGAME-2** — nested child teardown for hierarchical partial return.

  Parent runs full backwards / neural once at top level. Child still needs per-call
  ``Y`` / ``j`` / ``i`` for hierarchical ``mdp.Q`` append (``.m`` ~1180–1209); skip
  backwards replay and ``OPTIONS.N`` neural on the 128× child stack only.
    """
    _vb_fidelity._vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
    vb_posterior_predictive_Y_child_optim(models, bundle, opts)
    _vb_fidelity._vb_reorganize_X_S_from_QP(bundle)
    vb_cold_assemble_12h(models, bundle)
