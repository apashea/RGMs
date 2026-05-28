"""
Entry 12 Phase 1 — draw-index audit and **paired sample trace** (official RNG deep-dive).

**Framework role:** Named exception to “no ad-hoc probes” (``Atari_example.md``). Use this
script instead of windowed ``_diag_*`` scripts when investigating replay skew.

**Contract (Pillar B):**
- Script **1a** counts ``K`` scalar ``numpy.random.rand()`` draws (native, no replay).
- Script **1b** records ``vb_rand_buf = rand(K,1)`` after preamble-rewind (oracle lane).
- Script **3** replays the buffer through ``_spm_sample`` (``reuse_matlab_draws=True``).

This script runs the **script 3** lane (``entry12_vb_oracle_flags``) with replay logging.

**Outputs:**
- ``matlab_custom/entry12_draw_index_audit_results.json`` — summary + coherence gates.
- ``tests/oracle/toolbox/DEM/fixtures/entry12_sample_trace_<tag>.json`` — full tagged trace.

**Per-call fields:** ``seq``, ``site``, ``pattern`` (L0/L1/L2/N1), ``draw_start``/``draw_end``,
``n_draws``, ``depth``, ``t_gen``, dtype/shape, ``k_mask``, ``out``.

**Interpretation:** Compare **first** row where ``pattern`` or ``n_draws`` disagrees with MATLAB
(same ``seq`` on a future MATLAB trace). Do **not** fix buffer indices without a site class fix.

**Site taxonomy (static inventory — VB loop order):**

| Site id | MATLAB band | Python caller |
|---------|-------------|---------------|
| ``gp_path_E`` | ~810 ``spm_sample(pu)`` on ``GP.E{f}`` | ``_vb_gen_u_paths_one_model`` |
| ``policy`` | ~823 ``spm_sample(Pu)`` | ``_vb_prior_QP_paths_states_one_model`` |
| ``control_P`` | ~863 ``spm_sample(P{m,f,t-1})`` | ``_vb_gen_control_one_model`` |
| ``state_ps`` | ~889 ``spm_sample(ps)`` | ``_vb_gen_states_one_model`` |
| ``outcome_softmax`` | ~942 / softmax branch | ``_vb_generate_outcomes_if_options_o`` |
| ``outcome_GP_A`` | ~969 ``spm_sample(O{m,o,t})`` from ``GP.A`` | ``_vb_gp_outcome_sample_index`` |
| ``outcome_shared_po`` | ~1005 | ``_vb_shared_probabilistic_outcomes`` |
| ``child_spm_action`` | ~1087 ``spm_action`` | ``_spm_action`` |
| ``child_GD`` | ~1143 ``spm_sample(GD{f})`` | hierarchical process path |
| ``child_E`` / ``child_D`` | ~1155–1156 | hierarchical non-process path |
"""
from __future__ import annotations

import inspect
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.entry12_atari_calls import (
    entry12_assert_buf_k_coherent,
    entry12_fixtures_dir,
    entry12_load_vb_rand_buf_for_tag,
    entry12_log_signoff_chain,
    entry12_resolve_run_tag,
    entry12_vb_oracle_flags,
    load_entry12_rdp_for_tag,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

_OUT_SUMMARY = ROOT / "matlab_custom" / "entry12_draw_index_audit_results.json"

_TRACE_CTX: dict[str, Any] = {"t_gen": None, "pu_len": None}
_LAST_AUDIT_REPLAY: list[Any] = [None]

# Outermost frame name (in ``spm_MDP_VB_XXX``) → site id for trace rows.
_SITE_BY_FRAME: tuple[tuple[str, str], ...] = (
    ("_vb_prior_QP_paths_states_one_model", "policy"),
    ("_vb_gen_control_one_model", "control_P"),
    ("_vb_gen_states_one_model", "state_ps"),
    ("_vb_gen_u_paths_one_model", "gp_path_E"),
    ("_vb_gp_outcome_sample_index", "outcome_GP_A"),
    ("_vb_generate_outcomes_if_options_o", "outcome_softmax"),
    ("_vb_shared_probabilistic_outcomes", "outcome_shared_po"),
    ("_vb_hierarchical_subordinate_outcomes", "hierarchical"),
    ("_spm_action", "child_spm_action"),
    ("_vb_run_partial_t_loop", "vb_loop"),
    ("spm_MDP_VB_XXX", "vb_entry"),
)

_PATTERN_EXPECTED_DRAWS: dict[str, int] = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "N1": 1,
    "N0": 1,
}


