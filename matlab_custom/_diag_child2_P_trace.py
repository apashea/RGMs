"""Trace child bundle P{2}/Q{2} across internal t during second hierarchical VB (depth==2)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

F_PATH = 1  # P{2}
_TRACE: list[dict[str, object]] = []


def _peak(v: Any) -> dict[str, object]:
    a = np.asarray(v, dtype=np.float64).ravel()
    if a.size == 0:
        return {"n": 0}
    return {
        "n": int(a.size),
        "argmax": int(np.argmax(a) + 1),
        "top": float(a[0]),
        "head": a[:6].tolist(),
    }


def _log(label: str, bundle: dict, *, t_idx: int | None = None) -> None:
    if vb._VB_TIMING_DEPTH != 2:
        return
    mi = 0
    P = bundle["P"][mi][F_PATH]
    Q = bundle["Q"][mi][F_PATH]
    Nu = int(bundle["Nu"][mi, F_PATH])
    Um = float(np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()[F_PATH]) if F_PATH < bundle["Um"][mi].size else 0.0
    row: dict[str, object] = {
        "label": label,
        "t_idx": t_idx,
        "Nu": Nu,
        "Um": Um,
        "Np": int(bundle["Np"][mi]),
    }
    if t_idx is not None:
        row["P_t"] = _peak(P[t_idx])
        row["Q_t"] = _peak(Q[t_idx])
        if t_idx > 0:
            row["P_tm1"] = _peak(P[t_idx - 1])
    else:
        row["P_cols"] = [_peak(P[t]) for t in range(len(P))]
    _TRACE.append(row)


def _wrap(name: str, before: str | None = None, after: str | None = None):
    orig = getattr(vb, name)

    def wrapped(*args, **kw):
        bundle = None
        t_idx = None
        for a in args:
            if isinstance(a, dict) and "P" in a and "Q" in a and "Nu" in a:
                bundle = a
            elif isinstance(a, int):
                t_idx = a
        if bundle is not None and vb._VB_TIMING_DEPTH == 2:
            if before:
                _log(before, bundle, t_idx=t_idx)
        out = orig(*args, **kw)
        if bundle is not None and vb._VB_TIMING_DEPTH == 2:
            if after:
                _log(after, bundle, t_idx=t_idx)
        return out

    setattr(vb, name, wrapped)


_orig_belief = vb._vb_belief_after_forwards
_orig_prior = vb._vb_prior_QP_paths_states_one_model
_orig_loop = vb._vb_run_partial_t_loop
_orig_hier = vb._vb_hierarchical_subordinate_outcomes
_hier_calls = 0


def _belief(mi, bundle, t_m, t_idx, G_m, alpha):
    if vb._VB_TIMING_DEPTH == 2:
        _log("belief_pre", bundle, t_idx=t_idx)
    G_out, Z = _orig_belief(mi, bundle, t_m, t_idx, G_m, alpha)
    if vb._VB_TIMING_DEPTH == 2:
        _log("belief_post", bundle, t_idx=t_idx)
    return G_out, Z


def _prior(mi, bundle, t_idx, Pu_vec):
    if vb._VB_TIMING_DEPTH == 2:
        _log("prior_QP_pre", bundle, t_idx=t_idx)
    out = _orig_prior(mi, bundle, t_idx, Pu_vec)
    if vb._VB_TIMING_DEPTH == 2:
        _log("prior_QP_post", bundle, t_idx=t_idx)
    return out


def _loop(models, bundle, alpha, recurse_partial, *, reuse_matlab_draws=False):
    if vb._VB_TIMING_DEPTH == 2:
        _log("child_loop_start", bundle)
    return _orig_loop(
        models, bundle, alpha, recurse_partial, reuse_matlab_draws=reuse_matlab_draws
    )


def _hier(models, bundle, t_idx, M_row, recurse_partial, **kw):
    global _hier_calls
    out = _orig_hier(models, bundle, t_idx, M_row, recurse_partial, **kw)
    if vb._VB_TIMING_DEPTH == 1 and t_idx == 1:
        _hier_calls += 1
        if _hier_calls == 1:
            _TRACE.append({"label": "second_hier_done"})
    return out


def main() -> None:
    vb._vb_belief_after_forwards = _belief
    vb._vb_prior_QP_paths_states_one_model = _prior
    vb._vb_run_partial_t_loop = _loop
    vb._vb_hierarchical_subordinate_outcomes = _hier
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb._vb_belief_after_forwards = _orig_belief
        vb._vb_prior_QP_paths_states_one_model = _orig_prior
        vb._vb_run_partial_t_loop = _orig_loop
        vb._vb_hierarchical_subordinate_outcomes = _orig_hier

    out_path = ROOT / "matlab_custom" / "_diag_child2_P_trace.json"
    out_path.write_text(json.dumps(_TRACE, indent=2), encoding="utf-8")
    print(f"wrote {out_path} ({len(_TRACE)} rows)")
    for row in _TRACE:
        if row.get("label") in (
            "child_loop_start",
            "prior_QP_post",
            "belief_post",
            "second_hier_done",
        ) or str(row.get("label", "")).startswith("belief"):
            print(row)


if __name__ == "__main__":
    main()
