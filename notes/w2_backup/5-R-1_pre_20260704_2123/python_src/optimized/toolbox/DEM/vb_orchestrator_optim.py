"""W2 Tier B — optim-native 12F orchestrator (Phase **3-O**).

**3-O-2 (2026-07-04):** path/state generation + share-states — ``.m`` ~796–909.
**3-O-3 (2026-07-04):** outcomes block — ``.m`` ~911–1009 (+ fill-O seam).
**3-O-4 (2026-07-04):** hierarchical hook + ``BP``/``IP`` — ``.m`` ~1011–1259, ~1224–1256.
**3-O-5 (2026-07-04):** post-forwards belief — ``.m`` ~1264–1409.
**3-O-6 (2026-07-04):** ``id.ig``/``sn`` + terminal trim — ``.m`` ~1418–1443.
**4-W-2 (2026-07-04):** prior ``Q``/``P`` + post-forwards ``P`` in-place on ``VbWorkspace`` (dual-write).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from python_src.spm_cross import spm_cross
from python_src.spm_dot import spm_dot
from python_src.spm_softmax import spm_softmax
from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM import vb_primitives_optim as _prim
from python_src.toolbox.DEM.spm_parents import spm_parents
from python_src.optimized.toolbox.DEM.vb_workspace_optim import (
    ws_copy_p_column,
    ws_get,
    ws_pull_model_q_at_t,
    ws_set_p_column,
    ws_set_p_onehot,
    ws_set_q_column,
)

_spm_sample = _prim._spm_sample
spm_children = _prim.spm_children
_spm_norm = _prim._spm_norm
_spm_action = _prim._spm_action
_spm_log = _prim._spm_log
_spm_one_hot = _prim._spm_one_hot
_unwrap_gp_elem = _prim._unwrap_gp_elem
_vb_gp_transition_column = _prim._vb_gp_transition_column
_vb_gp_A_outcome_column = _prim._vb_gp_A_outcome_column
_vb_gp_outcome_sample_index = _prim._vb_gp_outcome_sample_index
_tensor_nonempty = _prim._tensor_nonempty
_default_options_vb = _prim._default_options_vb
_spm_norm_inplace = _prim._spm_norm_inplace
_spm_wnorm = _prim._spm_wnorm
_spm_hnorm = _prim._spm_hnorm
_vb_workspace_A_like_mdp_shape = _prim._vb_workspace_A_like_mdp_shape


def _gen_u_paths_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """``.m`` ~798–814: initialise/propagate ``MDP(m).u`` over ``NF(m)``."""
    md = models[mi]
    gpm = bundle["gp"][mi]
    nf_gp = int(bundle["NF"][mi])
    for f_idx in range(nf_gp):
        if float(md["u"][f_idx, t_idx]) != 0.0:
            continue
        if t_idx > 0:
            md["u"][f_idx, t_idx] = float(md["u"][f_idx, t_idx - 1])
        else:
            Ef = _unwrap_gp_elem(gpm["E"][f_idx])
            pu = _spm_norm(Ef)
            if int(np.asarray(pu).size) == 0:
                continue
            md["u"][f_idx, t_idx] = float(_spm_sample(pu))


def _prior_qp_paths_states_one_model(
    mi: int,
    bundle: dict[str, Any],
    t_idx: int,
    Pu_vec: np.ndarray,
) -> None:
    """``.m`` ~819–842: policy ``Pu``, update ``P`` / ``Q`` over generative ``Nf`` factors."""
    Um = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
    vd = bundle["V"][mi].toarray()
    nf_gen = int(bundle["Nf"][mi])
    Nu_m = bundle["Nu"]
    Q_all = bundle["Q"]
    P_all = bundle["P"]
    B_t = bundle["B"]

    pu_col = np.asarray(Pu_vec, dtype=np.float64).reshape(-1, 1)
    if pu_col.size == 0:
        pu_col = np.ones((1, 1), dtype=np.float64)
    k_pol = int(_spm_sample(pu_col))

    ws = ws_get(bundle)

    for f_idx in range(nf_gen):
        if f_idx < Um.size and float(Um[f_idx]) != 0.0:
            if vd.shape[0] == 0:
                continue
            u_mark = int(round(float(vd[k_pol - 1, f_idx])))
            if ws is not None:
                ws_set_p_onehot(ws, bundle, mi, f_idx, t_idx - 1, u_mark)
            else:
                P_arr = np.asarray(P_all[mi][f_idx][t_idx - 1], dtype=np.float64).ravel()
                P_arr[:] = 0.0
                if 1 <= u_mark <= P_arr.size:
                    P_arr[u_mark - 1] = 1.0
                P_all[mi][f_idx][t_idx - 1] = P_arr.reshape(-1, 1)

        nu_mf = int(Nu_m[mi, f_idx])
        if ws is not None:
            Q_prev = ws.Q[mi][f_idx][:, t_idx - 1].copy()
        else:
            Q_prev = np.asarray(Q_all[mi][f_idx][t_idx - 1], dtype=np.float64)
        Bmf = B_t[mi][f_idx]
        if nu_mf > 1:
            P_prev = P_all[mi][f_idx][t_idx - 1]
            tp = np.asarray(spm_dot(Bmf, [P_prev]), dtype=np.float64)
            Q_new = tp @ Q_prev
        else:
            Bm = np.asarray(_unwrap_gp_elem(Bmf), dtype=np.float64)
            Q_new = Bm @ Q_prev
        if ws is not None:
            ws_set_q_column(ws, bundle, mi, f_idx, t_idx, Q_new)
        else:
            Q_all[mi][f_idx][t_idx] = Q_new

    bundle["_entry12_last_k_pol"] = k_pol
    bundle["_entry12_last_Pu"] = pu_col


def _gen_control_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """``.m`` ~848–866: ``spm_action`` (process) or sample ``u(:,t-1)`` from ``P``."""
    md = models[mi]
    if float(bundle["process"][mi]) > 0.0:
        if "GV" not in md:
            raise NotImplementedError(
                "spm_MDP_VB_XXX: process model without GV (nested spm_action requires GV)"
            )
        t_int = int(bundle["T"])
        nf = int(bundle["Nf"][mi])
        A_list = bundle["A"][mi]
        Q_all = bundle["Q"]
        Q_slice = [Q_all[mi][f][t_idx] for f in range(nf)]
        nf_gp = len(md["GB"])
        for key, fill in (("u", 1.0), ("s", 1.0)):
            if key not in md or md[key] is None:
                md[key] = np.full((nf_gp, t_int), fill, dtype=np.float64)
            else:
                arr = np.asarray(md[key], dtype=np.float64)
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)
                if arr.shape[0] < nf_gp:
                    arr = np.vstack(
                        [arr, np.full((nf_gp - arr.shape[0], arr.shape[1]), fill, dtype=np.float64)]
                    )
                if arr.shape[1] < t_int:
                    arr = np.hstack(
                        [arr, np.full((arr.shape[0], t_int - arr.shape[1]), fill, dtype=np.float64)]
                    )
                md[key] = arr
        _spm_action(md, A_list, Q_slice, t_idx)
        return
    idm = bundle["id"][mi]
    P_all = bundle["P"]
    fu = np.asarray(idm.get("fu", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    for f_1 in fu:
        f_idx = int(f_1) - 1
        md["u"][f_idx, t_idx - 1] = float(_spm_sample(P_all[mi][f_idx][t_idx - 1]))


def _gen_states_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """``.m`` ~872–893: sample ``s`` from ``GP.B`` / ``GP.D`` over ``NF(m)``."""
    md = models[mi]
    gpm = bundle["gp"][mi]
    nf_gp = int(bundle["NF"][mi])
    for f_idx in range(nf_gp):
        if float(md["s"][f_idx, t_idx]) != 0.0:
            continue
        if t_idx > 0:
            Bg = gpm["B"][f_idx]
            su = int(round(float(md["s"][f_idx, t_idx - 1])))
            uu = int(round(float(md["u"][f_idx, t_idx - 1])))
            ps = _vb_gp_transition_column(Bg, su, uu)
        else:
            Df = _unwrap_gp_elem(gpm["D"][f_idx])
            ps = _spm_norm(Df)
        md["s"][f_idx, t_idx] = float(_spm_sample(ps))


def vb_orchestrator_generation_paths_states(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """Optim 12F path/state generation — ``.m`` ~794–895."""
    nm = int(bundle.get("Nm", len(models)))
    bundle.setdefault("Pu_carry", [None] * nm)
    Pu_carry: list[Any] = bundle["Pu_carry"]

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        _gen_u_paths_one_model(mi, models, bundle, t_idx)
        if t_idx > 0:
            pu_v = Pu_carry[mi]
            if pu_v is None:
                npp = int(bundle["Np"][mi])
                pu_v = np.ones((max(1, npp), 1), dtype=np.float64)
            _prior_qp_paths_states_one_model(mi, bundle, t_idx, np.asarray(pu_v, dtype=np.float64))
            if _inst._vb_dump_active():
                k_pol = int(bundle.get("_entry12_last_k_pol", 1))
                pu_rec = np.asarray(bundle.get("_entry12_last_Pu", pu_v), dtype=np.float64)
                _inst._entry12_record_phase(
                    mi,
                    t_idx + 1,
                    "post_generation",
                    bundle,
                    extra={
                        "k_policy": k_pol,
                        "Pu": _prim._vb_as_float64_array(pu_rec).ravel().tolist(),
                    },
                )
            _gen_control_one_model(mi, models, bundle, t_idx)
        _gen_states_one_model(mi, models, bundle, t_idx)


def vb_orchestrator_share_states_one_t(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """Optim share-states — ``.m`` ~900–909 via ``MDP(m).m``."""
    NF_arr = bundle["NF"]
    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        if "m" not in md:
            continue
        m_src = np.asarray(md["m"], dtype=np.float64).ravel()
        nf_gp = int(NF_arr[mi])
        for f_idx in range(min(nf_gp, int(m_src.size))):
            n_agent = int(round(float(m_src[f_idx])))
            if n_agent > 0:
                md["s"][f_idx, t_idx] = float(models[n_agent - 1]["s"][f_idx, t_idx])


def vb_orchestrator_generate_outcomes_if_options_o(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """Optim outcomes generation — ``.m`` ~911–985 (``OPTIONS.O``)."""
    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("O", 1)) == 0:
        return

    ID_list = bundle["ID"]
    gp_list = bundle["gp"]
    O_shell = bundle["O"]
    NG_arr = bundle["NG"]
    t_int = int(bundle["T"])
    Fm_store: dict[tuple[int, int, int], np.ndarray] = bundle.setdefault("_vb_Fm_neg_t_o_m", {})

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        gpm = gp_list[mi]
        ng_gen = int(NG_arr[mi])
        n_shell = len(O_shell[mi])
        ng_loop = min(ng_gen, n_shell)
        n_o_rows = int(md["o"].shape[0]) if isinstance(md.get("o"), np.ndarray) else ng_gen
        n_mat = np.asarray(md.get("n", np.zeros((max(ng_gen, n_o_rows), t_int))), dtype=np.float64)
        if n_mat.size == 0:
            n_mat = np.zeros((ng_loop, t_int), dtype=np.float64)
        if n_mat.ndim == 1:
            n_mat = n_mat.reshape(-1, 1)
        if n_mat.shape[0] < ng_loop:
            pad = np.zeros((ng_loop, t_int), dtype=np.float64)
            pad[: n_mat.shape[0], :] = n_mat
            n_mat = pad
        if n_mat.shape[1] < t_int:
            pad = np.zeros((n_mat.shape[0], t_int), dtype=np.float64)
            pad[:, : n_mat.shape[1]] = n_mat
            n_mat = pad

        for g_idx in range(ng_loop):
            g_1 = g_idx + 1
            s_col = np.asarray(md["s"][:, t_idx], dtype=np.float64).reshape(-1, 1)
            j_p, i_ch = spm_parents(ID_list[mi], g_1, s_col)
            i_vals = np.atleast_1d(np.asarray(i_ch, dtype=float)).ravel().tolist()
            for o_1based in i_vals:
                o_idx = int(round(float(o_1based))) - 1
                if o_idx < 0 or o_idx >= n_shell or o_idx >= n_o_rows:
                    continue
                if float(md["o"][o_idx, t_idx]) != 0.0:
                    if not _tensor_nonempty(O_shell[mi][o_idx][t_idx]):
                        no_mo = int(bundle["No"][mi, o_idx])
                        oi = int(round(float(md["o"][o_idx, t_idx])))
                        if no_mo > 0 and oi > 0 and oi <= no_mo:
                            O_shell[mi][o_idx][t_idx] = _spm_one_hot(oi, no_mo)
                    continue
                n_ot = float(n_mat[o_idx, t_idx])

                if n_ot > 0:
                    ni = int(round(n_ot)) - 1
                    if ni == mi:
                        j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                        q_list = [bundle["Q"][mi][int(jv) - 1][t_idx] for jv in j_arr if int(jv) > 0]
                        Amg = _unwrap_gp_elem(bundle["A"][mi][g_idx])
                        if callable(Amg) and not isinstance(Amg, np.ndarray):
                            raise NotImplementedError(
                                "OPTIONS.O: likelihood function_handle A{g} not translated"
                            )
                        F = np.asarray(spm_dot(Amg, q_list), dtype=np.float64).reshape(-1, 1)
                        Fl = np.asarray(_spm_log(F), dtype=np.float64).reshape(-1, 1)
                        Ocell = np.asarray(spm_softmax(Fl * 512.0), dtype=np.float64).reshape(-1, 1)
                        O_shell[mi][o_idx][t_idx] = Ocell
                        md["o"][o_idx, t_idx] = float(_spm_sample(Ocell))
                    else:
                        O_shell[mi][o_idx][t_idx] = O_shell[ni][o_idx][t_idx]
                        md["o"][o_idx, t_idx] = float(models[ni]["o"][o_idx, t_idx])
                    continue

                if n_ot < 0:
                    j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                    q_list = [bundle["Q"][mi][int(jv) - 1][t_idx] for jv in j_arr if int(jv) > 0]
                    Amg = _unwrap_gp_elem(bundle["A"][mi][g_idx])
                    if callable(Amg) and not isinstance(Amg, np.ndarray):
                        raise NotImplementedError(
                            "OPTIONS.O: likelihood function_handle A{g} not translated (Fm branch)"
                        )
                    Fm_store[(t_idx, o_idx, mi)] = np.asarray(
                        _spm_log(np.asarray(spm_dot(Amg, q_list), dtype=np.float64)),
                        dtype=np.float64,
                    ).reshape(-1, 1)
                    continue

                Ag_raw = _unwrap_gp_elem(gpm["A"][g_idx])
                if callable(Ag_raw) and not isinstance(Ag_raw, np.ndarray):
                    raise NotImplementedError("OPTIONS.O: GP.A{g} function_handle not translated")
                j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                ind_parts: list[int] = []
                for jx in j_arr:
                    jxi = int(round(float(jx)))
                    sv = float(md["s"][jxi - 1, t_idx])
                    ind_parts.append(int(round(sv)) - 1)
                col = _vb_gp_A_outcome_column(Ag_raw, ind_parts)
                k_out = _vb_gp_outcome_sample_index(col)
                O_shell[mi][o_idx][t_idx] = np.asarray(col, dtype=np.float64).reshape(-1, 1, order="F")
                md["o"][o_idx, t_idx] = float(k_out)


def vb_orchestrator_shared_probabilistic_outcomes(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """Optim shared probabilistic outcomes — ``.m`` ~992–1009."""
    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("O", 1)) == 0:
        return

    Fm_store: dict[tuple[int, int, int], np.ndarray] = bundle.get("_vb_Fm_neg_t_o_m", {})
    O_shell = bundle["O"]
    Ng_arr = bundle["Ng"]
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        ng_m = int(Ng_arr[mi])
        n_mat = np.asarray(md.get("n", np.zeros((ng_m, t_int))), dtype=np.float64)
        if n_mat.size == 0:
            n_mat = np.zeros((ng_m, t_int), dtype=np.float64)
        if n_mat.ndim == 1:
            n_mat = n_mat.reshape(ng_m, -1)
        if n_mat.shape[0] < ng_m:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[: n_mat.shape[0], :] = n_mat
            n_mat = pad
        if n_mat.shape[1] < t_int:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[:, : n_mat.shape[1]] = n_mat
            n_mat = pad

        for g_idx in range(ng_m):
            if float(n_mat[g_idx, t_idx]) >= 0.0:
                continue
            acc: np.ndarray | None = None
            for j_other in range(nm):
                if j_other == mi:
                    continue
                key = (t_idx, g_idx, j_other)
                vec = Fm_store.get(key)
                if vec is None:
                    continue
                v = np.asarray(vec, dtype=np.float64).reshape(-1, 1)
                acc = v.copy() if acc is None else (acc + v)
            if acc is None:
                continue
            F = acc
            O_dist = np.asarray(spm_softmax(F), dtype=np.float64).reshape(-1, 1)
            po = np.asarray(spm_softmax(F * 512.0), dtype=np.float64).reshape(-1, 1)
            O_shell[mi][g_idx][t_idx] = O_dist
            md["o"][g_idx, t_idx] = float(_spm_sample(po))


def _fill_O_empty_from_realized_o(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    mi: int,
) -> None:
    """``.m`` ~973–979: one-hot ``O{m,o,t}`` from realized ``o`` when ``O`` empty."""
    md = models[mi]
    O_m = bundle["O"][mi]
    ng_m = len(O_m)
    for o_idx in range(ng_m):
        if _tensor_nonempty(O_m[o_idx][t_idx]):
            continue
        if float(md["o"][o_idx, t_idx]) == 0.0:
            continue
        no_mo = int(bundle["No"][mi, o_idx])
        oi = int(round(float(md["o"][o_idx, t_idx])))
        if no_mo > 0 and 0 < oi <= no_mo:
            O_m[o_idx][t_idx] = _spm_one_hot(oi, no_mo)


def vb_orchestrator_fill_O_empty_from_realized_o_at_t(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """12E→12F seam: fill empty ``O`` shells from realized ``o`` — ``.m`` ~977–978."""
    for mm in np.asarray(M_row, dtype=np.int64).ravel():
        mi = int(mm) - 1
        if mi >= 0:
            _fill_O_empty_from_realized_o(models, bundle, t_idx, mi)


def vb_orchestrator_hierarchical_subordinate_outcomes(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
    recurse_partial: bool,
    *,
    reuse_matlab_draws: bool = False,
) -> None:
    """Optim hierarchical subordinate outcomes — direct Tier A call (``.m`` ~1011–1259)."""
    from python_src.optimized.toolbox.DEM.vb_hierarchical_optim import (
        vb_hierarchical_subordinate_outcomes_optim,
    )

    vb_hierarchical_subordinate_outcomes_optim(
        models,
        bundle,
        t_idx,
        M_row,
        recurse_partial,
        reuse_matlab_draws=reuse_matlab_draws,
    )


def vb_orchestrator_fill_BP_IP_at_t(bundle: dict[str, Any], t_idx: int) -> None:
    """Belief propagators ``BP`` / ``IP`` from ``B``, ``I``, ``V``, ``P`` — ``.m`` ~1224–1256."""
    nm = int(bundle["Nm"])
    Nf = bundle["Nf"]
    Nu = bundle["Nu"]
    Um_list = bundle["Um"]
    V_list = bundle["V"]
    B_t = bundle["B"]
    I_t = bundle["I"]
    P_all = bundle["P"]
    BP = bundle["BP"]
    IP = bundle["IP"]
    Np = bundle["Np"]

    for m in range(nm):
        nf_m = int(Nf[m])
        npp = int(Np[m])
        Um = np.asarray(Um_list[m], dtype=np.float64).ravel()
        V_csr = V_list[m]
        vd = V_csr.toarray()

        for f_idx in range(nf_m):
            controllable = f_idx < Um.size and float(Um[f_idx]) != 0.0
            Bmf = _unwrap_gp_elem(B_t[m][f_idx])
            Imf = I_t[m][f_idx]

            if controllable:
                Barr = np.asarray(Bmf, dtype=np.float64)
                if Barr.ndim == 2:
                    Barr = Barr[:, :, np.newaxis]
                Iarr = None
                if _tensor_nonempty(Imf):
                    Iarr = np.asarray(_unwrap_gp_elem(Imf), dtype=np.float64)
                    if Iarr.ndim == 2:
                        Iarr = Iarr[:, :, np.newaxis]
                for k in range(npp):
                    u_sel = int(round(float(vd[k, f_idx])))
                    if u_sel < 1:
                        u_sel = 1
                    nu_third = Barr.shape[2]
                    if u_sel > nu_third:
                        u_sel = nu_third
                    BP[m][f_idx][k] = np.asarray(Barr[:, :, u_sel - 1], dtype=np.float64)
                    if Iarr is not None:
                        IP[m][f_idx][k] = np.asarray(Iarr[:, :, u_sel - 1], dtype=np.float64)
            else:
                Pmf_t = P_all[m][f_idx][t_idx]
                if int(Nu[m, f_idx]) > 1:
                    BP[m][f_idx][0] = spm_dot(Bmf, [Pmf_t])
                    if _tensor_nonempty(Imf):
                        dotted = spm_dot(Imf, [Pmf_t])
                        for k in range(npp):
                            IP[m][f_idx][k] = dotted
                else:
                    BP[m][f_idx][0] = np.asarray(Bmf, dtype=np.float64)
                    if _tensor_nonempty(Imf):
                        Imf_u = _unwrap_gp_elem(Imf)
                        for k in range(npp):
                            IP[m][f_idx][k] = np.asarray(Imf_u, dtype=np.float64)


def vb_orchestrator_ensure_per_t_traces(models: list[dict[str, Any]], mi: int, t_int: int) -> None:
    """Preallocate ``MDP(m).F`` / ``G`` / ``Z`` trace slots — ``.m`` ~1412–1416."""
    md = models[mi]
    gg = md.get("G")
    if gg is None or not isinstance(gg, list):
        md["G"] = [None] * t_int
    elif len(gg) < t_int:
        md["G"] = list(gg) + [None] * (t_int - len(gg))
    ff = md.get("F")
    if ff is None or (not isinstance(ff, np.ndarray)) or (int(ff.size) != t_int):
        md["F"] = np.zeros((t_int,), dtype=np.float64)
    zz = md.get("Z")
    if zz is None or (not isinstance(zz, np.ndarray)) or (int(zz.size) != t_int):
        md["Z"] = np.zeros((t_int,), dtype=np.float64)


def vb_orchestrator_belief_after_forwards(
    mi: int,
    bundle: dict[str, Any],
    t_m: int,
    t_idx: int,
    G_m: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, float]:
    """Post-``spm_forwards`` policy/path update — ``.m`` ~1264–1395."""
    Pu_carry: list[Any] = bundle["Pu_carry"]
    npp = int(bundle["Np"][mi])
    G_flat = np.asarray(G_m, dtype=np.float64).copy().ravel(order="F")
    if npp > 0:
        G_work = G_flat.reshape(npp, -1, order="F")
        if G_work.shape[1] != 1:
            G_work = np.sum(G_work, axis=1, keepdims=True)
        G_work = G_work.reshape(npp, 1)
        G_for_R = G_work
        n_rows_r = npp
    else:
        G_work = np.zeros((0, 1), dtype=np.float64)
        if G_flat.size == 0:
            G_for_R = np.zeros((1, 1), dtype=np.float64)
        else:
            G_for_R = np.asarray(G_flat.reshape(-1, 1)[:1], dtype=np.float64)
        n_rows_r = 1

    V_csr = bundle["V"][mi]
    Vd = V_csr.toarray()
    Um_row = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
    E_list = bundle["gp"][mi]["E"]
    nf_m = int(bundle["Nf"][mi])
    Nu_arr = bundle["Nu"]

    if t_m == 1:
        for k in range(npp):
            le_acc = 0.0
            for f_idx in range(nf_m):
                if f_idx >= Um_row.size or Um_row[f_idx] == 0.0:
                    continue
                Ef = np.asarray(_unwrap_gp_elem(E_list[f_idx]), dtype=np.float64).reshape(-1, 1, order="F")
                vk = int(round(float(Vd[k, f_idx])))
                if vk < 1 or vk > Ef.shape[0]:
                    continue
                ev = float(Ef[vk - 1, 0])
                le_acc += float(np.asarray(_spm_log(np.array([[ev]], dtype=np.float64))).reshape(-1)[0])
            G_work[k, 0] += le_acc

    if bundle["R_policy"][mi].shape[0] < n_rows_r:
        old = np.asarray(bundle["R_policy"][mi], dtype=np.float64)
        grown = np.zeros((n_rows_r, old.shape[1]), dtype=np.float64)
        if old.size:
            grown[: old.shape[0], :] = old
        bundle["R_policy"][mi] = grown
    R_col = np.asarray(spm_softmax(G_for_R), dtype=np.float64).reshape(n_rows_r, 1)
    bundle["R_policy"][mi][:n_rows_r, t_idx] = R_col.reshape(-1)
    bundle["w_policy"][mi][t_idx] = float(
        (R_col.T @ np.asarray(_spm_log(R_col), dtype=np.float64).reshape(-1, 1)).reshape(-1)[0]
    )
    bundle["v_policy"][mi][t_idx] = float((R_col.T @ G_for_R).reshape(-1)[0])

    Q_all = bundle["Q"]
    P_all = bundle["P"]
    B_t = bundle["B"]
    ws = ws_get(bundle)

    Z_acc = 0.0
    if t_m > 1:
        for f_idx in range(nf_m):
            nu_mf = int(Nu_arr[mi, f_idx])
            if nu_mf > 1:
                Bmf = _unwrap_gp_elem(B_t[mi][f_idx])
                if ws is not None:
                    Qt = ws.Q[mi][f_idx][:, t_idx].reshape(-1, 1, order="F")
                    Qtm1 = ws.Q[mi][f_idx][:, t_idx - 1].reshape(-1, 1, order="F")
                    LP = np.asarray(
                        _spm_log(ws.P[mi][f_idx][:, t_idx - 1]), dtype=np.float64
                    ).reshape(-1, 1)
                else:
                    Qt = np.asarray(Q_all[mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1, order="F")
                    Qtm1 = np.asarray(Q_all[mi][f_idx][t_idx - 1], dtype=np.float64).reshape(-1, 1, order="F")
                    LP = np.asarray(_spm_log(P_all[mi][f_idx][t_idx - 1]), dtype=np.float64).reshape(-1, 1)
                LL = np.asarray(spm_dot(spm_dot(Bmf, Qt), Qtm1), dtype=np.float64)
                LL = np.asarray(_spm_log(LL), dtype=np.float64).reshape(-1, 1)
                post = np.asarray(spm_softmax(LL + LP), dtype=np.float64).reshape(-1, 1)
                if ws is not None:
                    ws_set_p_column(ws, bundle, mi, f_idx, t_idx - 1, post)
                else:
                    P_all[mi][f_idx][t_idx - 1] = post
                logp = np.asarray(_spm_log(post), dtype=np.float64).reshape(-1, 1)
                Z_acc += float((post.T @ (LL + LP - logp)).reshape(-1)[0])
            else:
                if ws is not None:
                    ws_set_p_column(
                        ws, bundle, mi, f_idx, t_idx - 1, np.array([1.0], dtype=np.float64)
                    )
                else:
                    P_all[mi][f_idx][t_idx - 1] = np.array([[1.0]], dtype=np.float64)

    if npp > 0:
        Pu = np.asarray(spm_softmax(G_work, float(alpha)), dtype=np.float64).reshape(npp, 1)
    else:
        g1 = G_flat.reshape(1, 1) if G_flat.size == 1 else np.zeros((1, 1), dtype=np.float64)
        Pu = np.asarray(spm_softmax(g1, float(alpha)), dtype=np.float64).reshape(1, 1)
    Pu_carry[mi] = Pu

    for f_idx in range(nf_m):
        if f_idx < Um_row.size and Um_row[f_idx] != 0.0:
            nu = int(Nu_arr[mi, f_idx])
            col = np.zeros((nu, 1), dtype=np.float64)
            for u in range(1, nu + 1):
                mask = (Vd[:, f_idx] == float(u)).astype(np.float64).reshape(npp, 1)
                col[u - 1, 0] = float((Pu.T @ mask).reshape(-1)[0])
            if ws is not None:
                ws_set_p_column(ws, bundle, mi, f_idx, t_idx, col)
            else:
                P_all[mi][f_idx][t_idx] = col
        else:
            if t_m > 1:
                if ws is not None:
                    ws_copy_p_column(ws, bundle, mi, f_idx, t_idx, t_idx - 1)
                else:
                    P_all[mi][f_idx][t_idx] = np.asarray(
                        P_all[mi][f_idx][t_idx - 1], dtype=np.float64
                    ).copy()

    if npp > 0:
        gw_out = np.asarray(G_work, dtype=np.float64).copy()
    elif G_flat.size >= 1:
        gw_out = np.asarray(G_flat, dtype=np.float64).copy().reshape(-1, 1)
    else:
        gw_out = np.asarray(G_for_R, dtype=np.float64).reshape(-1, 1).copy()
    return gw_out, float(Z_acc)


def vb_orchestrator_active_learning_in_loop(
    mi: int,
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    t_m: int,
) -> None:
    """Online Dirichlet ``a``/``b`` updates — ``.m`` ~1398–1455."""
    md = models[mi]
    id_m = bundle["id"][mi]
    nf_m = int(bundle["Nf"][mi])
    O_m = bundle["O"][mi]
    Q_row: list[Any] = [bundle["Q"][mi][f][t_idx] for f in range(nf_m)]

    if "a" in md:
        for g_1 in np.ravel(spm_children(id_m)).astype(np.int64):
            g_idx = int(g_1) - 1
            if g_idx < 0:
                continue
            jdom, kcod = spm_parents(id_m, int(g_1), Q_row)
            k_flat = np.atleast_1d(np.asarray(kcod, dtype=np.float64).ravel()).astype(np.int64).ravel()
            if k_flat.size == 0:
                continue
            j_flat = np.atleast_1d(np.asarray(jdom, dtype=np.float64).ravel()).astype(np.int64).ravel()
            if j_flat.size == 0:
                continue
            q_parts: list[np.ndarray] = []
            for jj in j_flat:
                ji = int(jj)
                if ji < 1 or ji > nf_m:
                    continue
                q_parts.append(np.asarray(Q_row[ji - 1], dtype=np.float64))
            if not q_parts:
                continue
            if len(q_parts) == 1:
                Qj = q_parts[0]
            else:
                Qj = spm_cross(*q_parts)

            qa_slot = bundle["qa"][mi][g_idx]
            qa_base = _unwrap_gp_elem(qa_slot)
            qa_arr = np.asarray(qa_base, dtype=np.float64)
            if qa_arr.size == 0:
                continue
            da = np.zeros_like(qa_arr, dtype=np.float64)
            for i_out in k_flat:
                io = int(i_out)
                if io < 1:
                    continue
                ocell = O_m[io - 1][t_idx]
                if ocell is None or not _tensor_nonempty(ocell):
                    continue
                Oi = np.asarray(ocell, dtype=np.float64)
                term = np.asarray(spm_cross(Oi, Qj), dtype=np.float64)
                if int(term.size) != int(qa_arr.size):
                    raise ValueError(
                        f"spm_MDP_VB_XXX: spm_cross(O,Qj) numel {int(term.size)} != qa numel {int(qa_arr.size)} "
                        f"(m={mi + 1}, g={g_1}, t={t_idx + 1})"
                    )
                if term.shape != qa_arr.shape:
                    term = np.reshape(term, qa_arr.shape, order="F")
                da = da + term
            supp = qa_arr != 0.0
            da = np.where(supp, da, 0.0)
            qa_new = np.asarray(qa_arr + da, dtype=np.float64)
            if not qa_new.flags.writeable:
                qa_new = np.asarray(qa_arr + da, dtype=np.float64).copy(order="F")
            _spm_norm_inplace(qa_new)
            if "A" in md:
                Agf = md["A"][g_idx]
                Agf = Agf[0] if isinstance(Agf, list) and len(Agf) == 1 else Agf
                if isinstance(Agf, np.ndarray) and Agf.dtype == bool:
                    qa_new = qa_new.astype(bool)
            if isinstance(qa_slot, list) and len(qa_slot) == 1:
                qa_slot[0] = qa_new
            else:
                bundle["qa"][mi][g_idx] = qa_new
            qa_a = (
                _vb_workspace_A_like_mdp_shape(qa_new, md["A"][g_idx])
                if "A" in md
                else qa_new
            )
            A_slot = bundle["A"][mi][g_idx]
            if isinstance(A_slot, list) and len(A_slot) == 1:
                A_slot[0] = qa_a
            else:
                bundle["A"][mi][g_idx] = qa_a
            bundle["W"][mi][g_idx] = _spm_wnorm(qa_new)
            bundle["K"][mi][g_idx] = _spm_hnorm(qa_new)

    if "b" in md and t_m > 1:
        for f_idx in range(nf_m):
            Qt = np.asarray(bundle["Q"][mi][f_idx][t_idx], dtype=np.float64)
            Qtm1 = np.asarray(bundle["Q"][mi][f_idx][t_idx - 1], dtype=np.float64)
            Ptm1 = np.asarray(bundle["P"][mi][f_idx][t_idx - 1], dtype=np.float64)
            db = np.asarray(
                spm_cross(spm_cross(Qt, Qtm1), Ptm1),
                dtype=np.float64,
            )
            qb_slot = bundle["qb"][mi][f_idx]
            qb_arr = np.asarray(_unwrap_gp_elem(qb_slot), dtype=np.float64)
            if qb_arr.size == 0:
                continue
            if db.shape != qb_arr.shape:
                db = np.reshape(db, qb_arr.shape, order="F")
            supp_b = qb_arr != 0.0
            db = np.where(supp_b, db, 0.0)
            qb_new = qb_arr + db
            if isinstance(qb_slot, list) and len(qb_slot) == 1:
                qb_slot[0] = qb_new
            else:
                bundle["qb"][mi][f_idx] = qb_new
            B_norm = _spm_norm(qb_new)
            if "B" in md:
                Bgf = md["B"][f_idx]
                Bgf = Bgf[0] if isinstance(Bgf, list) and len(Bgf) == 1 else Bgf
                if isinstance(Bgf, np.ndarray) and Bgf.dtype == bool:
                    B_norm = B_norm.astype(bool)
            bundle["B"][mi][f_idx] = B_norm
            I_w = _spm_wnorm(qb_new)
            bundle["I"][mi][f_idx] = I_w
            if "b" in md:
                b_sl = md["b"][f_idx]
                if isinstance(b_sl, list) and len(b_sl) == 1:
                    b_sl[0] = qb_new.copy()
                else:
                    md["b"][f_idx] = qb_new.copy()
            if "B" in md:
                bg = md["B"][f_idx]
                bn = np.array(B_norm, copy=True)
                if isinstance(bg, list) and len(bg) == 1:
                    bg[0] = bn
                else:
                    md["B"][f_idx] = bn


def vb_orchestrator_in_loop_id_ig_and_sn(
    mi: int,
    bundle: dict[str, Any],
    t_idx: int,
) -> None:
    """``id.ig`` and ``sn`` when ``OPTIONS.N`` — ``.m`` ~1418–1431."""
    t_int = int(bundle["T"])
    id_m = bundle["id"][mi]
    if "i" in id_m:
        if "ig" not in id_m or id_m["ig"] is None:
            id_m["ig"] = np.zeros((t_int,), dtype=np.float64)
        else:
            ig0 = np.asarray(id_m["ig"], dtype=np.float64).ravel()
            if ig0.size < t_int:
                id_m["ig"] = np.concatenate([ig0, np.zeros(t_int - ig0.size, dtype=np.float64)])
            else:
                id_m["ig"] = ig0[:t_int].copy()
        iv = np.asarray(id_m["i"], dtype=np.float64).ravel()
        id_m["ig"][t_idx] = float(iv[0]) if iv.size > 0 else 0.0

    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("N", 0)) == 0:
        return
    sn_all = bundle.get("sn")
    if sn_all is None:
        return
    for f_idx in range(int(bundle["Nf"][mi])):
        snmf = sn_all[mi][f_idx]
        if snmf is None:
            continue
        ns = int(snmf.shape[0])
        for ii in range(t_int):
            q_src = np.asarray(bundle["Q"][mi][f_idx][ii], dtype=np.float64).reshape(-1)
            if ns <= 0:
                continue
            take = min(ns, int(q_src.size))
            if take <= 0:
                continue
            snmf[:take, ii, t_idx] = q_src[:take]
            if take < ns:
                snmf[take:, ii, t_idx] = 0.0


def vb_orchestrator_trim_mdp_o_s_u_at_terminal_horizon(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> None:
    """When ``t == T``: keep first ``T`` columns of ``o``/``s``/``u`` — ``.m`` ~1438–1443."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    Ng = bundle["Ng"]
    NF = bundle["NF"]
    for mi in range(nm):
        md = models[mi]
        ng_m = int(Ng[mi])
        nf_m = int(NF[mi])
        for key, n_rows in (("o", ng_m), ("s", nf_m), ("u", nf_m)):
            if key not in md:
                continue
            arr = np.asarray(md[key], dtype=np.float64)
            if arr.ndim < 2:
                continue
            if arr.shape[1] > t_int:
                md[key] = np.asarray(arr[:, :t_int], dtype=np.float64).copy()