class _AuditingRandReplay(vb._VbMatlabRandReplay):
    """``_VbMatlabRandReplay`` with draw index + history (script 3 replay path)."""

    def __init__(self, buf: np.ndarray) -> None:
        super().__init__(buf)
        self.draw_index = 0
        self.history: list[tuple[int, float]] = []
        _LAST_AUDIT_REPLAY[0] = self

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        v = float(super()._shim(*args, **kwargs))
        self.history.append((self.draw_index, v))
        self.draw_index += 1
        return v


def _sample_trace_path(tag: str) -> Path:
    return entry12_fixtures_dir() / f"entry12_sample_trace_{tag}.json"


def _infer_site_from_stack() -> str:
    """Map ``inspect.stack()`` to a stable site id (first matching VB frame)."""
    depth = int(vb._VB_TIMING_DEPTH)
    for fr in inspect.stack()[2:20]:
        name = fr.function
        if name == "_vb_spm_sample_column":
            # Hierarchical prep (parent ``t`` loop, before child recurse).
            if fr.lineno == 4218:
                return "child_GD"
            if fr.lineno == 4223:
                return "child_E"
            if fr.lineno == 4224:
                return "child_D"
            return "nested_child_sample_column" if depth >= 2 else "child_sample_column"
        for key, site in _SITE_BY_FRAME:
            if name == key:
                if depth >= 2 and site not in ("vb_loop", "vb_entry", "hierarchical"):
                    return f"nested_{site}"
                return site
    return "unknown"


def _describe_input(p: Any) -> dict[str, Any]:
    pa = np.asarray(p)
    flat = pa.ravel(order="F")
    nz = int(np.count_nonzero(flat)) if flat.size else 0
    is_bool = pa.dtype == bool
    is_01 = False
    if not is_bool and flat.size and np.issubdtype(pa.dtype, np.number):
        is_01 = bool(np.all((flat == 0) | (flat == 1)))
    vals_head = [float(x) for x in flat[:8].tolist()]
    return {
        "dtype": str(pa.dtype),
        "shape": list(pa.shape),
        "nz": nz,
        "is_bool": is_bool,
        "is_01_numeric": is_01,
        "vals_head": vals_head,
    }


def _classify_pattern(p: Any, *, n_draws: int) -> tuple[str, int, str]:
    """
    Return (pattern_id, k_mask, kind).

    ``k_mask`` = number of positive entries (logical ``find`` count or numeric nz).
    """
    pa = np.asarray(p)
    if pa.dtype == bool:
        k_mask = int(np.count_nonzero(pa))
        if k_mask == 1:
            pat = "L0"
        elif k_mask in (2, 3, 4):
            pat = "L2"
        else:
            pat = "L1"
        return pat, k_mask, "logical"
    flat = np.asarray(pa, dtype=np.float64).ravel(order="F")
    nz = int(np.count_nonzero(flat))
    total = float(np.sum(flat))
    if (not np.isfinite(total)) or total <= 0.0:
        return "N0", nz, "numeric_degenerate"
    return "N1", nz, "numeric"


