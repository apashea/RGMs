#!/usr/bin/env python3
"""OPTIM1FULL call4 VB investigation — Stage **0** (read-only artifact mine).

Mines existing tier **3f** paired PKL/MAT lean snaps and ``entry12_phase_log``;
does **not** re-run VB. See ``OPTIM1FULL.md`` § Call4 VB investigation subframework.

Report: ``tests/demo1/optim1full/probe/reports/call4_stage0_<date>.txt``
"""
from __future__ import annotations

import pickle
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

TAG = "rgms_atari_optim1full_call4"
BANDS = ("12D", "12E", "12F")
BOUNDARY_KEYS = ("in", "out_t1", "out_t2", "out_t3", "out_tT")
TOL = 1e-9


def _repo_probe_reports() -> Path:
    p = _REPO / "tests" / "demo1" / "optim1full" / "probe" / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fixtures() -> Path:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    return optim1full_fixtures_dir()


def _load_pkl_band(fix: Path, band: str) -> dict[str, Any]:
    p = fix / f"DEMAtariIII_entry12_{TAG}_{band}.pkl"
    with p.open("rb") as f:
        ws = pickle.load(f)
    if not isinstance(ws, dict):
        raise TypeError(f"{p}: expected dict workspace, got {type(ws).__name__}")
    return ws


def _load_mat_snap(fix: Path, band: str, sub: str) -> dict[str, Any] | None:
    from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat

    if sub == "in":
        name = f"DEMAtariIII_entry12_{TAG}_{band}_in.mat"
    else:
        base = fix / f"DEMAtariIII_entry12_{TAG}_{band}.mat"
        if not base.is_file():
            return None
        bundle = load_entry12_subentry_mat(base)
        if sub not in bundle:
            return None
        return {"in": bundle[sub]} if False else bundle[sub]  # noqa: dead path guard
    path = fix / name
    if not path.is_file():
        return None
    return load_entry12_subentry_mat(path).get("in") or load_entry12_subentry_mat(path)


def _load_mat_boundary(fix: Path, band: str, sub: str) -> dict[str, Any] | None:
    from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat

    if sub == "in":
        path = fix / f"DEMAtariIII_entry12_{TAG}_{band}_in.mat"
        if not path.is_file():
            return None
        return load_entry12_subentry_mat(path).get("in")
    path = fix / f"DEMAtariIII_entry12_{TAG}_{band}.mat"
    if not path.is_file():
        return None
    bundle = load_entry12_subentry_mat(path)
    return bundle.get(sub)


def _parent_mdp(snap: dict[str, Any]) -> dict[str, Any] | None:
    mdp = snap.get("MDP")
    if isinstance(mdp, list) and mdp:
        mdp = mdp[0]
    return mdp if isinstance(mdp, dict) else None


def _f_at_t(mdp: dict[str, Any] | None, t_lab: int) -> float | None:
    if mdp is None or "F" not in mdp:
        return None
    fi = max(0, t_lab - 1) if t_lab > 0 else 0
    try:
        return float(np.asarray(mdp["F"], dtype=np.float64).reshape(-1)[fi])
    except (IndexError, TypeError, ValueError):
        return None


def _max_abs_diff(a: Any, b: Any) -> float | None:
    try:
        pa = np.asarray(a, dtype=np.float64).reshape(-1)
        pb = np.asarray(b, dtype=np.float64).reshape(-1)
        n = min(pa.size, pb.size)
        if n == 0:
            return 0.0 if pa.size == pb.size else None
        return float(np.max(np.abs(pa[:n] - pb[:n])))
    except (TypeError, ValueError):
        return None


def _scan_phase_log_f(lines: list[str], py_snap: dict, mat_snap: dict, label: str) -> None:
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        _entry12_parent_mdp_from_12f_snap,
        _entry12_phase_log_model_entries,
        _entry12_phase_log_parent_phase_map,
        ENTRY12_PHASE_LOG_ORDER,
    )

    t_lab = int(np.asarray(py_snap.get("t", 0), dtype=np.float64).item())
    py_entries = _entry12_phase_log_model_entries(py_snap.get("entry12_phase_log"))
    mat_entries = _entry12_phase_log_model_entries(mat_snap.get("entry12_phase_log"))
    lines.append(f"  phase_log entries: py={len(py_entries)} mat={len(mat_entries)}")
    py_mdp = _entry12_parent_mdp_from_12f_snap(py_snap)
    mat_mdp = _entry12_parent_mdp_from_12f_snap(mat_snap)
    fp = _f_at_t(py_mdp, t_lab)
    fm = _f_at_t(mat_mdp, t_lab)
    if fp is not None and fm is not None:
        d = fp - fm
        lines.append(f"  MDP.F at t={t_lab}: py={fp} mat={fm} diff={d}")
    py_map = _entry12_phase_log_parent_phase_map(py_entries)
    mat_map = _entry12_phase_log_parent_phase_map(mat_entries)
    for ph in ENTRY12_PHASE_LOG_ORDER:
        if ph not in py_map and ph not in mat_map:
            continue
        pe, me = py_map.get(ph, {}), mat_map.get(ph, {})
        for sk in ("F_vbx", "F_after_fwd", "F_mdp_slot"):
            if sk in pe or sk in me:
                d = _max_abs_diff(pe.get(sk), me.get(sk))
                if d is not None and (d > TOL or sk in pe or sk in me):
                    lines.append(f"    phase={ph} {sk}: max|diff|={d}")


