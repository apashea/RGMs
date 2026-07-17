"""ENDGAME-1 — unified parent policy engine on ``VbWorkspace``.

Single hot-path seam: **VBX → induction → overt-policy ``G`` → EFE recursion** (``.m`` ``spm_forwards``).
Hoisted ``B{m,f,k}`` stacks live in ``_ForwardsModelStatic.B_fk_stacked`` (once per model, not per call).

**Tranche 4 (2026-07-06):** hoisted induction ``b_map``/``Bf``/``Pf`` via ``InductionModelStatic``;
``pf_at_t`` from post-VBX ``Q_upd`` (no ws re-read); hoisted ``B_fp0`` for ``id_fp``.

Gate: ``--vb-optim-tier3f``.
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM import vb_primitives_optim as _prim
from python_src.optimized.toolbox.DEM.vb_contract_optim import (
    forwards_dot_A_qj as _forwards_dot_A_qj,
    forwards_dot_R_qcells as _forwards_dot_R_qcells,
    forwards_dot_vec_match as _forwards_dot_vec_match,
)
from python_src.optimized.toolbox.DEM.vb_forwards_optim import (
    _EXP_NEG8,
    _ForwardsModelStatic,
    _ForwardsRunCtx,
    _efe_memo_key,
    _fwd_col_vec,
    _fwd_p_row,
    _fwd_write_belief_col,
    _induction_cached,
    _vbx_belief_row_ws_writable,
)
from python_src.optimized.toolbox.DEM.vb_VBX_optim import spm_VBX_optim as spm_VBX
from python_src.optimized.toolbox.DEM.vb_workspace_optim import (
    VbWorkspace,
    ws_assign_o_slot,
    ws_o_row_at_t,
    ws_q_zero_inactive_tail,
)
from python_src.spm_cross import spm_cross
from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_MDP_BMR import spm_MDP_BMR
from python_src.toolbox.DEM.spm_index import spm_index
from python_src.toolbox.DEM.spm_parents import spm_parents


def _pf_from_q_upd(Q_upd: list[Any], nf: int) -> dict[int, np.ndarray]:
    """Post-VBX belief columns — ``(n,1)`` float64 (**ENDGAME-1 t4**, no ws re-read)."""
    return {
        f: np.asarray(Q_upd[f], dtype=np.float64).reshape(-1, 1, order="F")
        for f in range(nf)
    }


def _policy_engine_efe_g(
    run_ctx: _ForwardsRunCtx,
    *,
    O: list[Any],
    P: list[Any],
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    t_next: int,
    T: int,
    N: int,
    m: int,
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None,
    ws: VbWorkspace | None,
    ws_m: int | None,
    bundle: dict[str, Any] | None,
    use_ws: bool,
) -> np.ndarray:
    """EFE ``t+1`` — direct ``policy_engine_step`` (no ``_forwards_compute`` wrapper)."""
    mi = int(m) - 1
    idm = id_list[mi]
    if mi not in run_ctx.static_by_mi:
        from python_src.optimized.toolbox.DEM.vb_forwards_optim import _forwards_model_static

        run_ctx.static_by_mi[mi] = _forwards_model_static(mi, A, B, C, H, K, W, I, idm)
    mstat = run_ctx.static_by_mi[mi]
    driver = run_ctx.driver
    driver.t_stack.append(int(t_next))
    try:
        g_out, _, _, _, _ = policy_engine_step(
            O,
            P,
            A,
            B,
            C,
            H,
            K,
            W,
            I,
            int(t_next),
            T,
            N,
            m,
            mi,
            idm,
            id_list,
            pA,
            qa,
            run_ctx,
            mstat,
            ws=ws,
            ws_m=ws_m,
            bundle=bundle,
            use_ws=use_ws,
        )
        return np.asarray(g_out, dtype=np.float64)
    finally:
        driver.t_stack.pop()


def policy_engine_step(
    O: list[Any],
    P: list[Any],
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    t: int,
    T: int,
    N: int,
    m: int,
    mi: int,
    idm: dict[str, Any],
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None,
    run_ctx: _ForwardsRunCtx,
    mstat: _ForwardsModelStatic,
    *,
    ws: VbWorkspace | None,
    ws_m: int | None,
    bundle: dict[str, Any] | None,
    use_ws: bool,
) -> tuple[np.ndarray, Any, float, list[Any], dict[int, Any]]:
    """Unified policy engine — ``spm_forwards`` body after per-model static hoist."""
    nf = mstat.nf
    nk = mstat.nk
    Ni = len(idm["g"])
    G = np.zeros((nk, Ni), dtype=np.float64)
    Pa: dict[int, Any] = {}
    id_fp_list = mstat.id_fp_list
    id_fu_list = mstat.id_fu_list
    id_iH_list = mstat.id_iH_list
    id_iI_list = mstat.id_iI_list
    a_f64 = mstat.a_f64
    c_f64 = mstat.c_f64
    k_f64 = mstat.k_f64
    w_f64 = mstat.w_f64
    log_hf = mstat.log_hf
    B_fk = mstat.B_fk
    B_fk_stacked = mstat.B_fk_stacked
    B_fp0 = mstat.B_fp0
    I_fk = mstat.I_fk
    ge_set = mstat.ge_set
    t_col = t - 1

    O_row = (
        ws_o_row_at_t(ws, bundle, mi, t_col)
        if use_ws and ws is not None and bundle is not None
        else [O[mi][g][t_col] for g in range(len(O[mi]))]
    )
    if use_ws and ws is not None and ws_m is not None and bundle is not None:
        P_row = _vbx_belief_row_ws_writable(ws, ws_m, t_col, nf, bundle)
    else:
        P_row = _fwd_p_row(P, mi, nf, t_col)
    A_row = A[mi]
    if _inst._vb_dump_active():
        _inst._entry12_record_phase_belief_rows(
            mi,
            t,
            "pre_vbx",
            O,
            P,
            P_row,
            extra={"A_peaks": _inst._entry12_a_peaks_for_model(A, mi)},
        )
    if os.getenv("RGMS_ENTRY12_PROBE_CHILD_F") and int(t) == 1 and len(O[mi]) >= 100:
        import sys as _sys_child_f

        if not _inst._ENTRY12_PROBE_CHILD_F_NPZ_DONE:
            import copy as _copy_probe
            import pickle as _pickle_probe

            _inst._ENTRY12_PROBE_CHILD_F_NPZ_DONE = True  # noqa: PLW0603
            _O_copy = [np.array(x, dtype=np.float64).copy() for x in O_row]
            _P_copy = [np.array(x, dtype=np.float64).copy() for x in P_row]
            _A_copy = [np.array(a, dtype=np.float64).copy() for a in A_row]
            _A0 = np.asarray(_A_copy[0], dtype=np.float64).ravel()
            np.savez(
                "matlab_custom/probe_child_vbx_t1.npz",
                O_row=np.array(_O_copy, dtype=object),
                P_row=np.array(_P_copy, dtype=object),
                A_row=np.array(_A_copy, dtype=object),
                A0_peak=int(np.argmax(_A0)) + 1,
                id_snapshot=_pickle_probe.dumps(_copy_probe.deepcopy(idm)),
                allow_pickle=True,
            )
        print(
            f"[entry12 child-F pre-vbx] m={m} t={t} len_O_mi={len(O[mi])} len_A={len(A_row)}",
            file=_sys_child_f.stderr,
            flush=True,
        )
    Q_upd, F = spm_VBX(O_row, P_row, A_row, idm)
    F_vbx_here = float(F)
    if os.getenv("RGMS_ENTRY12_PROBE_CHILD_F") and int(t) == 1 and len(O[mi]) >= 100:
        import sys as _sys_child_f

        print(
            f"[entry12 child-F] m={m} t={t} F_vbx={F_vbx_here}",
            file=_sys_child_f.stderr,
            flush=True,
        )
    if _inst._vb_dump_active():
        _inst._entry12_record_phase_belief_rows(
            mi, t, "post_vbx", O, P, Q_upd, extra={"F_vbx": F_vbx_here}
        )
    if _inst._vb_capture_y_probe_active():
        _inst._entry12_record_vbx_probe(mi, t, Q_upd, O_row, P_row, idm, F_vbx=F_vbx_here)
    for f in range(len(Q_upd)):
        if use_ws and ws is not None and ws_m is not None and Q_upd[f] is P_row[f]:
            ws_q_zero_inactive_tail(ws, ws_m, f, t_col, None)
        else:
            _fwd_write_belief_col(ws, ws_m, None, P, mi, f, t_col, Q_upd[f], use_ws=use_ws)

    if t > T or (nk * Ni == 1):
        return G, P, float(F_vbx_here), id_list, Pa

    B_slice = B[mi]
    H_slice = H[mi]
    if (
        os.getenv("RGMS_PROBE_12F_PARENT_T1")
        and t == 1
        and m == 1
        and nk >= 6
        and _inst._PROBE_12F_PARENT is None
    ):
        _inst._PROBE_12F_PARENT = {}
    ws_ind = ws if use_ws else None
    ws_m_ind = ws_m if use_ws else None
    R, r = _induction_cached(
        run_ctx,
        mi,
        t,
        int(T - t),
        None if use_ws and ws is not None and ws_m is not None else [
            _fwd_col_vec(ws, ws_m, P, mi, f, t_col, use_ws=use_ws, bundle=bundle)
            for f in range(nf)
        ],
        B_slice,
        H_slice,
        idm,
        ws=ws_ind,
        ws_m=ws_m_ind,
        ws_t_col=t_col if use_ws else None,
        nf=nf,
        ind_static=mstat.ind_static,
    )
    if (
        os.getenv("RGMS_PROBE_12F_PARENT_T1")
        and t == 1
        and m == 1
        and nk >= 6
        and isinstance(_inst._PROBE_12F_PARENT, dict)
    ):
        Rv0 = np.asarray(R, dtype=np.float64).ravel(order="F")
        _inst._PROBE_12F_PARENT["R_sum_post_induction"] = float(np.sum(Rv0))
        _inst._PROBE_12F_PARENT["R_nz_post_induction"] = np.flatnonzero(Rv0 > 0.0).tolist()[:8]
    if np.asarray(R).size:
        Rv = np.asarray(R, dtype=np.float64)
        if Rv.ndim == 1:
            R = Rv.reshape(1, -1, order="F")
        elif Rv.ndim == 2 and Rv.shape[1] == 1:
            R = Rv.reshape(1, -1, order="F")
        else:
            R = Rv

    pf_at_t = _pf_from_q_upd(Q_upd, nf)

    Qp: list[Any] = [None] * nf
    for f in id_fp_list:
        fi = int(f) - 1
        Qp[fi] = B_fp0[fi] @ pf_at_t[fi]

    pf_fu: dict[int, np.ndarray] = {}
    for f in id_fu_list:
        fi = int(f) - 1
        pf_fu[fi] = pf_at_t[fi]

    qp_fu_batch: dict[int, np.ndarray] = {}
    for f in id_fu_list:
        fi = int(f) - 1
        qp_fu_batch[fi] = np.matmul(B_fk_stacked[fi], pf_fu[fi])

    pmf_ii: dict[int, np.ndarray] = {}
    for f in id_iI_list:
        fi = int(f) - 1
        pmf_ii[fi] = pf_at_t[fi].reshape(1, -1, order="F")

    # **XXX_matlab-3 / PASS2 step 3:** hoist covert ``gi`` rows once (not per policy ``k``).
    gi_rows: list[np.ndarray] = []
    for i_cov in range(Ni):
        gi = idm["g"][i_cov]
        if ge_set is not None:
            gi = np.array(
                [x for x in np.atleast_1d(np.asarray(gi).ravel()) if int(x) in ge_set],
                dtype=np.int64,
            )
        else:
            gi = np.atleast_1d(np.asarray(gi, dtype=np.int64).ravel())
        gi_rows.append(gi)

    _probe_parent = bool(
        os.getenv("RGMS_PROBE_12F_PARENT_T1")
        and t == 1
        and m == 1
        and nk >= 6
        and _inst._PROBE_12F_PARENT is not None
    )

    for k in range(nk):
        for f in id_fu_list:
            fi = int(f) - 1
            Qp[fi] = qp_fu_batch[fi][k]

        if _probe_parent and k == 0 and "G_before_iH" not in _inst._PROBE_12F_PARENT:
            _inst._PROBE_12F_PARENT["G_before_iH"] = float(np.asarray(G[k, 0], dtype=np.float64))

        for f in id_iH_list:
            fi = int(f) - 1
            Qf = np.asarray(Qp[fi], dtype=np.float64).reshape(-1, 1, order="F")
            ih_term = float((Qf.T @ (_prim._spm_log(Qf) - log_hf[fi])).reshape(-1)[0])
            G[k, :] -= ih_term
            if _probe_parent and k == 0:
                _inst._PROBE_12F_PARENT["ih_term"] = ih_term
                _inst._PROBE_12F_PARENT["G_after_iH"] = float(np.asarray(G[k, 0], dtype=np.float64))

        for f in id_iI_list:
            fi = int(f) - 1
            Qf = np.asarray(Qp[fi], dtype=np.float64).reshape(-1, 1, order="F")
            G[k, :] += float(pmf_ii[fi] @ I_fk[fi][k] @ Qf)

        parents_k: dict[int, tuple[Any, Any]] = {}
        qj_k: dict[tuple[int, ...], list[Any]] = {}

        def _parents_cached(ig: int) -> tuple[Any, Any]:
            if ig not in parents_k:
                parents_k[ig] = spm_parents(idm, ig, Qp)
            return parents_k[ig]

        def _qj_cached(j: Any) -> list[Any]:
            jv = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
            key = tuple(int(x) for x in jv.tolist())
            if key not in qj_k:
                qj_k[key] = _prim._cell_get_Qj(Qp, j)
            return qj_k[key]

        if _prim._numel(R) > 0:
            q_cells = _prim._cell_get_Qj(Qp, r)
            if _probe_parent and k == 0:
                Rv = np.asarray(R, dtype=np.float64)
                _inst._PROBE_12F_PARENT["R_shape"] = list(Rv.shape)
                _inst._PROBE_12F_PARENT["R_max"] = float(np.max(Rv)) if Rv.size else 0.0
                _inst._PROBE_12F_PARENT["R_sum"] = float(np.sum(Rv))
                _inst._PROBE_12F_PARENT["r_factors"] = np.atleast_1d(np.asarray(r, dtype=np.int64)).ravel().tolist()
                if len(q_cells) == 1:
                    Qflat = np.asarray(q_cells[0], dtype=np.float64).ravel(order="F")
                else:
                    Qflat = np.asarray(spm_cross(q_cells), dtype=np.float64).ravel(order="F")
                Rflat = Rv.ravel(order="F")
                nz = np.flatnonzero(Rflat > 0.0)
                _inst._PROBE_12F_PARENT["R_nz_idx"] = nz[:8].tolist()
                _inst._PROBE_12F_PARENT["Q_at_R_nz"] = Qflat[nz[:8]].tolist() if nz.size else []
                _inst._PROBE_12F_PARENT["dot_manual_RQ"] = float(
                    (Rflat.reshape(1, -1) @ Qflat.reshape(-1, 1)).reshape(-1)[0]
                )
                for fi in _inst._PROBE_12F_PARENT["r_factors"]:
                    Qfi = np.asarray(Qp[int(fi) - 1], dtype=np.float64).ravel(order="F")
                    Pfi = _fwd_col_vec(
                        ws, ws_m, P, mi, int(fi) - 1, t_col, use_ws=use_ws, bundle=bundle
                    )
                    _inst._PROBE_12F_PARENT[f"Qf_len_f{fi}"] = int(Qfi.size)
                    _inst._PROBE_12F_PARENT[f"Qf_max_f{fi}"] = float(np.max(Qfi)) if Qfi.size else 0.0
                    _inst._PROBE_12F_PARENT[f"Pf_sum_f{fi}"] = float(np.sum(Pfi))
            g_risk = np.asarray(_forwards_dot_R_qcells(R, q_cells), dtype=np.float64).reshape(-1)
            if _probe_parent and k == 0:
                _inst._PROBE_12F_PARENT["spm_dot_R_Q"] = float(g_risk.reshape(-1)[0]) if g_risk.size else 0.0
                _inst._PROBE_12F_PARENT["G_after_dot"] = float(np.asarray(G[k, 0], dtype=np.float64))
                _inst._PROBE_12F_PARENT["done"] = True
            if g_risk.size == 1:
                G[k, :] += float(g_risk[0])
            elif g_risk.size == Ni:
                G[k, :] += g_risk
            else:
                G[k, :] += float(g_risk[0])

        No = np.zeros((1, Ni), dtype=np.float64)
        for i_cov in range(Ni):
            gi = gi_rows[i_cov]
            for ig in gi:
                j, gg = _parents_cached(int(ig))
                for g in np.atleast_1d(np.asarray(gg, dtype=np.int64).ravel()):
                    gi0 = int(g) - 1
                    Amg = a_f64[gi0]
                    if Amg is None:
                        Amg = A[mi][gi0]
                        if callable(Amg):
                            raise NotImplementedError("spm_forwards: A{m,g} function_handle not translated")
                    qj = _qj_cached(j)
                    qo = np.asarray(_forwards_dot_A_qj(Amg, qj), dtype=np.float64).reshape(-1, 1, order="F")
                    No[0, i_cov] += float(
                        np.asarray(
                            _prim._spm_log(np.array([[float(np.size(qo))]], dtype=np.float64)),
                            dtype=np.float64,
                        ).reshape(-1)[0]
                    )
                    G[k, i_cov] -= float((qo.T @ _prim._spm_log(qo)).reshape(-1)[0])
                    Cmg = c_f64[gi0]
                    if Cmg is not None:
                        c_cells = idm.get("C", [])
                        cg = None
                        if isinstance(c_cells, (list, tuple)) and len(c_cells) >= int(g):
                            cg = c_cells[int(g) - 1]
                        if cg is not None and _prim._numel(cg) > 0:
                            fC = int(np.asarray(cg, dtype=np.int64).ravel()[0])
                            U = np.asarray(
                                _forwards_dot_vec_match(_prim._spm_log(Cmg), Qp[int(fC) - 1]),
                                dtype=np.float64,
                            ).reshape(-1, 1, order="F")
                        else:
                            U = np.asarray(_prim._spm_log(Cmg), dtype=np.float64).reshape(
                                -1, 1, order="F"
                            )
                        G[k, i_cov] += float((qo.T @ U).reshape(-1)[0])
                    Kmg = k_f64[gi0]
                    if Kmg is not None:
                        G[k, i_cov] += float(np.asarray(_forwards_dot_A_qj(Kmg, qj), dtype=np.float64).reshape(-1)[0])
                    Wmg = w_f64[gi0]
                    if Wmg is not None:
                        G[k, i_cov] += float(
                            (qo.T @ np.asarray(_forwards_dot_A_qj(Wmg, qj), dtype=np.float64).reshape(-1, 1)).reshape(-1)[0]
                        )
                    pAg = pA[mi][int(g) - 1]
                    if _prim._numel(pAg) > 0:
                        if qa is None:
                            raise ValueError("spm_forwards: qa required when pA is non-empty")
                        da = spm_cross(qo, qj)
                        Pa[int(g)] = spm_MDP_BMR(np.asarray(qa[mi][int(g) - 1], dtype=np.float64), pAg)
                        Pg = spm_MDP_BMR(
                            np.asarray(qa[mi][int(g) - 1], dtype=np.float64) + np.asarray(da, dtype=np.float64),
                            pAg,
                        )
                        pal = np.asarray(Pa[int(g)], dtype=np.float64).reshape(-1, 1, order="F")
                        pgl = np.asarray(Pg, dtype=np.float64).reshape(-1, 1, order="F")
                        G[k, i_cov] += float((pgl.T @ (_prim._spm_log(pgl) - _prim._spm_log(pal))).reshape(-1)[0])
                    else:
                        Pa[int(g)] = {}

    G = G + No
    if "i" in idm:
        col_max = np.max(G, axis=0)
        i_sel = int(np.argmax(col_max) + 1)
        G = G[:, i_sel - 1 : i_sel]
        idm["i"] = i_sel
    else:
        G = np.sum(G, axis=1, keepdims=True)
        i_sel = 1

    if t < N:
        ng = len(pA[mi])
        pA[mi] = [None] * ng
        ig = idm["g"][i_sel - 1]
        ig = np.atleast_1d(np.asarray(ig, dtype=np.int64).ravel())
        u = np.asarray(spm_softmax(G), dtype=np.float64)
        mxu = float(np.max(u)) / 16.0
        k_plausible = u > mxu
        G = np.asarray(G, dtype=np.float64)
        G = np.where(k_plausible, G, float(np.max(G) - 512.0))

        for k in range(nk):
            if not bool(np.asarray(k_plausible, dtype=bool).reshape(-1)[k]):
                continue
            for f in id_fu_list:
                fi = int(f) - 1
                Qp[fi] = qp_fu_batch[fi][k]

            j_acc: list[int] = []
            parents_pl: dict[int, tuple[Any, Any]] = {}
            for g in ig.tolist():
                ig_i = int(g)
                if ig_i not in parents_pl:
                    parents_pl[ig_i] = spm_parents(idm, ig_i, Qp)
                j1, _ = parents_pl[ig_i]
                j1a = np.unique(np.atleast_1d(np.asarray(j1, dtype=np.int64).ravel())).tolist()
                j_acc = sorted(set(j_acc + [int(x) for x in j1a]))
            jv = np.asarray(j_acc, dtype=np.int64)

            s_list: list[np.ndarray] = []
            S_list: list[np.ndarray] = []
            n_list: list[int] = []
            for jf in jv.tolist():
                Qjf = np.asarray(Qp[int(jf) - 1], dtype=np.float64).reshape(-1, order="F")
                s_idx = np.flatnonzero(Qjf > _EXP_NEG8) + 1
                s_list.append(s_idx.astype(np.int64))
                S_list.append(Qjf[s_idx - 1].reshape(-1, 1, order="F"))
                n_list.append(int(s_idx.size))

            q = spm_cross(S_list)
            q = np.asarray(q, dtype=np.float64).reshape(tuple(n_list) + (1,), order="F")
            flat = q.ravel(order="F").copy()
            order_idx = np.argsort(-flat)
            if flat.size > 4:
                flat[order_idx[4:]] = 0.0
            zs = float(np.sum(flat))
            if zs > 0:
                flat = flat / zs
            q = flat.reshape(q.shape, order="F")
            EFE = np.zeros_like(q, dtype=np.float64)
            for ii_lin in range(int(q.size)):
                if float(flat[ii_lin]) == 0.0:
                    continue
                ind = spm_index(np.asarray(q.shape, dtype=float).reshape(-1), float(ii_lin + 1))
                ind_arr = np.asarray(ind, dtype=np.int64).ravel()
                fi = np.zeros(nf, dtype=np.int64)
                for pos, jf in enumerate(jv.tolist()):
                    fi[int(jf) - 1] = int(s_list[pos][int(ind_arr[pos]) - 1])
                memo_key = _efe_memo_key(m, t + 1, k, fi)
                if memo_key in run_ctx.memo:
                    E = run_ctx.memo[memo_key]
                else:
                    for g in ig.tolist():
                        fac, gg = parents_pl[int(g)]
                        ind_cell = [int(fi[int(ff) - 1]) for ff in np.atleast_1d(np.asarray(fac, dtype=np.int64).ravel())]
                        gi0 = int(g) - 1
                        Amg = a_f64[gi0]
                        if Amg is None:
                            Amg = A[mi][gi0]
                        for o in np.atleast_1d(np.asarray(gg, dtype=np.int64).ravel()):
                            if callable(Amg):
                                raise NotImplementedError("spm_forwards: function_handle A in recursion")
                            sl = tuple(slice(int(x - 1), int(x)) for x in ind_cell)
                            if Amg.ndim == len(ind_cell) + 1:
                                col = np.asarray(Amg[(slice(None),) + sl], dtype=np.float64).reshape(-1, 1, order="F")
                            else:
                                col = np.asarray(Amg[sl], dtype=np.float64).reshape(-1, 1, order="F")
                            if use_ws and ws is not None and bundle is not None:
                                ws_assign_o_slot(ws, None, mi, int(o) - 1, t, col)
                            else:
                                O[mi][int(o) - 1][t] = col
                    for f in range(nf):
                        _fwd_write_belief_col(ws, ws_m, None, P, mi, f, t, Qp[f], use_ws=use_ws)
                    E = _policy_engine_efe_g(
                        run_ctx,
                        O=O,
                        P=P,
                        A=A,
                        B=B,
                        C=C,
                        H=H,
                        K=K,
                        W=W,
                        I=I,
                        t_next=t + 1,
                        T=T,
                        N=N,
                        m=m,
                        id_list=id_list,
                        pA=pA,
                        qa=qa,
                        ws=ws,
                        ws_m=ws_m,
                        bundle=bundle,
                        use_ws=use_ws,
                    )
                    run_ctx.memo[memo_key] = np.asarray(E, dtype=np.float64).copy()
                Es = np.asarray(spm_softmax(E), dtype=np.float64).reshape(-1, 1, order="F")
                Ea = np.asarray(E, dtype=np.float64).reshape(-1, 1, order="F")
                EFE.ravel(order="F")[ii_lin] = float((Es.T @ Ea).reshape(-1)[0])

            G[k, 0] += float(np.sum(EFE * q))

    return G, P, float(F_vbx_here), id_list, Pa