def _run_replay_trace() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tag = entry12_resolve_run_tag()
    entry12_assert_buf_k_coherent(tag)
    paths = entry12_log_signoff_chain(tag, stream=sys.stderr)
    buf = entry12_load_vb_rand_buf_for_tag(tag)
    k = int(buf.size)
    summary: dict[str, Any] = {
        "tag": tag,
        "K": k,
        "buf_path": str(paths["rand_buf"]),
        "trace_path": str(_sample_trace_path(tag)),
    }

    trace: list[dict[str, Any]] = []
    orig_sample = vb._spm_sample

    def _logged_sample(p: Any) -> int:
        ar = _LAST_AUDIT_REPLAY[0]
        i0 = 0 if ar is None else int(ar.draw_index)
        out = int(orig_sample(p))
        i1 = 0 if ar is None else int(ar.draw_index)
        n_draws = i1 - i0
        pat, k_mask, kind = _classify_pattern(p, n_draws=n_draws)
        expected = _PATTERN_EXPECTED_DRAWS.get(pat, n_draws)
        desc = _describe_input(p)
        row = {
            "seq": len(trace),
            "site": _infer_site_from_stack(),
            "pattern": pat,
            "kind": kind,
            "k_mask": k_mask,
            "draw_start": i0,
            "draw_end": i1,
            "n_draws": n_draws,
            "expected_n_draws": expected,
            "pattern_draw_ok": n_draws == expected,
            "out": out,
            "depth": int(vb._VB_TIMING_DEPTH),
            "t_gen": _TRACE_CTX.get("t_gen"),
            **desc,
        }
        if row["site"] == "policy":
            row["pu_len"] = _TRACE_CTX.get("pu_len")
        trace.append(row)
        return out

    # Time context for generation / outcomes / hierarchy (script 3 loop).
    orig_gen = vb._vb_generation_paths_states
    orig_outcomes = vb._vb_generate_outcomes_if_options_o
    orig_shared = vb._vb_shared_probabilistic_outcomes
    orig_hier = vb._vb_hierarchical_subordinate_outcomes
    orig_prior = vb._vb_prior_QP_paths_states_one_model

    def _gen_hook(models, bundle, t_idx, M_row):
        _TRACE_CTX["t_gen"] = int(t_idx) + 1
        return orig_gen(models, bundle, t_idx, M_row)

    def _out_hook(models, bundle, t_idx, M_row):
        _TRACE_CTX["t_gen"] = int(t_idx) + 1
        return orig_outcomes(models, bundle, t_idx, M_row)

    def _shared_hook(models, bundle, t_idx, M_row):
        _TRACE_CTX["t_gen"] = int(t_idx) + 1
        return orig_shared(models, bundle, t_idx, M_row)

    def _hier_hook(models, bundle, t_idx, M_row, recurse_partial, *, reuse_matlab_draws=False):
        _TRACE_CTX["t_gen"] = int(t_idx) + 1
        return orig_hier(models, bundle, t_idx, M_row, recurse_partial, reuse_matlab_draws=reuse_matlab_draws)

    def _prior_hook(mi, bundle, t_idx, Pu_vec):
        _TRACE_CTX["t_gen"] = int(t_idx) + 1
        pu = np.asarray(Pu_vec, dtype=np.float64).ravel()
        _TRACE_CTX["pu_len"] = int(pu.size)
        return orig_prior(mi, bundle, t_idx, Pu_vec)

    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb_mod

    orig_replay_cls = vb._VbMatlabRandReplay
    orig_mod_replay_cls = vb_mod._VbMatlabRandReplay

    rdp = load_entry12_rdp_for_tag(tag)
    flags = entry12_vb_oracle_flags(reuse_matlab_draws=True)
    vb._VbMatlabRandReplay = _AuditingRandReplay  # type: ignore[misc,assignment]
    vb_mod._VbMatlabRandReplay = _AuditingRandReplay  # type: ignore[misc,assignment]
    vb._spm_sample = _logged_sample
    vb._vb_generation_paths_states = _gen_hook
    vb._vb_generate_outcomes_if_options_o = _out_hook
    vb._vb_shared_probabilistic_outcomes = _shared_hook
    vb._vb_hierarchical_subordinate_outcomes = _hier_hook
    vb._vb_prior_QP_paths_states_one_model = _prior_hook
    try:
        pdp = spm_MDP_VB_XXX(rdp, {}, **flags)
    finally:
        vb._VbMatlabRandReplay = orig_replay_cls
        vb_mod._VbMatlabRandReplay = orig_mod_replay_cls
        vb._spm_sample = orig_sample
        vb._vb_generation_paths_states = orig_gen
        vb._vb_generate_outcomes_if_options_o = orig_outcomes
        vb._vb_shared_probabilistic_outcomes = orig_shared
        vb._vb_hierarchical_subordinate_outcomes = orig_hier
        vb._vb_prior_QP_paths_states_one_model = orig_prior

    ar = _LAST_AUDIT_REPLAY[0]
    total = int(ar.draw_index) if ar is not None else 0
    summary["replay"] = {
        "total_draws": total,
        "unused_draws": k - total,
        "spm_sample_calls": len(trace),
        "PDP_G1": float(np.asarray(pdp["G"][0], dtype=np.float64).ravel()[0]),
    }
    return summary, trace


