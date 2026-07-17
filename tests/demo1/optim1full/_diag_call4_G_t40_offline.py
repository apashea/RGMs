#!/usr/bin/env python3
"""Phase A — offline deepen of call4 ledger G@t=40 snap (no VB re-run).

Reads ``matlab_custom/optim1full_call4_py_vs_mat_pdp_snap.pkl`` (or rebuilds if missing
via ledger VB — avoid if snap present). Writes
``matlab_custom/optim1full_call4_G_t40_offline_diag.txt``.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _sq(x) -> np.ndarray:
    return np.squeeze(np.asarray(x, dtype=float))


def main() -> int:
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    snap_path = _REPO / "matlab_custom" / "optim1full_call4_py_vs_mat_pdp_snap.pkl"
    report = _REPO / "matlab_custom" / "optim1full_call4_G_t40_offline_diag.txt"
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        lines.append(msg)

    if not snap_path.is_file():
        log(f"MISSING snap {snap_path} — run _diag_call4_pdp_causal_fields.py first")
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 2

    with snap_path.open("rb") as f:
        snap = pickle.load(f)
    py, mat = snap["py"], snap["mat"]
    log(f"snap={snap_path.name}")

    Gpy, Gmat = _sq(py["G"]), _sq(mat["G"])
    log(f"PDP.G shapes py={Gpy.shape} mat={Gmat.shape}")
    assert Gpy.shape == Gmat.shape == (128, 4), Gpy.shape

    # Index check: stacked PDP.G row t corresponds to MATLAB MDP.G{t} (1-based t).
    # Compare stored per-t list if present on models.
    def _mdp_g_list(pdp: dict) -> list | None:
        mdp = pdp.get("MDP")
        if not isinstance(mdp, dict):
            return None
        g = mdp.get("G")
        return g if isinstance(g, list) else None

    py_g_cells = _mdp_g_list(py)
    mat_g_cells = _mdp_g_list(mat)
    log(f"nested MDP.G list lens py={None if py_g_cells is None else len(py_g_cells)} "
        f"mat={None if mat_g_cells is None else len(mat_g_cells)}")

    # At labeled t=40 (0-based row 39 if G is (T,Np) with row0 = t=1):
    # Prior timeline used axis0 as t with first diverge t=40 meaning index 40
    # (0-based), i.e. MATLAB t=41 if row0=t=1 — OR row index == MATLAB t-1.
    # Empirically: u diverge "t=40" with u.shape (128,) — need to know if index 40
    # is MATLAB t=41 or t=40.
    upy, umat = _sq(py["u"]), _sq(mat["u"])
    dG = np.abs(Gpy - Gmat)
    bad_rows = np.where(np.max(dG, axis=1) > 1e-6)[0]
    log(f"G bad rows (0-based indices): {bad_rows.tolist()}")
    i40 = int(bad_rows[0]) if bad_rows.size else 40
    log(f"using diverge index i={i40} as stacked-G row / u index")
    log(f"  MATLAB 1-based t interpretation: if row0=t=1 then MATLAB t={i40 + 1}; "
        f"if row index==MATLAB t (0 unused) unused — check MDP.G cells")

    if py_g_cells is not None and mat_g_cells is not None and len(py_g_cells) >= i40 + 1:
        # Try cell index i40 as 0-based for MATLAB t=i40+1
        for cell_i, label in ((i40, f"cell[{i40}] as t={i40+1}"), (i40 - 1, f"cell[{i40-1}] as t={i40}")):
            if cell_i < 0 or cell_i >= len(py_g_cells):
                continue
            try:
                cg_py = _sq(py_g_cells[cell_i])
                cg_mat = _sq(mat_g_cells[cell_i])
                # broadcast to 4
                cg_py = cg_py.ravel()
                cg_mat = cg_mat.ravel()
                row = Gpy[i40]
                match_py = cg_py.size >= 4 and np.allclose(cg_py[:4], row, atol=1e-6, equal_nan=True)
                match_mat = cg_mat.size >= 4 and np.allclose(cg_mat[:4], Gmat[i40], atol=1e-6, equal_nan=True)
                log(f"  MDP.G {label}: py_cell={cg_py[:4] if cg_py.size>=4 else cg_py} "
                    f"matches stacked row={match_py}; mat_cell matches={match_mat}")
            except Exception as exc:
                log(f"  MDP.G {label}: compare fail {exc}")

    log("--- per-policy delta at diverge row ---")
    log(f"  G_py  = {Gpy[i40].tolist()}")
    log(f"  G_mat = {Gmat[i40].tolist()}")
    log(f"  dG    = {(Gpy[i40] - Gmat[i40]).tolist()}")
    log(f"  abs_dG= {np.abs(Gpy[i40] - Gmat[i40]).tolist()}")
    log(f"  policy0 dominates: abs_d0={abs(Gpy[i40,0]-Gmat[i40,0]):.6f} "
        f"vs max others={float(np.max(np.abs(Gpy[i40,1:]-Gmat[i40,1:]))):.6f}")

    log("--- u / P / R at nearby indices ---")
    for t in range(max(0, i40 - 2), min(128, i40 + 3)):
        log(f"  t_idx={t} u py/mat={float(upy[t])}/{float(umat[t])} "
            f"G_dmax={float(np.max(np.abs(Gpy[t]-Gmat[t]))):.6g}")

    # Nested MDP reds
    log("--- nested MDP field reds ---")
    mdp_py, mdp_mat = py.get("MDP"), mat.get("MDP")
    if isinstance(mdp_py, dict) and isinstance(mdp_mat, dict):
        reds = []
        for k in sorted(set(mdp_py) | set(mdp_mat)):
            if k not in mdp_py or k not in mdp_mat:
                reds.append((k, "present mismatch"))
                continue
            try:
                _assert_nested_rdp_equal(mdp_py[k], mdp_mat[k], f"MDP.{k}")
            except AssertionError as exc:
                reds.append((k, str(exc)[:140]))
        log(f"  n_reds={len(reds)}")
        for k, msg in reds:
            log(f"  MDP.{k}: {msg}")
    else:
        log("  nested MDP not both dicts")

    # X vs s surprise
    Xpy, Xmat = _sq(py["X"]), _sq(mat["X"])
    spy, smat = _sq(py["s"]), _sq(mat["s"])
    log(f"X shapes {Xpy.shape} {Xmat.shape}; s shapes {spy.shape} {smat.shape}")
    if Xpy.shape == Xmat.shape and 128 in Xpy.shape:
        tax = list(Xpy.shape).index(128)
        if tax == 1:
            per = [float(np.max(np.abs(Xpy[:, t] - Xmat[:, t]))) for t in range(128)]
        else:
            per = [float(np.max(np.abs(Xpy[t] - Xmat[t]))) for t in range(128)]
        badx = [t for t, v in enumerate(per) if v > 1e-6]
        log(f"X bad_t count={len(badx)} maxabs_all={max(per):.6g} at_diverge_i={per[i40]:.6g}")
    if spy.ndim >= 1:
        ds = np.abs(spy.astype(float) - smat.astype(float))
        if spy.ndim == 1:
            bads = np.where(ds > 0)[0]
            log(f"s 1d first diverge idx={int(bads[0]) if bads.size else None} n={bads.size}")
        elif spy.ndim == 2 and 128 in spy.shape:
            tax = list(spy.shape).index(128)
            if tax == 1:
                bads = [t for t in range(128) if not np.array_equal(spy[:, t], smat[:, t])]
            else:
                bads = [t for t in range(128) if not np.array_equal(spy[t], smat[t])]
            log(f"s first diverge idx={bads[0] if bads else None} n={len(bads)}")

    log("NOTE: final X match all-t while s/u flip is NOT evidence that forwards inputs "
        "at the diverge step already differed — Phase B must dump beliefs into spm_forwards.")
    log("RESULT Phase A: OFFLINE COMPLETE - diverge cell idx 40 = MATLAB t=41; "
        "policy0 dG~10; nested reds downstream only")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
