#!/usr/bin/env python3
"""OPTIM1FULL Product B — NR game-1 RDP assembly structural compare (§ **11.7.3** P1).

Read-only: MATLAB vs Python fidelity assembly from the same ``MDP_pre_active_inference``
fixture. Exit **0** only when top-level ``nB``, ``nA``, ``T``, and ``L`` match.

Does **not** run VB or consume ledger draws.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import matlab.engine
import numpy as np
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _scalar(x: object) -> float:
    return float(np.asarray(x, dtype=np.float64).reshape(-1)[0])


def _rdp_shape_summary(rdp: dict[str, Any], label: str) -> dict[str, Any]:
    l_raw = rdp.get("L")
    l_val = int(np.asarray(l_raw, dtype=np.int64).reshape(-1)[0]) if l_raw is not None else None
    out: dict[str, Any] = {
        "label": label,
        "T": _scalar(rdp.get("T", 0)),
        "L": l_val,
        "nA": len(rdp.get("A", [])),
        "nB": len(rdp.get("B", [])),
        "hasMDP": "MDP" in rdp,
    }
    if "MDP" in rdp and isinstance(rdp["MDP"], list) and rdp["MDP"]:
        c0 = rdp["MDP"][0]
        if isinstance(c0, dict):
            out["child0_nA"] = len(c0.get("A", []))
    return out


def _matlab_assemble_nr_rdp_game1(
    eng: matlab.engine.MatlabEngine,
    pre_mat: Path,
    *,
    c_val: float,
    ns: float,
    nt: int,
    tmp_mat: Path,
) -> dict[str, Any]:
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    pre_posix = str(pre_mat.resolve()).replace("\\", "/")
    tmp_posix = str(tmp_mat.resolve()).replace("\\", "/")
    eng.eval(
        f"load('{pre_posix}','MDP_pre_active_inference','Ne'); "
        f"C={c_val}; NS={ns}; NT={nt}; "
        "RDP=spm_set_goals(MDP_pre_active_inference,[2,3],[C,-C]); "
        "RDP=spm_set_costs(RDP,[2,3],[C,-C]); "
        "RDP=spm_mdp2rdp(RDP,0,1/NS); "
        "RDP.T=fix(NT/Ne); "
        f"save('{tmp_posix}','RDP','-v7');",
        nargout=0,
    )
    rdp = mat_nested_to_py(loadmat(str(tmp_mat))["RDP"])
    if isinstance(rdp, dict) and "T" in rdp:
        rdp["T"] = _scalar(rdp["T"])
    return rdp


def _python_assemble_nr_rdp_game1(
    pre_mat: Path,
    *,
    c_val: float,
    ns: float,
    nt: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from tests.demo1.optim1full.optim1full_audit_nr_segment_draws import assemble_nr_rdp_parity
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat

    mdp_py = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
    ne = load_ne_from_mat(pre_mat, "Ne")
    rdp_py = assemble_nr_rdp_parity(mdp_py, c_val, ne, nt=nt, ns=ns)
    return rdp_py, mdp_py


def _mdp_level_counts_matlab(
    eng: matlab.engine.MatlabEngine, pre_mat: Path, levels: int
) -> list[dict[str, int]]:
    pre_posix = str(pre_mat.resolve()).replace("\\", "/")
    eng.eval(f"load('{pre_posix}','MDP_pre_active_inference');", nargout=0)
    rows: list[dict[str, int]] = []
    for i in range(levels):
        na = int(eng.eval(f"numel(MDP_pre_active_inference{{{i + 1}}}.a)"))
        nb = int(eng.eval(f"numel(MDP_pre_active_inference{{{i + 1}}}.b)"))
        rows.append({"level": i, "na": na, "nb": nb})
    return rows


def _mdp_level_counts_python(mdp: list[dict[str, Any]]) -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    for i, m in enumerate(mdp):
        rows.append({"level": i, "na": len(m.get("a", [])), "nb": len(m.get("b", []))})
    return rows


def compare_nr_game1_rdp_assembly() -> dict[str, Any]:
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.demo1.optim1full.optim1full_signoff_env import (
        OPTIM1FULL_CANONICAL_NS,
        OPTIM1FULL_CANONICAL_NT,
        optim1full_signoff_env,
    )

    repo = demo1_repo_root()
    pre = optim1full_mdp_pre_active_inference_mat()
    if not pre.is_file():
        raise FileNotFoundError(f"missing pre-NR authority: {pre}")

    c_val = atari_c_value()
    ns = float(OPTIM1FULL_CANONICAL_NS)
    nt = int(OPTIM1FULL_CANONICAL_NT)
    tmp = repo / "matlab_custom" / "_optim1full_matlab_rdp_nr1_compare.mat"

    with optim1full_signoff_env(deadline_minutes="30"):
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, repo)
            mat_rdp = _matlab_assemble_nr_rdp_game1(
                eng, pre, c_val=c_val, ns=ns, nt=nt, tmp_mat=tmp
            )
            mat_mdp_counts = _mdp_level_counts_matlab(eng, pre, levels=2)
        finally:
            eng.quit()

        py_rdp, py_mdp = _python_assemble_nr_rdp_game1(
            pre, c_val=c_val, ns=ns, nt=nt
        )
        py_mdp_counts = _mdp_level_counts_python(py_mdp)

    mat_shape = _rdp_shape_summary(mat_rdp, "matlab")
    py_shape = _rdp_shape_summary(py_rdp, "python")

    fields = ("nA", "nB", "T", "L", "hasMDP")
    mismatches = [
        f"{key}: matlab={mat_shape[key]!r} python={py_shape[key]!r}"
        for key in fields
        if mat_shape[key] != py_shape[key]
    ]
    mdp_match = mat_mdp_counts == py_mdp_counts

    passed = not mismatches and mdp_match
    return {
        "pass": passed,
        "matlab_rdp": mat_shape,
        "python_rdp": py_shape,
        "matlab_mdp_levels": mat_mdp_counts,
        "python_mdp_levels": py_mdp_counts,
        "mismatches": mismatches,
        "assembly": "spm_set_goals_spm_set_costs_spm_mdp2rdp",
        "fixture": str(pre),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1FULL NR game-1 RDP assembly compare")
    p.parse_args(argv)

    t0 = time.perf_counter()
    report = compare_nr_game1_rdp_assembly()
    wall_s = time.perf_counter() - t0

    status = "PASS" if report["pass"] else "FAIL"
    mat = report["matlab_rdp"]
    py = report["python_rdp"]
    print(
        f"[optim1full_compare_nr_game1_rdp_assembly] {status} "
        f"mat nA={mat['nA']} nB={mat['nB']} T={mat['T']} | "
        f"py nA={py['nA']} nB={py['nB']} T={py['T']} "
        f"wall_s={wall_s:.3f}",
        file=sys.stderr,
        flush=True,
    )
    if report["mismatches"]:
        for line in report["mismatches"]:
            print(f"[optim1full_compare_nr_game1_rdp_assembly] mismatch {line}", file=sys.stderr)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