def _summarize_trace(trace: list[dict[str, Any]], buf: np.ndarray) -> dict[str, Any]:
    by_site = Counter(r["site"] for r in trace)
    by_pattern = Counter(r["pattern"] for r in trace)
    pattern_draw_mismatches = [r for r in trace if not r.get("pattern_draw_ok", True)]
    policy_rows = [r for r in trace if r.get("site") == "policy"]
    policy_multi = [r for r in policy_rows if int(r.get("pu_len") or 0) > 1]
    first_policy_multi: dict[str, Any] | None = None
    if policy_multi:
        r0 = policy_multi[0]
        i0 = int(r0["draw_start"])
        r_at = float(buf[i0]) if 0 <= i0 < buf.size else None
        r_next = float(buf[i0 + 1]) if i0 + 1 < buf.size else None
        pu_len = int(r0.get("pu_len") or 0)
        k_from_r = None
        k_from_r_next = None
        if r_at is not None and pu_len > 0:
            pu = np.ones(pu_len, dtype=np.float64) / float(pu_len)
            cs = np.cumsum(pu)
            k_from_r = int(np.flatnonzero(r_at < cs)[0] + 1) if r_at is not None else None
            if r_next is not None:
                k_from_r_next = int(np.flatnonzero(r_next < cs)[0] + 1)
        first_policy_multi = {
            "seq": r0["seq"],
            "t_gen": r0.get("t_gen"),
            "draw_start": i0,
            "draw_end": r0["draw_end"],
            "n_draws": r0["n_draws"],
            "out": r0["out"],
            "pu_len": pu_len,
            "r_at_draw_start": r_at,
            "r_at_draw_start_plus_1": r_next,
            "k_from_buf_at_start": k_from_r,
            "k_from_buf_at_start_plus_1": k_from_r_next,
            "mat_k_policy_t2_expected": 2,
        }
    # Window before first multi-action policy (for skew triage without ad-hoc scripts).
    pre_policy_window: list[dict[str, Any]] = []
    if first_policy_multi:
        i_pol = int(first_policy_multi["draw_start"])
        lo = max(0, i_pol - 12)
        hi = min(len(trace), i_pol + 4)
        pre_policy_window = [
            {
                "seq": r["seq"],
                "site": r["site"],
                "pattern": r["pattern"],
                "draw_start": r["draw_start"],
                "n_draws": r["n_draws"],
                "depth": r["depth"],
                "t_gen": r.get("t_gen"),
                "nz": r.get("nz"),
                "shape": r.get("shape"),
                "out": r["out"],
            }
            for r in trace
            if lo <= int(r["draw_start"]) < hi
        ]

    return {
        "by_site": dict(sorted(by_site.items())),
        "by_pattern": dict(sorted(by_pattern.items())),
        "pattern_draw_mismatch_count": len(pattern_draw_mismatches),
        "pattern_draw_mismatch_first10": pattern_draw_mismatches[:10],
        "policy_row_count": len(policy_rows),
        "policy_multi_pu_count": len(policy_multi),
        "first_policy_uniform_multi": first_policy_multi,
        "pre_policy_draw_window": pre_policy_window,
    }


def _run_native_sample_count() -> dict[str, int]:
    """Native RNG: count ``spm_sample`` calls (``dump_subentries=False``, no replay)."""
    n = [0]
    orig = vb._spm_sample

    def _count(p: Any) -> int:
        n[0] += 1
        return int(orig(p))

    tag = entry12_resolve_run_tag()
    rdp = load_entry12_rdp_for_tag(tag)
    vb._spm_sample = _count
    try:
        spm_MDP_VB_XXX(
            rdp,
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=False,
        )
    finally:
        vb._spm_sample = orig
    return {"native_spm_sample_calls": n[0]}


def main() -> int:
    summary, trace = _run_replay_trace()
    tag = str(summary["tag"])
    buf = entry12_load_vb_rand_buf_for_tag(tag)
    trace_path = _sample_trace_path(tag)
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    out: dict[str, Any] = {
        **summary,
        "native": _run_native_sample_count(),
        "trace_summary": _summarize_trace(trace, buf),
        "trace": trace,
        "coherence": {
            "protocol": "entry12_v5_preamble_rewind (buf from MATLAB post-rewind rand(K,1))",
            "note": (
                "Replay injects MATLAB scalars through np.random.rand in _spm_sample. "
                "Fix site class (pattern/dtype/skip), not buffer index, when skew appears."
            ),
        },
    }
    out["coherence"]["sample_calls_match"] = (
        out["replay"]["spm_sample_calls"] == out["native"]["native_spm_sample_calls"]
    )
    out["coherence"]["unused_draws_ok"] = out["replay"]["unused_draws"] == 0

    _OUT_SUMMARY.write_text(json.dumps({k: v for k, v in out.items() if k != "trace"}, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in out.items() if k != "trace"}, indent=2))
    print(f"wrote summary {_OUT_SUMMARY}")
    print(f"wrote trace ({len(trace)} rows) {trace_path}")
    fp = out["trace_summary"].get("first_policy_uniform_multi")
    if fp:
        print("[entry12 trace] first multi-action policy row:", json.dumps(fp, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