def run_stage0() -> Path:
    fix = _fixtures()
    lines: list[str] = [
        f"OPTIM1FULL call4 VB investigation — Stage 0 (read-only)",
        f"tag={TAG}",
        f"fixtures={fix}",
        "",
        "=== Causal boundary witness: parent MDP.F (py PKL vs MAT lean snap) ===",
    ]

    first_f_red: tuple[str, float] | None = None
    causal_reds: list[str] = []

    for band in BANDS:
        py_ws = _load_pkl_band(fix, band)
        for sub in BOUNDARY_KEYS:
            if sub not in py_ws:
                continue
            py_snap = py_ws[sub]
            mat_snap = _load_mat_boundary(fix, band, sub)
            if mat_snap is None:
                lines.append(f"{band}.{sub}: MAT snap missing")
                continue
            t_lab = int(np.asarray(py_snap.get("t", 0), dtype=np.float64).item())
            py_f = _f_at_t(_parent_mdp(py_snap), t_lab)
            mat_f = _f_at_t(_parent_mdp(mat_snap), t_lab)
            if py_f is None or mat_f is None:
                lines.append(f"{band}.{sub} t={t_lab}: F unavailable py={py_f} mat={mat_f}")
                continue
            diff = py_f - mat_f
            flag = "OK" if abs(diff) <= TOL else "RED"
            lines.append(
                f"{band}.{sub} t={t_lab}: MDP.F py={py_f:.6g} mat={mat_f:.6g} diff={diff:.6g} [{flag}]"
            )
            if flag == "RED":
                causal_reds.append(f"{band}.{sub}")
                if first_f_red is None or sub == "out_tT":
                    first_f_red = (f"{band}.{sub}", abs(diff))
            if band == "12F" and sub.startswith("out_t"):
                lines.append(f"--- 12F.{sub} phase_log detail ---")
                _scan_phase_log_f(lines, py_snap, mat_snap, f"12F.{sub}")

    lines.extend(["", "=== 12E.out_tT O[0] spot check ==="])
    try:
        py_ws = _load_pkl_band(fix, "12E")
        mat_snap = _load_mat_boundary(fix, "12E", "out_tT")
        if mat_snap and "out_tT" in py_ws:
            py_o = py_ws["out_tT"].get("O")
            mat_o = mat_snap.get("O")
            if py_o is not None and mat_o is not None:
                d = _max_abs_diff(
                    py_o[0] if isinstance(py_o, list) else py_o,
                    mat_o[0] if isinstance(mat_o, list) else mat_o,
                )
                lines.append(f"12E.out_tT O[0] max|diff|={d}")
    except Exception as exc:
        lines.append(f"12E O check skipped: {exc}")

    lines.extend(["", "=== Stage 0 summary ==="])
    lines.append(f"Causal MDP.F reds ({len(causal_reds)}): {', '.join(causal_reds) or '(none)'}")
    if first_f_red:
        lines.append(f"First F red (by scan order): {first_f_red[0]} max|diff|~{first_f_red[1]:.6g}")
    lines.append(
        "Temporal gap: lean snaps only at t in {0,1,2,3,128} - Stage 1 T_stop bisection "
        "needed if no intermediate t in phase_log shows divergence onset."
    )
    lines.append(
        "Next: if t=2,3 OK and t=128 RED only -> run Stage 1 "
        "(optim1full_call4_vb_timestep_witness.py) one T_stop at a time."
    )

    out = _repo_probe_reports() / f"call4_stage0_{date.today().isoformat()}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[optim1full call4 stage0] wrote {out}", flush=True)
    return out


def main() -> int:
    try:
        run_stage0()
        return 0
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
