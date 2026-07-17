"""Phase **6-A** — native optim cold init for ``Q``/``X``/``S``/``P`` / ``sn`` (``.m`` ~683–752).

Replaces fidelity ``_vb_init_QXSP_outcomes_and_process`` nested ``copy.deepcopy(D/E)``
per time slot with **flat float64 column copies** and ``np.tile`` for ``X``/``S``.

Authority: ``spm_MDP_VB_XXX.m`` ~683–752. Tensor setup (``A``/``B``/``H``/``V``/``GV``) remains
``_vb_tensors_through_H`` until a later tranche ports it.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM.vb_primitives_optim import _spm_sample
from python_src.toolbox.DEM import spm_MDP_VB_XXX as _vb_fidelity

# MDP ``s``/``u``/``o`` + probabilistic ``O{g,t}`` helpers — small fidelity utilities only.
_vb_mdp_field_matrix = _vb_fidelity._vb_mdp_field_matrix
_vb_mdp_O_is_cell_gt_layout = _vb_fidelity._vb_mdp_O_is_cell_gt_layout
_get_mdp_O_gt = _vb_fidelity._get_mdp_O_gt
_vb_monitor_snapshot = _vb_fidelity._vb_monitor_snapshot


def _prior_slots_per_t(prior: Any, t_int: int) -> list[np.ndarray]:
    """``Q{m,f,t}=D`` / ``P{m,f,t}=E`` — one independent float64 column per ``t``, no ``deepcopy`` tree."""
    arr = np.asarray(prior, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return [np.zeros((0,), dtype=np.float64) for _ in range(t_int)]
    return [arr.copy() for _ in range(t_int)]


def _vb_native_qxsp_one_model(
    m: int,
    md: dict[str, Any],
    *,
    bundle: dict[str, Any],
    models: list[dict[str, Any]],
    options: dict[str, Any],
    chi: float,
    t_int: int,
    opt_neural: bool,
    in_place: bool,
    Q: list[list[list[Any]]],
    X: list[list[np.ndarray]],
    S: list[list[np.ndarray]],
    P: list[list[list[Any]]],
    sn: list[list[np.ndarray | None]],
) -> None:
    """Shared 12B Q/X/S/P/sn + s/u/o/O for one model index ``m``."""
    Ng = bundle["Ng"]
    Nf = bundle["Nf"]
    NF = bundle["NF"]
    Ns = bundle["Ns"]
    D_t = bundle["D"]
    E_t = bundle["E"]
    O_shell = bundle["O"]
    proc = bundle["process"]

    nf_m = int(Nf[m])
    ng_m = int(Ng[m])
    nf_proc = int(NF[m])

    if not in_place:
        Q.append([])
        X.append([])
        S.append([])
        P.append([])
        sn.append([])

    for f_idx in range(nf_m):
        Dmf = D_t[m][f_idx]
        Emf = E_t[m][f_idx]
        D_arr = np.asarray(Dmf, dtype=np.float64) if Dmf is not None else np.zeros((0, 0), dtype=np.float64)
        E_arr = np.asarray(Emf, dtype=np.float64) if Emf is not None else np.zeros((0, 0), dtype=np.float64)

        q_cols = _prior_slots_per_t(Dmf, t_int)
        p_cols = _prior_slots_per_t(Emf, t_int)
        if in_place:
            q_slots = bundle["Q"][m][f_idx]
            p_slots = bundle["P"][m][f_idx]
            for t_idx in range(t_int):
                q_slots[t_idx] = q_cols[t_idx]
                p_slots[t_idx] = p_cols[t_idx]
        else:
            Q[m].append(q_cols)
            P[m].append(p_cols)

        if D_arr.size == 0:
            x_new = np.zeros((0, t_int), dtype=np.float64)
        else:
            dcol = np.asarray(D_arr.reshape(-1, 1, order="F"), dtype=np.float64)
            x_new = np.tile(dcol, (1, t_int))
        if in_place:
            x_old = bundle["X"][m][f_idx]
            if x_old.shape == x_new.shape:
                x_old[:, :] = x_new
            else:
                bundle["X"][m][f_idx] = x_new
        else:
            X[m].append(x_new)

        if E_arr.size == 0:
            s_new = np.zeros((0, t_int), dtype=np.float64)
        else:
            ecol = np.asarray(E_arr.reshape(-1, 1, order="F"), dtype=np.float64)
            s_new = np.tile(ecol, (1, t_int))
        if in_place:
            s_old = bundle["S"][m][f_idx]
            if s_old.shape == s_new.shape:
                s_old[:, :] = s_new
            else:
                bundle["S"][m][f_idx] = s_new
        else:
            S[m].append(s_new)

        if opt_neural:
            ns_mf = int(Ns[m, f_idx])
            if ns_mf > 0:
                sn_new = np.zeros((ns_mf, t_int, t_int), dtype=np.float64) + (1.0 / ns_mf)
            else:
                sn_new = np.zeros((0, t_int, t_int), dtype=np.float64)
            if in_place:
                sn_old = bundle["sn"][m][f_idx]
                if (
                    sn_old is not None
                    and isinstance(sn_old, np.ndarray)
                    and sn_old.shape == sn_new.shape
                ):
                    sn_old[:, :, :] = sn_new
                else:
                    bundle["sn"][m][f_idx] = sn_new
            else:
                sn[m].append(sn_new)
        elif not in_place:
            sn[m].append(None)

    _vb_mdp_field_matrix(md, "s", nf_proc, t_int)
    _vb_mdp_field_matrix(md, "u", nf_proc, t_int)
    ng_o_rows = max(ng_m, int(bundle["NG"][m]))
    _vb_mdp_field_matrix(md, "o", ng_o_rows, t_int)

    if "O" in md and _vb_mdp_O_is_cell_gt_layout(md["O"], ng_m, t_int):
        options["O"] = False
        O_src = md["O"]
        for g_idx in range(ng_m):
            for t_idx in range(t_int):
                try:
                    entry = _get_mdp_O_gt(O_src, g_idx, t_idx)
                    O_shell[m][g_idx][t_idx] = entry
                    md["o"][g_idx, t_idx] = float(_spm_sample(entry))
                except Exception:
                    O_shell[m][g_idx][t_idx] = []
                    options["O"] = True

    if _inst._vb_monitoring_active():
        _vb_monitor_snapshot("12B", models[m], m + 1, None, "last")

    if proc[m] > 0:
        models[m]["GV"] = bundle["GV"][m]
        models[m]["chi"] = chi


def vb_native_refresh_qxsp_priors_only(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options: dict[str, Any],
    chi: float,
) -> None:
    """**PASS2 P3** — in-place ``Q``/``X``/``S``/``P`` refresh on cached child bundle (no list rebuild)."""
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    opt_neural = int(options.get("N", 0)) != 0
    Q: list[list[list[Any]]] = []
    X: list[list[np.ndarray]] = []
    S: list[list[np.ndarray]] = []
    P: list[list[list[Any]]] = []
    sn: list[list[np.ndarray | None]] = []
    for m in range(nm):
        _vb_native_qxsp_one_model(
            m,
            models[m],
            bundle=bundle,
            models=models,
            options=options,
            chi=chi,
            t_int=t_int,
            opt_neural=opt_neural,
            in_place=True,
            Q=Q,
            X=X,
            S=S,
            P=P,
            sn=sn,
        )


def vb_native_init_qxsp_outcomes_and_process(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options: dict[str, Any],
    chi: float,
) -> dict[str, Any]:
    """
    Optim-native **6-A** init — same fields as fidelity ``_vb_init_QXSP_outcomes_and_process``.

    ``Q``/``P`` slots are **1-D float64 copies** of ``D``/``E`` priors per ``t`` (``.m`` ~687–701).
    """
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    opt_neural = int(options.get("N", 0)) != 0

    Q: list[list[list[Any]]] = []
    X: list[list[np.ndarray]] = []
    S: list[list[np.ndarray]] = []
    P: list[list[list[Any]]] = []
    sn: list[list[np.ndarray | None]] = []

    for m in range(nm):
        _vb_native_qxsp_one_model(
            m,
            models[m],
            bundle=bundle,
            models=models,
            options=options,
            chi=chi,
            t_int=t_int,
            opt_neural=opt_neural,
            in_place=False,
            Q=Q,
            X=X,
            S=S,
            P=P,
            sn=sn,
        )

    return {"Q": Q, "X": X, "S": S, "P": P, "sn": sn}
