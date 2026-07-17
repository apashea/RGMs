"""Deep Entry 4 spectral inspection (``eig.md`` §20) — read-only on dump fixtures."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import scipy.linalg as spla

from python_src.utils.eig_layout_research import (
    column_permutation_report,
    cyclic_shift_scores,
    greedy_match_abs_w,
    matrix_fingerprint,
)
from python_src.utils.eig_nobalance import eig_nobalance
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    STAGE_OK,
    chosen_from_spectral,
    classify_failure_stage,
    first_order_mismatch,
    granular_spectral_report,
    rgm_spectral_decisions,
    sub_hash,
)


def order_rank_diff_table(
    order_ref: np.ndarray,
    order_got: np.ndarray,
    absv_ref: np.ndarray,
    absv_got: np.ndarray,
    *,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    """Per-rank ``sort(abs(...),'descend')`` comparison (full table or truncated)."""
    o_ref = np.asarray(order_ref, dtype=np.int64).ravel()
    o_got = np.asarray(order_got, dtype=np.int64).ravel()
    absv_ref = np.asarray(absv_ref, dtype=np.float64).ravel()
    absv_got = np.asarray(absv_got, dtype=np.float64).ravel()
    n = min(o_ref.size, o_got.size)
    rows: list[dict[str, Any]] = []
    for rank in range(n):
        ir, ig = int(o_ref[rank]), int(o_got[rank])
        rows.append(
            {
                "rank": int(rank),
                "idx_ref": ir,
                "idx_got": ig,
                "match": bool(ir == ig),
                "absv_ref": float(absv_ref[ir]),
                "absv_got": float(absv_got[ig]),
                "absv_delta": float(abs(absv_ref[ir] - absv_got[ig])),
            }
        )
    if max_rows is not None and len(rows) > max_rows:
        # Keep head (large |absv|) + all mismatches
        mism = [r for r in rows if not r["match"]]
        head = rows[: max_rows]
        seen = {r["rank"] for r in head}
        for r in mism:
            if r["rank"] not in seen:
                head.append(r)
                seen.add(r["rank"])
        rows = sorted(head, key=lambda x: x["rank"])
    return rows


def chosen_rank_diff(
    active: np.ndarray,
    absv_ref: np.ndarray,
    order_ref: np.ndarray,
    absv_got: np.ndarray,
    order_got: np.ndarray,
    dx: int,
    u_thresh: float,
) -> dict[str, Any]:
    """Diff ``chosen`` sets and list active indices only in one lane."""
    c_ref = chosen_from_spectral(active, absv_ref, order_ref, dx, u_thresh)
    c_got = chosen_from_spectral(active, absv_got, order_got, dx, u_thresh)
    s_ref = set(int(x) for x in c_ref)
    s_got = set(int(x) for x in c_got)
    return {
        "chosen_ref": c_ref.tolist(),
        "chosen_got": c_got.tolist(),
        "only_in_ref": sorted(s_ref - s_got),
        "only_in_got": sorted(s_got - s_ref),
        "symmetric_diff_size": int(len(s_ref ^ s_got)),
    }


def compare_lanes_on_block(
    sub: np.ndarray,
    w_ref: np.ndarray,
    v_ref: np.ndarray,
    *,
    lanes: dict[str, Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]] | None = None,
) -> dict[str, Any]:
    """Run multiple eig implementations on one ``sub_mi`` vs MATLAB reference."""
    if lanes is None:
        lanes = {
            "eig_nobalance": eig_nobalance,
            "scipy.linalg.eig": lambda a: spla.eig(a, check_finite=False, overwrite_a=False),
            "numpy.linalg.eig": lambda a: np.linalg.eig(np.asarray(a, dtype=np.float64)),
        }
    ref = rgm_spectral_decisions(sub, w_ref, v_ref)
    lane_reports: dict[str, Any] = {}
    for name, fn in lanes.items():
        w_py, v_py = fn(np.asarray(sub, dtype=np.float64))
        got = rgm_spectral_decisions(sub, w_py, v_py)
        from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import analyze_w_stage

        w_stage = analyze_w_stage(ref["w"], got["w"])
        stage = classify_failure_stage(ref, got, w_stage=w_stage)
        lane_reports[name] = {
            "stage": stage,
            "jmax_ref": ref["jmax"],
            "jmax_got": got["jmax"],
            "order_ok": bool(np.array_equal(ref["order"], got["order"])),
            "w_stage": w_stage,
            "cyclic_shift": cyclic_shift_scores(ref["w"], got["w"]),
            "greedy_w_match": greedy_match_abs_w(ref["w"], got["w"]),
        }
    return {"sub_hash": sub_hash(sub), "n": ref["n"], "fingerprint": matrix_fingerprint(sub), "lanes": lane_reports}


def deep_block_inspection(
    blk: dict[str, Any],
    probe_rec: dict[str, Any] | None,
    *,
    lane_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] = eig_nobalance,
    lane_label: str = "eig_nobalance",
    order_table_max_rows: int | None = 32,
) -> dict[str, Any]:
    """Full inspection packet for one oracle block (+ optional probe context)."""
    sub = np.asarray(blk["sub_mi"], dtype=np.float64)
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    granular = granular_spectral_report(
        sub, w_ref, v_ref, eig_fn=lane_fn, label=lane_label, probe_rec=probe_rec
    )
    ref = rgm_spectral_decisions(sub, w_ref, v_ref)
    w_py, v_py = lane_fn(np.asarray(sub, dtype=np.float64))
    got = rgm_spectral_decisions(sub, w_py, v_py)

    perm = column_permutation_report(
        ref["w"], got["w"], ref["v"], got["v"], jmax_ref=ref["jmax"], jmax_got=got["jmax"]
    )
    order_table = order_rank_diff_table(
        ref["order"], got["order"], ref["absv"], got["absv"], max_rows=order_table_max_rows
    )
    n_mismatch_ranks = sum(1 for r in order_table if not r["match"])

    out: dict[str, Any] = {
        "sub_hash": granular["sub_hash"],
        "n": granular["n"],
        "stage": granular["stage"],
        "context": granular.get("context"),
        "granular_summary": {
            "order_ok": granular["order_ok"],
            "jmax_ok": granular["jmax_ok"],
            "w_stage": granular["w_stage"],
            "order_first_mismatch": granular["order_first_mismatch"],
            "chosen": granular.get("chosen"),
        },
        "fingerprint": matrix_fingerprint(sub),
        "layout_research": perm,
        "cyclic_shift": cyclic_shift_scores(ref["w"], got["w"]),
        "order_rank_table": order_table,
        "order_rank_mismatch_count": int(n_mismatch_ranks),
        "order_rank_table_truncated": bool(order_table_max_rows is not None and ref["n"] > order_table_max_rows),
    }
    if probe_rec is not None:
        active = np.asarray(probe_rec["active_before"], dtype=np.int64)
        out["chosen_diff"] = chosen_rank_diff(
            active,
            ref["absv"],
            ref["order"],
            got["absv"],
            got["order"],
            int(probe_rec["dx"]),
            float(probe_rec["u_thresh"]),
        )
    out["multi_lane"] = compare_lanes_on_block(sub, w_ref, v_ref)
    return out


def build_failure_index(
    inspections: list[dict[str, Any]], *, pass_stage: str = STAGE_OK
) -> dict[str, Any]:
    """Compact index: failing hashes, stages, FSL context, key scalars."""
    failing = [x for x in inspections if x.get("stage") != pass_stage]
    passing = [x for x in inspections if x.get("stage") == pass_stage]
    by_stage: dict[str, list[str]] = {}
    for x in failing:
        st = str(x.get("stage", "UNKNOWN"))
        by_stage.setdefault(st, []).append(str(x["sub_hash"]))
    rows = []
    for x in failing:
        ws = (x.get("granular_summary") or {}).get("w_stage") or {}
        ctx = x.get("context") or {}
        rows.append(
            {
                "sub_hash": x["sub_hash"],
                "n": x["n"],
                "stage": x["stage"],
                "lev_call": ctx.get("lev_call"),
                "stream_idx": ctx.get("stream_idx"),
                "iter_idx": ctx.get("iter_idx"),
                "jmax_ref": ws.get("jmax_ref"),
                "jmax_got": ws.get("jmax_got"),
                "max_abs_w_diff": ws.get("max_abs_w_diff"),
                "sorted_abs_w_max_diff": ws.get("sorted_abs_w_max_diff"),
                "greedy_max_pair_w_diff": (x.get("layout_research") or {})
                .get("greedy_w_match", {})
                .get("max_pair_abs_w_diff"),
                "best_cyclic_shift": (x.get("cyclic_shift") or {}).get("best_shift"),
                "best_cyclic_max_abs_w_diff": (x.get("cyclic_shift") or {}).get("best_max_abs_w_diff"),
                "order_rank_mismatch_count": x.get("order_rank_mismatch_count"),
            }
        )
    return {
        "n_total": len(inspections),
        "n_pass": len(passing),
        "n_fail": len(failing),
        "by_stage_hashes": by_stage,
        "failing_rows": rows,
    }


def build_failure_replay_bundle(
    blocks: list[dict[str, Any]],
    inspections: list[dict[str, Any]],
    *,
    include_passing: bool = False,
) -> dict[str, Any]:
    """PKL-ready bundle: ``sub_mi`` + MATLAB ``(w,V)`` + probe fields for failing blocks."""
    fail_hashes = {
        x["sub_hash"]
        for x in inspections
        if include_passing or x.get("stage") != STAGE_OK
    }
    entries = []
    for blk, insp in zip(blocks, inspections):
        h = insp["sub_hash"]
        if h not in fail_hashes:
            continue
        entries.append(
            {
                "sub_hash": h,
                "n": int(insp["n"]),
                "stage": insp["stage"],
                "sub_mi": np.asarray(blk["sub_mi"], dtype=np.float64),
                "vals_mat": np.asarray(blk["vals_mat"], dtype=np.complex128),
                "vecs_mat": np.asarray(blk["vecs_mat"], dtype=np.complex128),
                "context": insp.get("context"),
                "inspection": insp,
            }
        )
    return {
        "purpose": "Replay corpus for MATLAB-nobalance eig research (Entry 4 isolated lane)",
        "n_entries": len(entries),
        "entries": entries,
    }
