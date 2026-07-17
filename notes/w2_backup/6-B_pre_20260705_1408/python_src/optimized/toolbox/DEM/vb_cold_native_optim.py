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
    Ng = bundle["Ng"]
    Nf = bundle["Nf"]
    NF = bundle["NF"]
    Ns = bundle["Ns"]
    D_t = bundle["D"]
    E_t = bundle["E"]
    O_shell = bundle["O"]
    proc = bundle["process"]

    t_int = int(bundle["T"])

    Q: list[list[list[Any]]] = []
    X: list[list[np.ndarray]] = []
    S: list[list[np.ndarray]] = []
    P: list[list[list[Any]]] = []
    sn: list[list[np.ndarray | None]] = []
    opt_neural = int(options.get("N", 0)) != 0

    for m in range(nm):
        md = models[m]
        nf_m = int(Nf[m])
        ng_m = int(Ng[m])
        nf_proc = int(NF[m])

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

            Q[m].append(_prior_slots_per_t(Dmf, t_int))

            if D_arr.size == 0:
                Xmf = np.zeros((0, t_int), dtype=np.float64)
            else:
                dcol = np.asarray(D_arr.reshape(-1, 1, order="F"), dtype=np.float64)
                Xmf = np.tile(dcol, (1, t_int))
            X[m].append(Xmf)

            if E_arr.size == 0:
                Smf = np.zeros((0, t_int), dtype=np.float64)
            else:
                ecol = np.asarray(E_arr.reshape(-1, 1, order="F"), dtype=np.float64)
                Smf = np.tile(ecol, (1, t_int))
            S[m].append(Smf)

            if opt_neural:
                ns_mf = int(Ns[m, f_idx])
                if ns_mf > 0:
                    sn_mf = np.zeros((ns_mf, t_int, t_int), dtype=np.float64) + (1.0 / ns_mf)
                else:
                    sn_mf = np.zeros((0, t_int, t_int), dtype=np.float64)
                sn[m].append(sn_mf)
            else:
                sn[m].append(None)

            P[m].append(_prior_slots_per_t(Emf, t_int))

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

    for m in range(nm):
        if proc[m] > 0:
            models[m]["GV"] = bundle["GV"][m]
            models[m]["chi"] = chi

    return {"Q": Q, "X": X, "S": S, "P": P, "sn": sn}
