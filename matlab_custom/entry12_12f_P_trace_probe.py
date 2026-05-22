"""Trace parent m=1 bundle P[0][f][t] sizes in full spm_MDP_VB_XXX (depth==1)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_TRACE: list[dict[str, object]] = []


def _sizes(bundle: dict, mi: int = 0) -> list[list[int]]:
    P = bundle["P"][mi]
    return [[int(np.asarray(P[f][ti]).size) for ti in range(min(4, len(P[f])))] for f in range(len(P))]


def _log(label: str, bundle: dict, **extra: object) -> None:
    if vb._VB_TIMING_DEPTH != 1:
        return
    row: dict[str, object] = {"label": label, "nf": len(bundle["P"][0]), "P": _sizes(bundle)}
    row.update(extra)
    _TRACE.append(row)


def _wrap(name: str, before: str | None = None, after: str | None = None):
    orig = getattr(vb, name)

    def wrapped(*args, **kw):
        bundle = None
        for a in args:
            if isinstance(a, dict) and "P" in a and "Q" in a:
                bundle = a
                break
        if before and bundle is not None:
            _log(before, bundle, t_idx=bundle.get("_trace_t"))
        out = orig(*args, **kw)
        if after and bundle is not None:
            _log(after, bundle, t_idx=bundle.get("_trace_t"))
        return out

    setattr(vb, name, wrapped)


_orig_loop = vb._vb_run_partial_t_loop
_orig_fwd = vb.spm_forwards


def _loop(models, bundle, alpha, recurse_partial, *, reuse_matlab_draws=False):
    t_int = int(bundle["T"])
    for t_idx in range(min(3, t_int)):
        bundle["_trace_t"] = t_idx
        _log(f"t{t_idx}_loop_enter", bundle)
        row = bundle["M_update"][t_idx, :]
        vb._vb_generation_paths_states_share(models, bundle, t_idx, row)
        _log(f"t{t_idx}_post_gen", bundle)
        vb._vb_generate_outcomes_if_options_o(models, bundle, t_idx, row)
        vb._vb_shared_probabilistic_outcomes(models, bundle, t_idx, row)
        vb._vb_hierarchical_subordinate_outcomes(
            models, bundle, t_idx, row, recurse_partial, reuse_matlab_draws=reuse_matlab_draws
        )
        _log(f"t{t_idx}_post_hier", bundle)
        vb._vb_fill_O_empty_from_realized_o_at_t(models, bundle, t_idx, row)
        vb._vb_fill_BP_IP_at_t(bundle, t_idx)
        _log(f"t{t_idx}_pre_forwards", bundle)
        t_m = t_idx + 1
        n_horiz = int(min(t_int, t_m + int(bundle["N_policy_depth"])))
        qa_b = bundle.get("qa")
        for mm in np.asarray(row, dtype=np.int64).ravel():
            if int(mm) != 1:
                continue
            mi = 0
            G_m, _, F_elbo, _, _ = vb.spm_forwards(
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
                1,
                bundle["id"],
                bundle["pA"],
                qa_b,
            )
            _log(f"t{t_idx}_post_forwards", bundle, F=float(F_elbo))
            vb._vb_belief_after_forwards(
                mi, bundle, t_m, t_idx, np.asarray(G_m, dtype=np.float64), float(alpha)
            )
            _log(f"t{t_idx}_post_belief", bundle)
        bundle.pop("_trace_t", None)
    return _orig_loop(models, bundle, alpha, recurse_partial, reuse_matlab_draws=reuse_matlab_draws)


def _fwd(*args, **kw):
    O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = args
    if vb._VB_TIMING_DEPTH == 1 and int(m) == 1 and int(t) <= 2:
        mi = 0
        pre = [int(np.asarray(P[mi][f][t - 1]).size) for f in range(len(P[mi]))]
        _TRACE.append({"label": f"fwd{t}_pre", "P_pre": pre})
    out = _orig_fwd(*args, **kw)
    if vb._VB_TIMING_DEPTH == 1 and int(m) == 1 and int(t) <= 2:
        mi = 0
        G, P2, f, id2, pa = out
        cur = [int(np.asarray(P2[mi][ff][t - 1]).size) for ff in range(len(P2[mi]))]
        nxt = []
        if len(P2[mi][0]) > t:
            nxt = [int(np.asarray(P2[mi][ff][t]).size) for ff in range(len(P2[mi]))]
        _TRACE.append({"label": f"fwd{t}_post", "P_cur": cur, "P_next": nxt, "F": float(f)})
    return out


def main() -> None:
    vb._vb_run_partial_t_loop = _loop
    vb.spm_forwards = _fwd
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb._vb_run_partial_t_loop = _orig_loop
        vb.spm_forwards = _orig_fwd
    # keep only parent-depth rows with nf==1
    slim = [r for r in _TRACE if r.get("nf") == 1 or "fwd" in str(r.get("label", ""))]
    out = ROOT / "matlab_custom" / "entry12_12f_P_trace_probe.json"
    out.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    print(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
