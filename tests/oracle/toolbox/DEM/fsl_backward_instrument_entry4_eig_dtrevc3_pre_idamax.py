#!/usr/bin/env python3
"""Entry 4 E2e–E2i — DGEEVX computation-order VR ladder (``eig.md`` §4.1)."""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_lapack_nobalance import (
    dtrevc3_debug_get,
    dtrevc3_debug_get_qr0_sweep_table,
    dtrevc3_debug_get_qr0_sweep37_boundary,
    dtrevc3_debug_get_qr0_sweep6_post_dlaqr5,
    dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5,
    dtrevc3_debug_get_qr0_sweep7_boundary,
    dtrevc3_debug_get_qr5_in_plate,
    dtrevc3_debug_get_qr5_out5_plate,
    dtrevc3_debug_get_qr5_plate_trace,
    dtrevc3_debug_get_qr5_s5_intra_trace,
    dtrevc3_debug_get_qr5_s5_zpre_subtrace,
    dtrevc3_debug_get_qr5_s5_z1_do140,
    dtrevc3_debug_get_qr5_s5_z1_gap,
    dtrevc3_debug_get_qr5_s5_z145_pre_zp1,
    dtrevc3_debug_get_qr5_s5_zp1_boundary,
    dtrevc3_debug_reset,
    dtrevc3_debug_set_col,
    eig_real_nobalance,
    lapack_nobalance_available,
)
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

MODE_B_HASH = "2d5f8b838be81f21"
PLATEAU_IDX = (13, 44)

# DGEEVX order for JOBVR='V', BALANC='N' (our driver):
#   DGEBAL → DGEHRD → DLACPY+ DORGHR → DHSEQR → DTREVC3 → (finalize)


def _leader(a13: float, a44: float) -> int:
    if a13 > a44:
        return 13
    if a44 > a13:
        return 44
    return 13


def _ulp_row_pick(a13: float, a44: float) -> dict[str, Any]:
    diff = float(a13) - float(a44)
    tol = 1e-15 * max(abs(a13), abs(a44), 1.0)
    if abs(diff) <= tol:
        pick = "tie"
        matlab_first_max = 13
    elif diff > 0:
        pick = "13"
        matlab_first_max = 13
    else:
        pick = "44"
        matlab_first_max = 44
    return {
        "abs_13": float(a13),
        "abs_44": float(a44),
        "diff_13_minus_44": diff,
        "leader_0based": _leader(a13, a44),
        "strict_pick": pick,
        "matlab_max_abs_first": matlab_first_max,
    }


def _sweep6_body_trace(
    qr5_out5_plate: dict[str, float | int],
    plate_trace: dict[str, Any],
    sweep7: dict[str, float | int],
) -> dict[str, Any]:
    """E2i-n1f — latch sweep 6 DLAQR5 exit plate; bridge entry -> sweep 7 pre."""
    if int(qr5_out5_plate.get("hit", 0)) != 1:
        return {"hit": 0}

    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    s6_in_hit = int(s6_in.get("hit", 0)) == 1

    entry_eq_exit = False
    if s6_in_hit:
        entry_eq_exit = (
            float(s6_in["z13_k"]) == float(qr5_out5_plate["z13_k"])
            and float(s6_in["z44_k"]) == float(qr5_out5_plate["z44_k"])
            and float(s6_in["z13_kp1"]) == float(qr5_out5_plate["z13_kp1"])
            and float(s6_in["z44_kp1"]) == float(qr5_out5_plate["z44_kp1"])
        )

    exit_eq_s7_pre = False
    s7_pre_kp1: float | None = None
    if int(sweep7.get("hit", 0)) == 1:
        s7_pre_kp1 = float(sweep7["pre_kp1_delta"])
        exit_eq_s7_pre = (
            float(qr5_out5_plate["z13_k"]) == float(sweep7["pre_z13_k"])
            and float(qr5_out5_plate["z44_k"]) == float(sweep7["pre_z44_k"])
            and float(qr5_out5_plate["z13_kp1"]) == float(sweep7["pre_z13_kp1"])
            and float(qr5_out5_plate["z44_kp1"]) == float(sweep7["pre_z44_kp1"])
        )

    return {
        "hit": 1,
        "qrsweep": int(qr5_out5_plate["qrsweep"]),
        "dlaqr0_sweep": int(qr5_out5_plate["dlaqr0_sweep"]),
        "entry_kp1_delta": float(s6_in["kp1_delta"]) if s6_in_hit else None,
        "exit_kp1_delta": float(qr5_out5_plate["kp1_delta"]),
        "s7_pre_kp1_delta": s7_pre_kp1,
        "entry_eq_exit": entry_eq_exit,
        "exit_eq_sweep7_pre": exit_eq_s7_pre,
        "entry_rewrite_in_sweep6_body": s6_in_hit and not entry_eq_exit,
        "z13_k": float(qr5_out5_plate["z13_k"]),
        "z44_k": float(qr5_out5_plate["z44_k"]),
        "z13_kp1": float(qr5_out5_plate["z13_kp1"]),
        "z44_kp1": float(qr5_out5_plate["z44_kp1"]),
        "kp1_delta": float(qr5_out5_plate["kp1_delta"]),
        "k_delta": float(qr5_out5_plate["k_delta"]),
        "z44_k_zero": float(qr5_out5_plate["z44_k"]) == 0.0,
    }


def _plate_equal(a: dict[str, float | int], b: dict[str, float | int]) -> bool:
    return (
        float(a["z13_k"]) == float(b["z13_k"])
        and float(a["z44_k"]) == float(b["z44_k"])
        and float(a["z13_kp1"]) == float(b["z13_kp1"])
        and float(a["z44_kp1"]) == float(b["z44_kp1"])
    )


def _is_asymmetric_plate(plate: dict[str, float | int]) -> bool:
    return float(plate["z44_k"]) == 0.0 or float(plate["z13_kp1"]) == 0.0


def _sweep6_intra_trace(
    intra: dict[str, Any],
    plate_trace: dict[str, Any],
    qr0_post_plate: dict[str, float | int],
) -> dict[str, Any]:
    """E2i-n1h — locate first asymmetric plate inside sweep-6 DLAQR5."""
    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    if int(s6_in.get("hit", 0)) != 1:
        return {"hit": 0}

    stages: list[tuple[str, int, dict[str, float | int]]] = [
        ("entry", 0, s6_in),
    ]
    if int(intra.get("zpre_hit", 0)) == 1:
        stages.append(("zpre", 5, intra["zpre"]))
    if int(intra.get("dir_hit", 0)) == 1:
        stages.append(("dir", 2, intra["dir"]))
    if int(intra.get("gem_hit", 0)) == 1:
        stages.append(("gem", 3, intra["gem"]))
    if int(intra.get("fas_hit", 0)) == 1:
        stages.append(("fas", int(intra["fas_stage"]), intra["fas"]))
    if int(intra.get("out_hit", 0)) == 1:
        stages.append(("out", 4, intra["out"]))
    if int(qr0_post_plate.get("hit", 0)) == 1:
        stages.append(("qr0_post", 99, qr0_post_plate))

    first_asym: str | None = None
    first_asym_stage: int | None = None
    for name, stage_id, plate in stages:
        if _is_asymmetric_plate(plate):
            first_asym = name
            first_asym_stage = stage_id
            break

    qr0_eq_out = False
    if int(intra.get("out_hit", 0)) == 1 and int(qr0_post_plate.get("hit", 0)) == 1:
        qr0_eq_out = _plate_equal(intra["out"], qr0_post_plate)

    entry_eq_zpre = False
    if int(intra.get("zpre_hit", 0)) == 1:
        entry_eq_zpre = _plate_equal(s6_in, intra["zpre"])

    return {
        "hit": 1,
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_hit": int(intra.get("zpre_hit", 0)),
        "dir_hit": int(intra.get("dir_hit", 0)),
        "gem_hit": int(intra.get("gem_hit", 0)),
        "out_hit": int(intra.get("out_hit", 0)),
        "fas_hit": int(intra.get("fas_hit", 0)),
        "fas_stage": int(intra.get("fas_stage", 0)),
        "zpre_iters": int(intra.get("zpre_iters", 0)),
        "kacc22": int(intra.get("kacc22", 0)),
        "z140_steps": int(intra.get("z140_steps", 0)),
        "z140_iters": int(intra.get("z140_iters", 0)),
        "entry_eq_zpre": entry_eq_zpre,
        "out_eq_qr0_post": qr0_eq_out,
        "first_asymmetry_site": first_asym,
        "first_asymmetry_stage": first_asym_stage,
        "entry_asymmetric": _is_asymmetric_plate(s6_in),
        "zpre_asymmetric": (
            _is_asymmetric_plate(intra["zpre"])
            if int(intra.get("zpre_hit", 0)) == 1
            else None
        ),
        "dir_asymmetric": (
            _is_asymmetric_plate(intra["dir"])
            if int(intra.get("dir_hit", 0)) == 1
            else None
        ),
        "gem_asymmetric": (
            _is_asymmetric_plate(intra["gem"])
            if int(intra.get("gem_hit", 0)) == 1
            else None
        ),
        "out_asymmetric": (
            _is_asymmetric_plate(intra["out"])
            if int(intra.get("out_hit", 0)) == 1
            else None
        ),
        "qr0_post_asymmetric": (
            _is_asymmetric_plate(qr0_post_plate)
            if int(qr0_post_plate.get("hit", 0)) == 1
            else None
        ),
        "stages": {
            name: {
                "stage_id": stage_id,
                "plate": plate,
                "asymmetric": _is_asymmetric_plate(plate),
            }
            for name, stage_id, plate in stages
        },
    }


def _sweep6_zpre_sub_trace(
    zpre_sub: dict[str, Any],
    plate_trace: dict[str, Any],
) -> dict[str, Any]:
    """E2i-n1i — first / first-asymmetric / last zpre iter inside sweep-6 DLAQR5."""
    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    if int(s6_in.get("hit", 0)) != 1 or int(zpre_sub.get("zp1_hit", 0)) != 1:
        return {"hit": 0}

    zp1 = zpre_sub["zp1"]
    zlast = zpre_sub["zlast"]
    entry_eq_zp1 = _plate_equal(s6_in, zp1)
    zp1_eq_zlast = _plate_equal(zp1, zlast)
    zp1_asym = _is_asymmetric_plate(zp1)
    zlast_asym = _is_asymmetric_plate(zlast)

    zpa_hit = int(zpre_sub.get("zpa_hit", 0)) == 1
    zpa_iter: int | None
    if zpa_hit:
        zpa_iter = int(zpre_sub.get("zpa_iter", 0))
    elif zp1_asym:
        zpa_iter = 1
    else:
        zpa_iter = None
    rewrite_site: str | None = None
    if not entry_eq_zp1:
        if zp1_asym:
            rewrite_site = "first_zpre_iter_snap"
        elif zpa_hit and zpa_iter == 1:
            rewrite_site = "within_first_zpre_iter"
        elif zpa_hit:
            rewrite_site = f"zpre_iter_{zpa_iter}"
        else:
            rewrite_site = "between_entry_and_last_zpre"
    elif zpa_hit:
        rewrite_site = (
            "after_first_zpre_before_zpa"
            if zpa_iter and zpa_iter > 1
            else "unknown_post_zp1"
        )

    return {
        "hit": 1,
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_iters": int(zpre_sub.get("zpre_iters", 0)),
        "zp1_hit": int(zpre_sub["zp1_hit"]),
        "zpa_hit": int(zpre_sub.get("zpa_hit", 0)),
        "zpa_iter": zpa_iter,
        "entry_eq_zp1": entry_eq_zp1,
        "zp1_eq_zlast": zp1_eq_zlast,
        "zp1_asymmetric": zp1_asym,
        "zlast_asymmetric": zlast_asym,
        "rewrite_site": rewrite_site,
        "entry": s6_in,
        "zp1": zp1,
        "zpa": zpre_sub["zpa"] if zpa_hit else None,
        "zlast": zlast,
    }


def _sweep6_z1_do140_trace(
    z1_do140: dict[str, Any],
    zpre_sub: dict[str, Any],
    plate_trace: dict[str, Any],
) -> dict[str, Any]:
    """E2i-n1j — per-M DO140 plates during first zpre iter inside sweep-6 DLAQR5."""
    if int(z1_do140["m5"]["hit"]) != 1:
        return {"hit": 0}

    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    zp1 = zpre_sub.get("zp1", {}) if int(zpre_sub.get("zp1_hit", 0)) == 1 else None

    m_chain: list[tuple[int, dict[str, Any]]] = []
    for m in (5, 4, 3, 2, 1):
        slot = z1_do140[f"m{m}"]
        if int(slot["hit"]) == 1:
            m_chain.append((m, slot["plate"]))

    first_asym_m: int | None = int(z1_do140["first_asym_m"]) or None
    if first_asym_m == 0:
        first_asym_m = None

    last_sym_m: int | None = None
    for m, plate in m_chain:
        if _is_asymmetric_plate(plate):
            break
        last_sym_m = m

    zp1_eq_last_m = False
    if zp1 is not None and m_chain:
        zp1_eq_last_m = _plate_equal(zp1, m_chain[-1][1])

    rewrite_m: int | None = None
    if first_asym_m is not None:
        rewrite_m = first_asym_m
    elif zp1 is not None and _is_asymmetric_plate(zp1) and last_sym_m is not None:
        rewrite_m = last_sym_m + 1 if last_sym_m < 5 else last_sym_m

    return {
        "hit": 1,
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_iter": 1,
        "do140_steps": int(z1_do140["do140_steps"]),
        "first_asym_m": first_asym_m,
        "last_sym_m_before_asym": last_sym_m,
        "rewrite_m": rewrite_m,
        "entry_eq_m5": (
            _plate_equal(s6_in, m_chain[0][1])
            if int(s6_in.get("hit", 0)) == 1 and m_chain
            else None
        ),
        "zp1_eq_last_do140_m": zp1_eq_last_m,
        "m_plates": {
            str(m): {
                "asymmetric": _is_asymmetric_plate(plate),
                "plate": plate,
            }
            for m, plate in m_chain
        },
    }


def _sweep6_z1_gap_trace(
    z1_gap: dict[str, Any],
    z1_do140: dict[str, Any],
    zpre_sub: dict[str, Any],
    plate_trace: dict[str, Any],
) -> dict[str, Any]:
    """E2i-n1k — ordered first-``zpre``-iter timeline: entry → zp1 → M5 → post-DO140 → dir."""
    if int(zpre_sub.get("zp1_hit", 0)) != 1:
        return {"hit": 0}

    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    zp1 = zpre_sub["zp1"]
    timeline: list[tuple[str, dict[str, Any] | None]] = [
        ("entry", s6_in if int(s6_in.get("hit", 0)) == 1 else None),
        ("zp1_pre_do140", zp1),
    ]
    if int(z1_do140.get("m5", {}).get("hit", 0)) == 1:
        timeline.append(("m5_do140", z1_do140["m5"]["plate"]))
    post_slot = z1_gap.get("post_do140", {})
    if int(post_slot.get("hit", 0)) == 1:
        timeline.append(("post_do140", post_slot["plate"]))
    dir_slot = z1_gap.get("z1_dir1", {})
    if int(dir_slot.get("hit", 0)) == 1:
        timeline.append(("z1_dir1", dir_slot["plate"]))

    stages: list[dict[str, Any]] = []
    first_asym_site: str | None = None
    rewrite_site: str | None = None
    prev_plate: dict[str, Any] | None = None
    prev_sym = True
    for name, plate in timeline:
        if plate is None:
            continue
        asym = _is_asymmetric_plate(plate)
        eq_prev = _plate_equal(plate, prev_plate) if prev_plate is not None else None
        stages.append(
            {
                "name": name,
                "asymmetric": asym,
                "eq_prev": eq_prev,
                "plate": plate,
            }
        )
        if first_asym_site is None and asym:
            first_asym_site = name
        if rewrite_site is None and prev_plate is not None and not eq_prev:
            if asym and prev_sym:
                rewrite_site = name
            elif name == "zp1_pre_do140" and not _plate_equal(s6_in, zp1):
                rewrite_site = "entry_to_zp1_pre_do140"
        prev_plate = plate
        prev_sym = asym

    if rewrite_site is None and first_asym_site is not None:
        rewrite_site = first_asym_site

    return {
        "hit": 1,
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_iter": 1,
        "first_asym_site": first_asym_site,
        "rewrite_site": rewrite_site,
        "entry_eq_zp1": (
            _plate_equal(s6_in, zp1) if int(s6_in.get("hit", 0)) == 1 else None
        ),
        "zp1_eq_m5": (
            _plate_equal(zp1, z1_do140["m5"]["plate"])
            if int(z1_do140.get("m5", {}).get("hit", 0)) == 1
            else None
        ),
        "m5_eq_post_do140": (
            _plate_equal(z1_do140["m5"]["plate"], post_slot["plate"])
            if int(z1_do140.get("m5", {}).get("hit", 0)) == 1
            and int(post_slot.get("hit", 0)) == 1
            else None
        ),
        "post_eq_dir1": (
            _plate_equal(post_slot["plate"], dir_slot["plate"])
            if int(post_slot.get("hit", 0)) == 1 and int(dir_slot.get("hit", 0)) == 1
            else None
        ),
        "stages": stages,
    }


def _sweep6_z145_pre_zp1_trace(
    z145: dict[str, Any],
    zpre_sub: dict[str, Any],
    plate_trace: dict[str, Any],
) -> dict[str, Any]:
    """E2i-n1l — ``DO 41`` / pre-``zp1`` gap before first stage-**5** snap."""
    if int(zpre_sub.get("zp1_hit", 0)) != 1:
        return {"hit": 0}

    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    zp1 = zpre_sub["zp1"]
    z41_fa = z145["z41_first_asym"]
    z41_ls = z145["z41_last_sym"]
    pre_zp1 = z145["pre_zp1"]

    rewrite_site: str | None = None
    first_asym_site: str | None = None

    if int(z41_fa["hit"]) == 1:
        first_asym_site = "z41_do41"
        rewrite_site = "z41_do41"
    elif _is_asymmetric_plate(pre_zp1["plate"]):
        first_asym_site = "pre_zp1_snap"
        if int(s6_in.get("hit", 0)) == 1 and not _plate_equal(s6_in, pre_zp1["plate"]):
            rewrite_site = "entry_to_pre_zp1"
        else:
            rewrite_site = "pre_zp1_snap"
    elif _is_asymmetric_plate(zp1):
        first_asym_site = "zp1_pre_do140"
        rewrite_site = "pre_zp1_to_zp1"

    last_sym_eq_entry = (
        _plate_equal(s6_in, z41_ls["plate"])
        if int(s6_in.get("hit", 0)) == 1 and int(z41_ls["hit"]) == 1
        else None
    )
    pre_zp1_eq_zp1 = _plate_equal(pre_zp1["plate"], zp1)
    last_sym_eq_pre_zp1 = (
        _plate_equal(z41_ls["plate"], pre_zp1["plate"])
        if int(z41_ls["hit"]) == 1 and int(pre_zp1["hit"]) == 1
        else None
    )

    return {
        "hit": 1,
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "z41_hit": int(z145["z41_hit"]),
        "z41_steps": int(z145["z41_steps"]),
        "first_asym_site": first_asym_site,
        "rewrite_site": rewrite_site,
        "last_sym_eq_entry": last_sym_eq_entry,
        "last_sym_eq_pre_zp1": last_sym_eq_pre_zp1,
        "pre_zp1_eq_zp1": pre_zp1_eq_zp1,
        "entry_eq_zp1": (
            _plate_equal(s6_in, zp1) if int(s6_in.get("hit", 0)) == 1 else None
        ),
        "z41_first_asym": z41_fa,
        "z41_last_sym": z41_ls,
        "pre_zp1": pre_zp1,
        "zp1": zp1,
    }


def _sweep6_zp1_boundary_trace(
    boundary: dict[str, Any],
    z145: dict[str, Any],
    plate_trace: dict[str, Any],
) -> dict[str, Any]:
    """E2i-n1o — atomic sweep-6 commit latch + ``S5Z1D`` slot drift audit."""
    if int(boundary.get("s5inl_hit", 0)) != 1:
        return {"hit": 0}

    s6_in = plate_trace.get("sweep6_dlaqr5_entry", {})
    pre_zp1 = boundary["pre_zp1"]
    s5inl = boundary["s5inl"]
    s5inc = boundary["s5inc"]
    zp1 = boundary["zp1"]
    commit_zp1 = boundary.get("commit_zp1", {})
    commit_s5inc = boundary.get("commit_s5inc", {})
    s5inl_it = int(boundary.get("s5inl_it", 0))
    s5inc_it = int(boundary.get("s5inc_it", 0))
    zp1_it = int(boundary.get("zp1_it", 0))
    scope_it = int(boundary.get("scope_it", 0))
    pend_it = int(boundary.get("pend_it", 0))

    col_match = (
        boundary["dbg_col"] == boundary["pre_zp1_col"] == boundary["zp1_col"]
    )
    krcol_match = boundary["pre_zp1_krcol"] == boundary["zp1_krcol"]
    capture_it_match = s5inl_it == s5inc_it == zp1_it
    sweep6_capture_it = s5inl_it == 4
    scope_it_stale_at_getter = scope_it != s5inl_it
    s6commit_hit = int(boundary.get("s6commit_hit", 0))
    slot_eq_commit = boundary.get("slot_eq_commit")
    commit_eq_s5inc = (
        _plate_equal(commit_s5inc, s5inc) if s6commit_hit == 1 else None
    )
    commit_eq_zp1 = (
        _plate_equal(commit_zp1, zp1) if s6commit_hit == 1 else None
    )

    boundary_kind: str | None = None
    alignment_kind: str | None = None
    first_asym_site: str | None = None
    rewrite_site: str | None = None

    if not col_match:
        boundary_kind = "col_mismatch"
    elif not krcol_match:
        boundary_kind = "krcol_mismatch"
    elif not capture_it_match:
        boundary_kind = "capture_it_mismatch"
    elif not sweep6_capture_it:
        boundary_kind = "capture_it_not_sweep6"
    elif _plate_equal(pre_zp1, s5inl) and _plate_equal(s5inl, s5inc) and _plate_equal(
        s5inc, zp1
    ):
        boundary_kind = "plates_identical"
    elif _plate_equal(s5inl, s5inc) and _plate_equal(s5inc, zp1) and not _plate_equal(
        pre_zp1, s5inl
    ):
        boundary_kind = "pre_zp1_latch_stale"
    elif _plate_equal(s5inl, s5inc) and not _plate_equal(s5inc, zp1):
        boundary_kind = "zp1_after_s5inc"
        if _is_asymmetric_plate(zp1) and not _is_asymmetric_plate(s5inc):
            first_asym_site = "zp1_post_s5inc"
            rewrite_site = "s5inc_to_zp1"
    if s6commit_hit == 1 and commit_eq_s5inc is True and slot_eq_commit is False:
        alignment_kind = "s5z1d_slot_drift"
    elif s6commit_hit == 1 and commit_eq_s5inc is True and slot_eq_commit is True:
        alignment_kind = "slots_aligned"
    elif s6commit_hit == 1 and commit_eq_s5inc is False:
        alignment_kind = "bndd_slot_drift"
    elif s6commit_hit == 0:
        alignment_kind = "commit_not_armed"
    elif not _plate_equal(s5inl, s5inc):
        boundary_kind = "s5inl_ne_s5inc"
    elif _plate_equal(pre_zp1, s5inl) and not _plate_equal(s5inl, zp1):
        boundary_kind = "zp1_after_counters"
        if _is_asymmetric_plate(zp1) and not _is_asymmetric_plate(pre_zp1):
            first_asym_site = "zp1_pre_do140"
            rewrite_site = "pre_zp1_to_zp1"
    else:
        boundary_kind = "mixed_plate_drift"

    return {
        "hit": 1,
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "dbg_col": boundary["dbg_col"],
        "pre_zp1_col": boundary["pre_zp1_col"],
        "zp1_col": boundary["zp1_col"],
        "pre_zp1_krcol": boundary["pre_zp1_krcol"],
        "zp1_krcol": boundary["zp1_krcol"],
        "pend_it": pend_it,
        "scope_it": scope_it,
        "s5inl_it": s5inl_it,
        "s5inc_it": s5inc_it,
        "zp1_it": zp1_it,
        "s5inc_hit": int(boundary.get("s5inc_hit", 0)),
        "s6commit_hit": s6commit_hit,
        "slot_eq_commit": slot_eq_commit,
        "commit_eq_s5inc": commit_eq_s5inc,
        "commit_eq_zp1": commit_eq_zp1,
        "alignment_kind": alignment_kind,
        "col_match": col_match,
        "krcol_match": krcol_match,
        "sweep6_capture_it": sweep6_capture_it,
        "scope_it_stale_at_getter": scope_it_stale_at_getter,
        "capture_it_match": capture_it_match,
        "boundary_kind": boundary_kind,
        "first_asym_site": first_asym_site,
        "rewrite_site": rewrite_site,
        "pre_zp1_eq_s5inl": _plate_equal(pre_zp1, s5inl),
        "s5inl_eq_s5inc": _plate_equal(s5inl, s5inc),
        "s5inc_eq_zp1": _plate_equal(s5inc, zp1),
        "s5inl_eq_zp1": _plate_equal(s5inl, zp1),
        "pre_zp1_eq_zp1": _plate_equal(pre_zp1, zp1),
        "entry_eq_s5inl": (
            _plate_equal(s6_in, s5inl) if int(s6_in.get("hit", 0)) == 1 else None
        ),
        "entry_eq_s5inc": (
            _plate_equal(s6_in, s5inc) if int(s6_in.get("hit", 0)) == 1 else None
        ),
        "entry_eq_zp1": (
            _plate_equal(s6_in, zp1) if int(s6_in.get("hit", 0)) == 1 else None
        ),
        "pre_zp1_asymmetric": _is_asymmetric_plate(pre_zp1),
        "s5inl_asymmetric": _is_asymmetric_plate(s5inl),
        "s5inc_asymmetric": _is_asymmetric_plate(s5inc),
        "zp1_asymmetric": _is_asymmetric_plate(zp1),
        "pre_zp1": pre_zp1,
        "s5inl": s5inl,
        "s5inc": s5inc,
        "zp1": zp1,
        "commit_s5inc": commit_s5inc,
        "commit_zp1": commit_zp1,
        "z145_pre_zp1_hit": int(z145.get("pre_zp1", {}).get("hit", 0)),
    }


def _sweep6_gap_trace(
    qr5_out5_plate: dict[str, float | int],
    qr0_post_plate: dict[str, float | int],
    sweep7: dict[str, float | int],
) -> dict[str, Any]:
    """E2i-n1g — triangulate DLAQR5 exit vs dlaqr0 post-return vs sweep 7 pre."""
    if int(qr0_post_plate.get("hit", 0)) != 1:
        return {"hit": 0}

    s7_pre = None
    qr0_eq_s7_pre = False
    if int(sweep7.get("hit", 0)) == 1:
        s7_pre = {
            "z13_k": float(sweep7["pre_z13_k"]),
            "z44_k": float(sweep7["pre_z44_k"]),
            "z13_kp1": float(sweep7["pre_z13_kp1"]),
            "z44_kp1": float(sweep7["pre_z44_kp1"]),
        }
        qr0_eq_s7_pre = _plate_equal(qr0_post_plate, s7_pre)

    qr5_eq_qr0 = False
    if int(qr5_out5_plate.get("hit", 0)) == 1:
        qr5_eq_qr0 = _plate_equal(qr5_out5_plate, qr0_post_plate)

    asymmetric_at_qr0 = (
        float(qr0_post_plate["z44_k"]) == 0.0
        or float(qr0_post_plate["z13_kp1"]) == 0.0
    )
    return {
        "hit": 1,
        "it": int(qr0_post_plate["it"]),
        "qrsweep_at_post": int(qr0_post_plate["qrsweep_at_post"]),
        "qr5_out_eq_qr0_post": qr5_eq_qr0,
        "qr0_post_eq_sweep7_pre": qr0_eq_s7_pre,
        "asymmetric_at_qr0_post": asymmetric_at_qr0,
        "qr0_post_kp1_delta": float(qr0_post_plate["kp1_delta"]),
        "s7_pre_kp1_delta": (
            float(sweep7["pre_kp1_delta"])
            if int(sweep7.get("hit", 0)) == 1
            else None
        ),
        "qr5_out_kp1_delta": (
            float(qr5_out5_plate["kp1_delta"])
            if int(qr5_out5_plate.get("hit", 0)) == 1
            else None
        ),
        "qr0_post": qr0_post_plate,
        "gap_site": (
            "none_qr0_matches_s7_pre"
            if qr0_eq_s7_pre
            else (
                "dlaqr5_exit_ne_qr0_post"
                if int(qr5_out5_plate.get("hit", 0)) == 1 and not qr5_eq_qr0
                else "qr0_post_ne_sweep7_pre"
            )
        ),
    }


def _sweep7_flip_trace(
    sweep7: dict[str, float | int],
    plate_trace: dict[str, Any],
    qr5_in_plate: dict[str, float | int],
) -> dict[str, Any]:
    """E2i-n1e — does sweep 7 DLAQR3 flip signed kp1_delta between sweeps 6 and 8?"""
    if int(sweep7.get("hit", 0)) != 1:
        return {"hit": 0}

    pre_kp1 = float(sweep7["pre_kp1_delta"])
    post_kp1 = float(sweep7["post_kp1_delta"])
    s6 = plate_trace.get("sweep6_dlaqr5_entry", {})
    s6_kp1 = float(s6["kp1_delta"]) if int(s6.get("hit", 0)) == 1 else None

    pre_eq_s6 = False
    if int(s6.get("hit", 0)) == 1:
        pre_eq_s6 = (
            float(sweep7["pre_z13_k"]) == float(s6["z13_k"])
            and float(sweep7["pre_z44_k"]) == float(s6["z44_k"])
            and float(sweep7["pre_z13_kp1"]) == float(s6["z13_kp1"])
            and float(sweep7["pre_z44_kp1"]) == float(s6["z44_kp1"])
        )

    post_eq_s8 = False
    s8_kp1: float | None = None
    if int(qr5_in_plate.get("hit", 0)) == 1:
        s8_kp1 = float(qr5_in_plate["z13_kp1"]) - float(qr5_in_plate["z44_kp1"])
        post_eq_s8 = (
            float(sweep7["post_z13_k"]) == float(qr5_in_plate["z13_k"])
            and float(sweep7["post_z44_k"]) == float(qr5_in_plate["z44_k"])
            and float(sweep7["post_z13_kp1"]) == float(qr5_in_plate["z13_kp1"])
            and float(sweep7["post_z44_kp1"]) == float(qr5_in_plate["z44_kp1"])
        )

    pre_plate_unchanged = (
        float(sweep7["pre_z13_k"]) == float(sweep7["post_z13_k"])
        and float(sweep7["pre_z44_k"]) == float(sweep7["post_z44_k"])
        and float(sweep7["pre_z13_kp1"]) == float(sweep7["post_z13_kp1"])
        and float(sweep7["pre_z44_kp1"]) == float(sweep7["post_z44_kp1"])
    )
    return {
        "hit": 1,
        "it": int(sweep7["it"]),
        "ld": int(sweep7["ld"]),
        "qrsweep_at_pre": int(sweep7["qrsweep_at_pre"]),
        "pre_kp1_delta": pre_kp1,
        "post_kp1_delta": post_kp1,
        "kp1_delta_changed": pre_kp1 != post_kp1,
        "kp1_sign_flipped_in_sweep7": (pre_kp1 * post_kp1) < 0,
        "pre_post_plate_unchanged": pre_plate_unchanged,
        "pre_eq_sweep6_dlaqr5_entry": pre_eq_s6,
        "post_eq_sweep8_qr5_in": post_eq_s8,
        "sweep6_kp1_delta": s6_kp1,
        "sweep8_kp1_delta": s8_kp1,
        "pre_z44_k_zero": float(sweep7["pre_z44_k"]) == 0.0,
    }


def _asymmetry_origin_trace(
    sweep_rows: list[dict[str, Any]],
    plate_trace: dict[str, Any],
    qr5_in_plate: dict[str, float | int],
    *,
    live_signed: dict[str, float] | None,
    vend_raw_signed: dict[str, float] | None,
) -> dict[str, Any]:
    """E2i-n1d — when ULP row asymmetry first appears; live vs vendored plates."""
    first_abs_diff: dict[str, Any] | None = None
    for r in sweep_rows:
        a13 = float(r["abs_13"])
        a44 = float(r["abs_44"])
        if a13 == 0.0 and a44 == 0.0:
            continue
        diff = a13 - a44
        tol = 1e-15 * max(a13, a44, 1.0)
        if abs(diff) > tol:
            first_abs_diff = {
                "sweep": int(r["sweep"]),
                "route_name": r["route_name"],
                "it": int(r["it"]),
                "abs_13": a13,
                "abs_44": a44,
                "diff_13_minus_44": diff,
            }
            break

    plate_slots: list[dict[str, Any]] = []
    first_kp1_slot: dict[str, Any] | None = None
    for key in ("sweep4_dlaqr5_entry", "sweep6_dlaqr5_entry"):
        slot = plate_trace[key]
        if int(slot["hit"]) != 1:
            continue
        plate_slots.append(slot)
        tol = 1e-15 * max(abs(slot["z13_kp1"]), abs(slot["z44_kp1"]), 1.0)
        if abs(float(slot["kp1_delta"])) > tol and first_kp1_slot is None:
            first_kp1_slot = slot

    sweep8_plate: dict[str, Any] | None = None
    if int(qr5_in_plate["hit"]) == 1:
        sweep8_plate = {
            "qrsweep": 7,
            "dlaqr0_sweep": 8,
            "z13_k": float(qr5_in_plate["z13_k"]),
            "z44_k": float(qr5_in_plate["z44_k"]),
            "z13_kp1": float(qr5_in_plate["z13_kp1"]),
            "z44_kp1": float(qr5_in_plate["z44_kp1"]),
            "k_delta": float(qr5_in_plate["z13_k"]) - float(qr5_in_plate["z44_k"]),
            "kp1_delta": float(qr5_in_plate["z13_kp1"])
            - float(qr5_in_plate["z44_kp1"]),
        }
        if first_kp1_slot is None and abs(sweep8_plate["kp1_delta"]) > 1e-300:
            first_kp1_slot = sweep8_plate

    slot_equal_6_8 = None
    s6 = plate_trace.get("sweep6_dlaqr5_entry")
    if (
        int(s6.get("hit", 0)) == 1
        and sweep8_plate is not None
        and float(s6["z13_k"]) == float(sweep8_plate["z13_k"])
        and float(s6["z44_k"]) == float(sweep8_plate["z44_k"])
        and float(s6["z13_kp1"]) == float(sweep8_plate["z13_kp1"])
        and float(s6["z44_kp1"]) == float(sweep8_plate["z44_kp1"])
    ):
        slot_equal_6_8 = True

    live_vs_vend: dict[str, Any] | None = None
    if live_signed and sweep8_plate is not None:
        vend_k = sweep8_plate["k_delta"]
        live_k = float(live_signed["k_delta"])
        live_vs_vend = {
            "scope_note": (
                "live=final Engine principal column; "
                "vend=Schur VR plate at DLAQR5 sweep-8 entry"
            ),
            "vend_kp1_delta": sweep8_plate["kp1_delta"],
            "vend_k_abs_delta": vend_k,
            "live_k_abs_delta": live_k,
            "k_abs_sign_opposite": (live_k * vend_k) < 0 if vend_k != 0 else None,
            "live_leader_0based": _leader(
                float(live_signed["abs_13"]), float(live_signed["abs_44"])
            ),
            "vend_leader_0based": _leader(
                abs(sweep8_plate["z13_k"]), abs(sweep8_plate["z44_k"])
            ),
        }

    return {
        "first_abs_diff_sweep": first_abs_diff,
        "plate_slots": plate_slots,
        "first_kp1_asymmetry_slot": first_kp1_slot,
        "sweep8_plate": sweep8_plate,
        "sweep6_equals_sweep8_plate": slot_equal_6_8,
        "live_signed_principal": live_signed,
        "vend_raw_signed_principal": vend_raw_signed,
        "live_vs_vend_plate": live_vs_vend,
    }


def _sweep_boundary_analysis(
    sweep_rows: list[dict[str, Any]],
    dbg: dict[str, float | int],
    *,
    live_abs: dict[str, float] | None,
) -> dict[str, Any]:
    """E2i-n0 — sweep 8 commit, frozen tail, sweep 37 endpoint jump."""
    by_sweep = {int(r["sweep"]): r for r in sweep_rows}
    s7 = by_sweep.get(7)
    s8 = by_sweep.get(8)
    s36 = by_sweep.get(36)
    s37 = by_sweep.get(37)
    s38 = by_sweep.get(38)

    def _diff_row(row: dict[str, Any] | None) -> float | None:
        if row is None:
            return None
        return float(row["abs_13"]) - float(row["abs_44"])

    frozen_span: dict[str, Any] | None = None
    if s8 is not None and s36 is not None:
        frozen_span = {
            "from_sweep": 9,
            "through_sweep": 36,
            "abs_13": float(s8["abs_13"]),
            "abs_44": float(s8["abs_44"]),
            "diff_13_minus_44": _diff_row(s8),
            "matches_sweep8": (
                float(s36["abs_13"]) == float(s8["abs_13"])
                and float(s36["abs_44"]) == float(s8["abs_44"])
            ),
        }

    jump37: dict[str, Any] | None = None
    if s36 is not None and s37 is not None:
        d36 = _diff_row(s36)
        d37 = _diff_row(s37)
        jump37 = {
            "from_sweep": 36,
            "to_sweep": 37,
            "route": s37["route_name"],
            "it": int(s37["it"]),
            "pre_abs_13": float(s36["abs_13"]),
            "pre_abs_44": float(s36["abs_44"]),
            "post_abs_13": float(s37["abs_13"]),
            "post_abs_44": float(s37["abs_44"]),
            "delta_13": float(s37["abs_13"]) - float(s36["abs_13"]),
            "delta_44": float(s37["abs_44"]) - float(s36["abs_44"]),
            "pre_diff_13_minus_44": d36,
            "post_diff_13_minus_44": d37,
            "leader_preserved": _leader(
                float(s37["abs_13"]), float(s37["abs_44"])
            )
            == _leader(float(s36["abs_13"]), float(s36["abs_44"])),
        }

    intra8 = {
        "qr5_in_abs_13": float(dbg["qr5_in_abs_13"]),
        "qr5_in_abs_44": float(dbg["qr5_in_abs_44"]),
        "strict_post_M5_abs_13": float(dbg["qr5_z140_strict_abs_13"]),
        "strict_post_M5_abs_44": float(dbg["qr5_z140_strict_abs_44"]),
        "qr5_out_abs_13": float(dbg["qr5_out_abs_13"]),
        "qr5_out_abs_44": float(dbg["qr5_out_abs_44"]),
        "sweep8_post_abs_13": float(s8["abs_13"]) if s8 else None,
        "sweep8_post_abs_44": float(s8["abs_44"]) if s8 else None,
    }
    if s7 is not None and s8 is not None:
        intra8["sweep7_to_8_delta_13"] = float(s8["abs_13"]) - float(s7["abs_13"])
        intra8["sweep7_to_8_delta_44"] = float(s8["abs_44"]) - float(s7["abs_44"])
        intra8["sweep7_to_8_diff_open"] = _diff_row(s8)
        intra8["sweep7_pre_diff"] = _diff_row(s7)

    live_endpoint: dict[str, Any] | None = None
    if live_abs and s38 is not None:
        live_13 = float(live_abs["13"])
        live_44 = float(live_abs["44"])
        vend_13 = float(s38["abs_13"])
        vend_44 = float(s38["abs_44"])
        live_endpoint = {
            "live_diff_13_minus_44": live_13 - live_44,
            "vend_diff_13_minus_44": vend_13 - vend_44,
            "live_minus_vend_13": live_13 - vend_13,
            "live_minus_vend_44": live_44 - vend_44,
            "sign_opposite": (live_13 - live_44) * (vend_13 - vend_44) < 0,
        }

    return {
        "sweep7_pre8": s7,
        "sweep8_commit": s8,
        "frozen_span": frozen_span,
        "sweep37_jump": jump37,
        "sweep38_endpoint": s38,
        "intra_sweep8_dlaqr5": intra8,
        "live_endpoint_delta": live_endpoint,
    }


def _stage(abs_13: float, abs_44: float) -> dict[str, Any]:
    return {
        "abs_13": abs_13,
        "abs_44": abs_44,
        "leader_0based": _leader(abs_13, abs_44),
    }


def _strict_leader(abs_13: float, abs_44: float, *, rtol: float = 1e-15) -> int | None:
    tol = max(1e-300, rtol * max(abs_13, abs_44, 1.0))
    if abs(abs_13 - abs_44) <= tol:
        return None
    return 13 if abs_13 > abs_44 else 44


def _first_flip_site(
    ladder: list[tuple[str, dict[str, Any]]], live_leader: int | None
) -> str:
    first_strict: str | None = None
    for name, st in ladder:
        strict = _strict_leader(float(st["abs_13"]), float(st["abs_44"]))
        if strict is not None and first_strict is None:
            first_strict = name
    if first_strict in (
        "2b_post_DLAQR0_out_schur_VR_col",
        "3_post_DHSEQR_schur_VR_col",
    ):
        site = "dlaqr0_schur_vr_accumulation"
    elif first_strict is not None:
        site = first_strict
    else:
        site = "no_strict_ordering_in_vendored_pipeline"
    if live_leader == 44 and site.startswith("dhseqr"):
        return site
    if live_leader is not None and live_leader != 13:
        return f"{site}_vs_live_principal"
    return site


def _dlaqr5_z_right_step(
    z13: tuple[float, float, float],
    z44: tuple[float, float, float],
    *,
    tau: float,
    v2: float,
    v3: float,
    mode: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """One DO-140 Z-right reflection row-pair on cols (K,K+1,K+2)."""
    t1 = tau
    t2 = tau * v2
    t3 = tau * v3

    def _step_row(zk: float, zk1: float, zk2: float) -> tuple[float, float, float]:
        if mode == "fortran":
            refsum = zk + v2 * zk1 + v3 * zk2
            return (zk - refsum * t1, zk1 - refsum * t2, zk2 - refsum * t3)
        if mode == "fma_v2_first":
            refsum = (v2 * zk1) + zk + v3 * zk2
            return (zk - refsum * t1, zk1 - refsum * t2, zk2 - refsum * t3)
        if mode == "fma_v3_first":
            refsum = v3 * zk2 + zk + v2 * zk1
            return (zk - refsum * t1, zk1 - refsum * t2, zk2 - refsum * t3)
        if mode == "kahan":
            s, c = zk, 0.0
            for term in (v2 * zk1, v3 * zk2):
                y = term - c
                t = s + y
                c = (t - s) - y
                s = t
            refsum = s
            return (zk - refsum * t1, zk1 - refsum * t2, zk2 - refsum * t3)
        if mode == "z_last":
            refsum = v2 * zk1 + v3 * zk2 + zk
            return (zk - refsum * t1, zk1 - refsum * t2, zk2 - refsum * t3)
        raise ValueError(mode)

    r13 = _step_row(*z13)
    r44 = _step_row(*z44)
    return r13, r44


def _m5_replay(dbg: dict[str, float | int], *, ki_0based: int) -> dict[str, Any]:
    tau = float(dbg["qr5_m5_v1"])
    v2 = float(dbg["qr5_m5_v2"])
    v3 = float(dbg["qr5_m5_v3"])
    k_fortran = int(dbg["qr5_m5_k"])
    k0 = k_fortran - 1
    z13 = (
        float(dbg["qr5_m5_z13k"]),
        float(dbg["qr5_m5_z13k1"]),
        float(dbg["qr5_m5_z13k2"]),
    )
    z44 = (
        float(dbg["qr5_m5_z44k"]),
        float(dbg["qr5_m5_z44k1"]),
        float(dbg["qr5_m5_z44k2"]),
    )
    modes = ("fortran", "fma_v2_first", "fma_v3_first", "z_last", "kahan")
    out: dict[str, Any] = {
        "k_fortran": k_fortran,
        "k_0based": k0,
        "ki_0based": ki_0based,
        "ki_in_block": k0 <= ki_0based <= k0 + 2,
        "tau": tau,
        "v2": v2,
        "v3": v3,
        "vendored_strict_abs_13": float(dbg["qr5_z140_strict_abs_13"]),
        "vendored_strict_abs_44": float(dbg["qr5_z140_strict_abs_44"]),
        "modes": {},
    }
    for mode in modes:
        r13, r44 = _dlaqr5_z_right_step(z13, z44, tau=tau, v2=v2, v3=v3, mode=mode)
        if k0 <= ki_0based <= k0 + 2:
            idx = ki_0based - k0
            abs_13 = abs(r13[idx])
            abs_44 = abs(r44[idx])
        else:
            abs_13 = float(dbg["qr5_m5_pre13"])
            abs_44 = float(dbg["qr5_m5_pre44"])
        out["modes"][mode] = {
            "abs_13": abs_13,
            "abs_44": abs_44,
            "leader_0based": _leader(abs_13, abs_44),
            "matches_vendored_strict": (
                abs(abs_13 - float(dbg["qr5_z140_strict_abs_13"])) <= 1e-15
                and abs(abs_44 - float(dbg["qr5_z140_strict_abs_44"])) <= 1e-15
            ),
        }
    return out


def _replay_leader_with_z44k_perturb(
    dbg: dict[str, float | int],
    *,
    ki_0based: int,
    z44k_delta: float,
    mode: str = "fortran",
) -> dict[str, Any]:
    """Replay strict M=5 with optional perturbation on ``Z(44,K)`` before DO-140."""
    tau = float(dbg["qr5_m5_v1"])
    v2 = float(dbg["qr5_m5_v2"])
    v3 = float(dbg["qr5_m5_v3"])
    k_fortran = int(dbg["qr5_m5_k"])
    k0 = k_fortran - 1
    z13 = (
        float(dbg["qr5_m5_z13k"]),
        float(dbg["qr5_m5_z13k1"]),
        float(dbg["qr5_m5_z13k2"]),
    )
    z44 = (
        float(dbg["qr5_m5_z44k"]) + z44k_delta,
        float(dbg["qr5_m5_z44k1"]),
        float(dbg["qr5_m5_z44k2"]),
    )
    r13, r44 = _dlaqr5_z_right_step(z13, z44, tau=tau, v2=v2, v3=v3, mode=mode)
    if k0 <= ki_0based <= k0 + 2:
        idx = ki_0based - k0
        abs_13 = abs(r13[idx])
        abs_44 = abs(r44[idx])
    else:
        abs_13 = float(dbg["qr5_m5_pre13"])
        abs_44 = float(dbg["qr5_m5_pre44"])
    return {
        "abs_13": abs_13,
        "abs_44": abs_44,
        "leader_0based": _leader(abs_13, abs_44),
        "diff_13_minus_44": abs_13 - abs_44,
    }


def _k_row_ulps_tied(z13_k: float, z44_k: float) -> bool:
    return abs(z13_k - z44_k) <= 1e-15 * max(abs(z13_k), abs(z44_k), 1.0)


def _plate_k_row_summary(
    name: str,
    *,
    z13_k: float,
    z44_k: float,
    z13_kp1: float,
    z44_kp1: float,
) -> dict[str, Any]:
    k_delta = z13_k - z44_k
    kp1_delta = z13_kp1 - z44_kp1
    return {
        "stage": name,
        "z13_k": z13_k,
        "z44_k": z44_k,
        "z13_kp1": z13_kp1,
        "z44_kp1": z44_kp1,
        "k_delta": k_delta,
        "kp1_delta": kp1_delta,
        "k_tied": _k_row_ulps_tied(z13_k, z44_k),
        "k_asymmetric": z44_k == 0.0,
        "kp1_asymmetric": z13_kp1 == 0.0 or z44_kp1 == 0.0,
    }


def _s8_entry_restoration_trace(
    sweep7: dict[str, float | int],
    s8_pre: dict[str, float | int],
    qr5_in: dict[str, float | int],
) -> dict[str, Any]:
    """E2i-n2b-b -- triangulate s7_post vs dlaqr0 pre-DLAQR5 vs qr5_in."""
    if int(s8_pre.get("hit", 0)) != 1:
        return {"hit": 0}

    s7_post = None
    if int(sweep7.get("hit", 0)) == 1:
        s7_post = _plate_k_row_summary(
            "s7_post_dlaqr3",
            z13_k=float(sweep7["post_z13_k"]),
            z44_k=float(sweep7["post_z44_k"]),
            z13_kp1=float(sweep7["post_z13_kp1"]),
            z44_kp1=float(sweep7["post_z44_kp1"]),
        )
    pre = _plate_k_row_summary(
        "s8_pre_dlaqr5",
        z13_k=float(s8_pre["z13_k"]),
        z44_k=float(s8_pre["z44_k"]),
        z13_kp1=float(s8_pre["z13_kp1"]),
        z44_kp1=float(s8_pre["z44_kp1"]),
    )
    qr5 = None
    if int(qr5_in.get("hit", 0)) == 1:
        qr5 = _plate_k_row_summary(
            "s8_qr5_in",
            z13_k=float(qr5_in["z13_k"]),
            z44_k=float(qr5_in["z44_k"]),
            z13_kp1=float(qr5_in["z13_kp1"]),
            z44_kp1=float(qr5_in["z44_kp1"]),
        )

    s7_eq_pre = s7_post is not None and (
        s7_post["z13_k"] == pre["z13_k"]
        and s7_post["z44_k"] == pre["z44_k"]
        and s7_post["z13_kp1"] == pre["z13_kp1"]
        and s7_post["z44_kp1"] == pre["z44_kp1"]
    )
    pre_eq_qr5 = qr5 is not None and (
        pre["z13_k"] == qr5["z13_k"]
        and pre["z44_k"] == qr5["z44_k"]
        and pre["z13_kp1"] == qr5["z13_kp1"]
        and pre["z44_kp1"] == qr5["z44_kp1"]
    )
    s7_eq_qr5 = (
        s7_post is not None
        and qr5 is not None
        and s7_post["z13_k"] == qr5["z13_k"]
        and s7_post["z44_k"] == qr5["z44_k"]
        and s7_post["z13_kp1"] == qr5["z13_kp1"]
        and s7_post["z44_kp1"] == qr5["z44_kp1"]
    )

    restoration_kind: str
    if s7_eq_pre and pre_eq_qr5:
        restoration_kind = "no_signed_change_s7_to_qr5_in"
    elif s7_eq_pre and not pre_eq_qr5:
        restoration_kind = "k_restored_dlaqr5_entry_only"
    elif (not s7_eq_pre) and pre_eq_qr5:
        restoration_kind = "k_restored_dlaqr0_gap_before_pre_latch"
    elif s7_eq_qr5:
        restoration_kind = "s7_post_stale_pre_latch_differs"
    else:
        restoration_kind = "multi_step_restoration"

    return {
        "hit": 1,
        "it": int(s8_pre["it"]),
        "qrsweep_at_pre": int(s8_pre["qrsweep_at_pre"]),
        "s7_post": s7_post,
        "s8_pre_dlaqr5": pre,
        "s8_qr5_in": qr5,
        "s7_post_eq_s8_pre": s7_eq_pre,
        "s8_pre_eq_qr5_in": pre_eq_qr5,
        "s7_post_eq_qr5_in": s7_eq_qr5,
        "restoration_kind": restoration_kind,
        "note": (
            "Pinpoints whether K-row symmetry restoration happens in "
            "dlaqr0 gap (shift setup) or only inside DLAQR5 entry."
        ),
    }


def _sweep68_z_plate_bridge(
    qr0_post: dict[str, float | int],
    sweep7: dict[str, float | int],
    qr5_in: dict[str, float | int],
    dbg: dict[str, float | int],
    *,
    sweep8_m5_oracle: dict[str, Any],
    s8_pre: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    """E2i-n2b-a — signed K-row plate bridge sweep-6 exit → sweep-7 → sweep-8 entry → m5pre."""
    stages: list[dict[str, Any]] = []
    if int(qr0_post.get("hit", 0)) == 1:
        stages.append(
            _plate_k_row_summary(
                "s6_post_dlaqr5",
                z13_k=float(qr0_post["z13_k"]),
                z44_k=float(qr0_post["z44_k"]),
                z13_kp1=float(qr0_post["z13_kp1"]),
                z44_kp1=float(qr0_post["z44_kp1"]),
            )
        )
    if int(sweep7.get("hit", 0)) == 1:
        stages.append(
            _plate_k_row_summary(
                "s7_pre_dlaqr3",
                z13_k=float(sweep7["pre_z13_k"]),
                z44_k=float(sweep7["pre_z44_k"]),
                z13_kp1=float(sweep7["pre_z13_kp1"]),
                z44_kp1=float(sweep7["pre_z44_kp1"]),
            )
        )
        stages.append(
            _plate_k_row_summary(
                "s7_post_dlaqr3",
                z13_k=float(sweep7["post_z13_k"]),
                z44_k=float(sweep7["post_z44_k"]),
                z13_kp1=float(sweep7["post_z13_kp1"]),
                z44_kp1=float(sweep7["post_z44_kp1"]),
            )
        )
    if s8_pre is not None and int(s8_pre.get("hit", 0)) == 1:
        stages.append(
            _plate_k_row_summary(
                "s8_pre_dlaqr5",
                z13_k=float(s8_pre["z13_k"]),
                z44_k=float(s8_pre["z44_k"]),
                z13_kp1=float(s8_pre["z13_kp1"]),
                z44_kp1=float(s8_pre["z44_kp1"]),
            )
        )
    if int(qr5_in.get("hit", 0)) == 1:
        stages.append(
            _plate_k_row_summary(
                "s8_qr5_in",
                z13_k=float(qr5_in["z13_k"]),
                z44_k=float(qr5_in["z44_k"]),
                z13_kp1=float(qr5_in["z13_kp1"]),
                z44_kp1=float(qr5_in["z44_kp1"]),
            )
        )
    if int(dbg.get("qr5_m5_hit", 0)) == 1:
        stages.append(
            _plate_k_row_summary(
                "s8_m5pre",
                z13_k=float(dbg["qr5_m5_z13k"]),
                z44_k=float(dbg["qr5_m5_z44k"]),
                z13_kp1=float(dbg["qr5_m5_z13k1"]),
                z44_kp1=float(dbg["qr5_m5_z44k1"]),
            )
        )

    if not stages:
        return {"hit": 0}

    transitions: list[dict[str, Any]] = []
    for left, right in zip(stages, stages[1:]):
        transitions.append(
            {
                "from": left["stage"],
                "to": right["stage"],
                "k_delta_unchanged": left["k_delta"] == right["k_delta"],
                "k_tied_both": left["k_tied"] and right["k_tied"],
                "k_asym_to_tied": left["k_asymmetric"] and right["k_tied"],
                "k_tied_to_asym": left["k_tied"] and right["k_asymmetric"],
            }
        )

    first_k_asym = next((s for s in stages if s["k_asymmetric"]), None)
    first_k_tied_after_asym: str | None = None
    if first_k_asym is not None:
        idx = stages.index(first_k_asym)
        for s in stages[idx + 1 :]:
            if s["k_tied"] and not s["k_asymmetric"]:
                first_k_tied_after_asym = s["stage"]
                break

    m5pre = stages[-1] if stages[-1]["stage"] == "s8_m5pre" else None
    flip_delta = sweep8_m5_oracle.get("min_z44k_delta_for_replay_leader_44")
    bias_needed: dict[str, Any] | None = None
    if m5pre is not None and flip_delta is not None:
        # Live kmax=44 needs Z(44,K) bumped by ~flip_delta before DO-140 M=5.
        bias_needed = {
            "current_k_delta": m5pre["k_delta"],
            "min_z44k_delta_for_leader_44": float(flip_delta),
            "z44k_must_exceed_z13k_by": float(flip_delta),
            "m5pre_k_tied": m5pre["k_tied"],
        }

    bridge_kind: str
    if first_k_asym is None:
        bridge_kind = "no_k_asymmetry_in_chain"
    elif first_k_tied_after_asym is None:
        bridge_kind = "k_asymmetry_persists_to_m5pre"
    elif first_k_tied_after_asym in ("s7_post_dlaqr3", "s8_qr5_in"):
        bridge_kind = "k_symmetry_restored_s7_to_s8_entry"
    elif first_k_tied_after_asym == "s7_pre_dlaqr3":
        bridge_kind = "k_symmetry_restored_before_s7_body"
    else:
        bridge_kind = "k_symmetry_restored_other"

    s6_eq_s7_pre = False
    s6_eq_s8_in = False
    if int(qr0_post.get("hit", 0)) == 1 and int(sweep7.get("hit", 0)) == 1:
        s6_eq_s7_pre = _plate_equal(
            qr0_post,
            {
                "z13_k": sweep7["pre_z13_k"],
                "z44_k": sweep7["pre_z44_k"],
                "z13_kp1": sweep7["pre_z13_kp1"],
                "z44_kp1": sweep7["pre_z44_kp1"],
            },
        )
    if int(qr0_post.get("hit", 0)) == 1 and int(qr5_in.get("hit", 0)) == 1:
        s6_eq_s8_in = _plate_equal(qr0_post, qr5_in)

    return {
        "hit": 1,
        "stages": stages,
        "transitions": transitions,
        "first_k_asymmetry_stage": (
            first_k_asym["stage"] if first_k_asym else None
        ),
        "first_k_tied_after_asym_stage": first_k_tied_after_asym,
        "s6_post_eq_s7_pre": s6_eq_s7_pre,
        "s6_post_eq_s8_qr5_in": s6_eq_s8_in,
        "m5pre_bias_needed": bias_needed,
        "bridge_kind": bridge_kind,
        "compute_patch_hint": (
            "preserve_or_restore_s6_k_asymmetry_through_s8_m5pre"
            if first_k_tied_after_asym is not None and m5pre and m5pre["k_tied"]
            else "inspect_k_asymmetry_chain"
        ),
        "note": (
            "K63: live kmax=44 needs sub-ULP Z(44,K) bias at m5pre; "
            "bridge locates where sweep-6 K-asymmetry (z44_k=0) is restored."
        ),
    }


def _sweep8_m5_oracle_gap(
    dbg: dict[str, float | int],
    m5_replay: dict[str, Any],
    boundary: dict[str, Any],
    *,
    ki_0based: int,
    live_kmax: int | None,
    live_abs: dict[str, float] | None,
) -> dict[str, Any]:
    """E2i-n2a — quantify sweep-8 ``M=5`` replay vs live ``kmax`` oracle gap."""
    intra = boundary.get("intra_sweep8_dlaqr5", {})
    strict13 = float(intra.get("strict_post_M5_abs_13", dbg["qr5_z140_strict_abs_13"]))
    strict44 = float(intra.get("strict_post_M5_abs_44", dbg["qr5_z140_strict_abs_44"]))
    strict_pick = _ulp_row_pick(strict13, strict44)
    pre_pick = _ulp_row_pick(float(dbg["qr5_m5_pre13"]), float(dbg["qr5_m5_pre44"]))
    replay_modes = m5_replay.get("modes", {})
    all_replay_leader_13 = all(
        int(st.get("leader_0based", -1)) == 13 for st in replay_modes.values()
    )
    replay_tied_post = all(
        abs(float(st["abs_13"]) - float(st["abs_44"])) <= 1e-15
        * max(abs(float(st["abs_13"])), abs(float(st["abs_44"])), 1.0)
        for st in replay_modes.values()
    )

    flip_delta: float | None = None
    if int(m5_replay.get("ki_in_block", 0)) == 1:
        lo, hi = 0.0, 1.0
        if _replay_leader_with_z44k_perturb(
            dbg, ki_0based=ki_0based, z44k_delta=hi
        )["leader_0based"] != 44:
            hi = 1.0
            for _ in range(48):
                if (
                    _replay_leader_with_z44k_perturb(
                        dbg, ki_0based=ki_0based, z44k_delta=hi
                    )["leader_0based"]
                    == 44
                ):
                    break
                hi *= 2.0
        for _ in range(64):
            mid = 0.5 * (lo + hi)
            if (
                _replay_leader_with_z44k_perturb(
                    dbg, ki_0based=ki_0based, z44k_delta=mid
                )["leader_0based"]
                == 44
            ):
                hi = mid
            else:
                lo = mid
        flip_delta = hi

    live_row_pick = None
    if live_abs:
        live_row_pick = _ulp_row_pick(
            float(live_abs.get("13", 0.0)), float(live_abs.get("44", 0.0))
        )

    oracle_kind: str
    if not all_replay_leader_13:
        oracle_kind = "replay_leader_not_13"
    elif replay_tied_post and live_kmax == 44:
        oracle_kind = "replay_tied_k_plate_live_kmax_44"
    elif strict_pick["leader_0based"] == 13 and live_kmax == 44:
        oracle_kind = "strict_m5_opens_13gt44_live_kmax_44"
    else:
        oracle_kind = "mixed"

    return {
        "dlaqr0_sweep": 8,
        "qrsweep_at_m5": 7,
        "qr_first_strict_step": int(dbg["qr_first_strict_step"]),
        "m5_hit": int(dbg["qr5_m5_hit"]),
        "ki_in_block": bool(m5_replay.get("ki_in_block")),
        "pre_m5_pick": pre_pick,
        "strict_post_m5_pick": strict_pick,
        "replay_all_leader_13": all_replay_leader_13,
        "replay_tied_post_m5": replay_tied_post,
        "live_kmax_0based": live_kmax,
        "live_row13_44_pick": live_row_pick,
        "min_z44k_delta_for_replay_leader_44": flip_delta,
        "oracle_kind": oracle_kind,
        "association_patch_sufficient": False,
        "note": (
            "K49 closed association-only REFSUM reorder; flip_delta is minimum "
            "signed Z(44,K) perturbation before DO-140 to flip replay row leader."
        ),
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[dgeevx ladder] vendored DLL missing", file=sys.stderr)
        return 2

    blocks_path = entry4_eig_oracle_blocks_pkl()
    with blocks_path.open("rb") as f:
        blk = [b for b in pickle.load(f)["blocks"] if b["sub_hash"] == MODE_B_HASH][0]

    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    j_ref = int(dr["jmax"])

    dtrevc3_debug_reset()
    w_probe, _ = eig_real_nobalance(sub)
    raw_j = int(np.argmax(np.abs(np.asarray(w_probe).ravel(order="F"))))
    fortran_col = raw_j + 1
    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    w_v, v_v = eig_real_nobalance(sub)
    dbg = dtrevc3_debug_get()

    w_pp, v_pp = apply_matlab_spectral_postprocess(w_v, v_v)
    dp_raw = rgm_spectral_decisions(sub, w_v, v_v)
    absv_final = np.abs(v_pp[:, j_ref])

    live_kmax = None
    live_abs: dict[str, float] = {}
    live_signed: dict[str, float] | None = None
    try:
        import matlab.engine

        eng = matlab.engine.start_matlab()
        eng.addpath(str(_REPO / "matlab_custom"), nargout=0)
        eng.workspace["rgms_sub"] = __import__("matlab").double(sub.tolist())
        eng.eval("rgms_out = entry4_eig_principal_column_probe(rgms_sub);", nargout=0)
        live_kmax = int(eng.eval("rgms_out.kmax_abs_entry")) - 1
        absv_live = np.asarray(eng.eval("rgms_out.absv"), dtype=np.float64).ravel()
        for i in PLATEAU_IDX:
            live_abs[str(i)] = float(absv_live[i])
        pc_live = np.asarray(eng.eval("rgms_out.principal_col"), dtype=np.float64).ravel()
        z13 = float(pc_live[13])
        z44 = float(pc_live[44])
        live_signed = {
            "z13_k": z13,
            "z44_k": z44,
            "k_delta": z13 - z44,
            "abs_13": float(abs(z13)),
            "abs_44": float(abs(z44)),
        }
        eng.quit()
    except Exception as exc:  # pragma: no cover
        print(f"[dgeevx ladder] Engine skipped: {exc}", file=sys.stderr)

    ladder_ordered: list[tuple[str, dict[str, Any]]] = [
        (
            "1_post_DGEHRD_hessenberg_H_col",
            _stage(dbg["post_dgehrd_hess_col_abs_13"], dbg["post_dgehrd_hess_col_abs_44"]),
        ),
        (
            "2_post_DORGHR_orthogonal_Q_col",
            _stage(dbg["post_dorghr_q_col_abs_13"], dbg["post_dorghr_q_col_abs_44"]),
        ),
        (
            "2a_post_DLAQR0_in_VR_col",
            _stage(dbg["dlaqr0_in_vr_col_abs_13"], dbg["dlaqr0_in_vr_col_abs_44"]),
        ),
        (
            "2b_post_DLAQR0_out_schur_VR_col",
            _stage(dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"]),
        ),
        (
            "3_post_DHSEQR_schur_VR_col",
            _stage(
                dbg["post_dhseqr_schur_vr_col_abs_13"],
                dbg["post_dhseqr_schur_vr_col_abs_44"],
            ),
        ),
        (
            "4_DTREVC3_at_KI_vr_col",
            _stage(dbg["vr_col_k_abs_13"], dbg["vr_col_k_abs_44"]),
        ),
        (
            "5_DTREVC3_post_DGEMM_pre_IDAMAX",
            _stage(dbg["post_bt_pre_idamax_abs_13"], dbg["post_bt_pre_idamax_abs_44"]),
        ),
        (
            "6_final_raw_eig_col",
            _stage(float(np.abs(v_v[13, raw_j])), float(np.abs(v_v[44, raw_j]))),
        ),
    ]

    transitions: list[dict[str, Any]] = []
    for i in range(1, len(ladder_ordered)):
        prev_n, prev_s = ladder_ordered[i - 1]
        cur_n, cur_s = ladder_ordered[i]
        transitions.append(
            {
                "from": prev_n,
                "to": cur_n,
                "delta_13": float(cur_s["abs_13"] - prev_s["abs_13"]),
                "delta_44": float(cur_s["abs_44"] - prev_s["abs_44"]),
                "leader_changed": prev_s["leader_0based"] != cur_s["leader_0based"],
            }
        )

    live_leader = _leader(live_abs.get("13", 0.0), live_abs.get("44", 0.0)) if live_abs else None
    flip_site = _first_flip_site(ladder_ordered, live_leader)
    m5_replay = _m5_replay(dbg, ki_0based=raw_j)

    row: dict[str, Any] = {
        "sub_hash": MODE_B_HASH,
        "n": int(sub.shape[0]),
        "raw_jmax_0based": raw_j,
        "fortran_dbg_col": fortran_col,
        "ref_jmax_0based": j_ref,
        "dgeevx_order_note": (
            "DGEBAL(N) → DGEHRD → DORGHR(Q in VR) → DHSEQR(Schur VR) → DTREVC3 → Python"
        ),
        "dbg": dbg,
        "ladder_ordered": {name: st for name, st in ladder_ordered},
        "transitions": transitions,
        "final_kmax_raw": int(np.argmax(dp_raw["absv"])),
        "final_kmax_pp": int(np.argmax(absv_final)),
        "live_kmax": live_kmax,
        "live_abs_at_plateau": live_abs,
        "live_plateau_leader_0based": live_leader,
        "flip_site": flip_site,
        "qr_sweep_total": dbg["qr_sweep_total"],
        "qr_first_strict_step": dbg["qr_first_strict_step"],
        "qr_first_strict_route": dbg["qr_first_strict_route_name"],
        "qr_first_strict_it": dbg["qr_first_strict_it"],
        "qr_first_strict_abs_13": dbg["qr_first_strict_abs_13"],
        "qr_first_strict_abs_44": dbg["qr_first_strict_abs_44"],
        "m5_replay": m5_replay,
    }

    sweep_table = dtrevc3_debug_get_qr0_sweep_table()
    row["sweep_table"] = sweep_table
    boundary = _sweep_boundary_analysis(
        sweep_table["rows"], dbg, live_abs=live_abs or None
    )
    row["sweep_boundary"] = boundary
    sweep37 = dtrevc3_debug_get_qr0_sweep37_boundary()
    row["sweep37_instrument"] = sweep37
    sweep7 = dtrevc3_debug_get_qr0_sweep7_boundary()
    row["sweep7_instrument"] = sweep7
    qr5_in_plate = dtrevc3_debug_get_qr5_in_plate()
    row["qr5_in_plate"] = qr5_in_plate
    plate_trace = dtrevc3_debug_get_qr5_plate_trace()
    row["qr5_plate_trace"] = plate_trace
    qr5_out5_plate = dtrevc3_debug_get_qr5_out5_plate()
    row["qr5_out5_plate"] = qr5_out5_plate
    qr0_post_plate = dtrevc3_debug_get_qr0_sweep6_post_dlaqr5()
    row["qr0_sweep6_post_dlaqr5"] = qr0_post_plate
    s8_pre_plate = dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5()
    row["qr0_sweep8_pre_dlaqr5"] = s8_pre_plate
    vend_raw_signed = {
        "z13_k": float(v_v[13, raw_j]),
        "z44_k": float(v_v[44, raw_j]),
        "k_delta": float(v_v[13, raw_j]) - float(v_v[44, raw_j]),
        "abs_13": float(np.abs(v_v[13, raw_j])),
        "abs_44": float(np.abs(v_v[44, raw_j])),
    }
    asymmetry_trace = _asymmetry_origin_trace(
        sweep_table["rows"],
        plate_trace,
        qr5_in_plate,
        live_signed=live_signed,
        vend_raw_signed=vend_raw_signed,
    )
    row["asymmetry_origin_trace"] = asymmetry_trace
    sweep7_flip = _sweep7_flip_trace(sweep7, plate_trace, qr5_in_plate)
    row["sweep7_flip_trace"] = sweep7_flip
    sweep6_body = _sweep6_body_trace(qr5_out5_plate, plate_trace, sweep7)
    row["sweep6_body_trace"] = sweep6_body
    sweep6_gap = _sweep6_gap_trace(qr5_out5_plate, qr0_post_plate, sweep7)
    row["sweep6_gap_trace"] = sweep6_gap
    s5_intra_raw = dtrevc3_debug_get_qr5_s5_intra_trace()
    row["qr5_s5_intra_trace"] = s5_intra_raw
    sweep6_intra = _sweep6_intra_trace(s5_intra_raw, plate_trace, qr0_post_plate)
    row["sweep6_intra_trace"] = sweep6_intra
    s5_zpre_sub_raw = dtrevc3_debug_get_qr5_s5_zpre_subtrace()
    row["qr5_s5_zpre_subtrace"] = s5_zpre_sub_raw
    sweep6_zpre_sub = _sweep6_zpre_sub_trace(s5_zpre_sub_raw, plate_trace)
    row["sweep6_zpre_sub_trace"] = sweep6_zpre_sub
    s5_z1_do140_raw = dtrevc3_debug_get_qr5_s5_z1_do140()
    row["qr5_s5_z1_do140"] = s5_z1_do140_raw
    sweep6_z1_do140 = _sweep6_z1_do140_trace(
        s5_z1_do140_raw, s5_zpre_sub_raw, plate_trace
    )
    row["sweep6_z1_do140_trace"] = sweep6_z1_do140
    s5_z1_gap_raw = dtrevc3_debug_get_qr5_s5_z1_gap()
    row["qr5_s5_z1_gap"] = s5_z1_gap_raw
    sweep6_z1_gap = _sweep6_z1_gap_trace(
        s5_z1_gap_raw, s5_z1_do140_raw, s5_zpre_sub_raw, plate_trace
    )
    row["sweep6_z1_gap_trace"] = sweep6_z1_gap
    s5_z145_raw = dtrevc3_debug_get_qr5_s5_z145_pre_zp1()
    row["qr5_s5_z145_pre_zp1"] = s5_z145_raw
    sweep6_z145 = _sweep6_z145_pre_zp1_trace(
        s5_z145_raw, s5_zpre_sub_raw, plate_trace
    )
    row["sweep6_z145_pre_zp1_trace"] = sweep6_z145
    s5_zp1_bnd_raw = dtrevc3_debug_get_qr5_s5_zp1_boundary()
    row["qr5_s5_zp1_boundary"] = s5_zp1_bnd_raw
    sweep6_zp1_bnd = _sweep6_zp1_boundary_trace(
        s5_zp1_bnd_raw, s5_z145_raw, plate_trace
    )
    row["sweep6_zp1_boundary_trace"] = sweep6_zp1_bnd
    sweep8_m5_oracle = _sweep8_m5_oracle_gap(
        dbg,
        m5_replay,
        boundary,
        ki_0based=raw_j,
        live_kmax=live_kmax,
        live_abs=live_abs or None,
    )
    row["sweep8_m5_oracle_gap"] = sweep8_m5_oracle
    sweep68_bridge = _sweep68_z_plate_bridge(
        qr0_post_plate,
        sweep7,
        qr5_in_plate,
        dbg,
        sweep8_m5_oracle=sweep8_m5_oracle,
        s8_pre=s8_pre_plate,
    )
    row["sweep68_z_plate_bridge"] = sweep68_bridge
    s8_restore = _s8_entry_restoration_trace(sweep7, s8_pre_plate, qr5_in_plate)
    row["s8_entry_restoration_trace"] = s8_restore

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E2i-n2b-b",
        "row": row,
    }
    out = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_eig_dtrevc3_pre_idamax.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[dgeevx ladder] {MODE_B_HASH} col={fortran_col} (raw jmax={raw_j})")
    for name, st in ladder_ordered:
        print(
            f"  {name:36s} leader={st['leader_0based']} "
            f"13={st['abs_13']:.6e} 44={st['abs_44']:.6e}"
        )
    if live_leader is not None:
        print(f"  live_matlab_final_principal       leader={live_leader} kmax={live_kmax}")
    print(f"  flip_site={flip_site}")
    print(
        f"  qr_sweeps={dbg['qr_sweep_total']} "
        f"first_strict_step={dbg['qr_first_strict_step']} "
        f"route={dbg['qr_first_strict_route_name']} "
        f"it={dbg['qr_first_strict_it']}"
    )
    print(
        f"  qr5_kacc22={dbg['qr5_kacc22']} "
        f"in=({dbg['qr5_in_abs_13']:.6e},{dbg['qr5_in_abs_44']:.6e}) "
        f"hpre=({dbg['qr5_hpre_abs_13']:.6e},{dbg['qr5_hpre_abs_44']:.6e}) "
        f"hpost=({dbg['qr5_hpost_abs_13']:.6e},{dbg['qr5_hpost_abs_44']:.6e}) "
        f"zpre=({dbg['qr5_zpre_abs_13']:.6e},{dbg['qr5_zpre_abs_44']:.6e}) "
        f"dir=({dbg['qr5_dir_abs_13']:.6e},{dbg['qr5_dir_abs_44']:.6e}) "
        f"gem=({dbg['qr5_gem_abs_13']:.6e},{dbg['qr5_gem_abs_44']:.6e}) "
        f"out=({dbg['qr5_out_abs_13']:.6e},{dbg['qr5_out_abs_44']:.6e})"
    )
    print(
        f"  z140_iters={dbg['qr5_z140_iters']} "
        f"z140_steps={dbg['qr5_z140_steps']} "
        f"first_m={dbg['qr5_z140_first_m']} "
        f"({dbg['qr5_z140_first_abs_13']:.6e},{dbg['qr5_z140_first_abs_44']:.6e}) "
        f"strict13_m={dbg['qr5_z140_strict_13_m']} "
        f"({dbg['qr5_z140_strict_abs_13']:.6e},{dbg['qr5_z140_strict_abs_44']:.6e}) "
        f"last_m={dbg['qr5_z140_last_m']} "
        f"({dbg['qr5_z140_last_abs_13']:.6e},{dbg['qr5_z140_last_abs_44']:.6e})"
    )
    print(
        f"  m5_hit={dbg['qr5_m5_hit']} k={dbg['qr5_m5_k']} "
        f"v=({dbg['qr5_m5_v1']:.6e},{dbg['qr5_m5_v2']:.6e},{dbg['qr5_m5_v3']:.6e}) "
        f"pre=({dbg['qr5_m5_pre13']:.6e},{dbg['qr5_m5_pre44']:.6e}) "
        f"ki_in_block={m5_replay['ki_in_block']}"
    )
    for mode, st in m5_replay["modes"].items():
        mark = "MATCH" if st["matches_vendored_strict"] else "diff"
        print(
            f"  replay_{mode:12s} leader={st['leader_0based']} "
            f"13={st['abs_13']:.6e} 44={st['abs_44']:.6e} [{mark}]"
        )
    chain_eq_m5 = (
        abs(dbg["qr5_chain_zpre13"] - dbg["qr5_m5_pre13"]) < 1e-12
        and abs(dbg["qr5_chain_zpre44"] - dbg["qr5_m5_pre44"]) < 1e-12
    )
    print(
        "  order_of_ops "
        f"(dlaqr5.f: stage5_zpre->145ctx->DO140_M5..1->stage2_dir): "
        f"iters={dbg['qr5_z140_iters']} "
        f"strict_145={dbg['qr5_strict_145']} "
        f"chain_145={dbg['qr5_chain_145']}"
    )
    print(
        f"    qr5_in=({dbg['qr5_in_abs_13']:.6e},{dbg['qr5_in_abs_44']:.6e}) "
        f"chain_zpre=({dbg['qr5_chain_zpre13']:.6e},{dbg['qr5_chain_zpre44']:.6e}) "
        f"m5pre=({dbg['qr5_m5_pre13']:.6e},{dbg['qr5_m5_pre44']:.6e}) "
        f"last_zpre=({dbg['qr5_zpre_abs_13']:.6e},{dbg['qr5_zpre_abs_44']:.6e}) "
        f"dir=({dbg['qr5_dir_abs_13']:.6e},{dbg['qr5_dir_abs_44']:.6e}) "
        f"chain_eq_m5={chain_eq_m5}"
    )
    print(
        f"    145ctx@strict window mbot={dbg['qr5_chain_mbot']} "
        f"mtop={dbg['qr5_chain_mtop']} krcol={dbg['qr5_chain_krcol']} "
        f"first_m={dbg['qr5_chain_firstm']}"
    )
    chain_eq_strict = (
        abs(dbg["qr5_chain_dir13"] - dbg["qr5_z140_strict_abs_13"]) < 1e-12
        and abs(dbg["qr5_chain_dir44"] - dbg["qr5_z140_strict_abs_44"]) < 1e-12
    )
    live_13 = live_abs.get("13")
    live_44 = live_abs.get("44")
    print(
        "  chain_cumulative "
        f"(strict iter only: DO140 M={dbg['qr5_chain_mbot']}..{dbg['qr5_chain_mtop']} "
        f"then stage2_dir; tail iters -> last_m={dbg['qr5_z140_last_m']}):"
    )
    chain_steps = [
        ("chain_zpre", dbg["qr5_chain_zpre13"], dbg["qr5_chain_zpre44"]),
        ("m5pre", dbg["qr5_m5_pre13"], dbg["qr5_m5_pre44"]),
        ("strict_post_M5", dbg["qr5_z140_strict_abs_13"], dbg["qr5_z140_strict_abs_44"]),
        ("chain_dir@strict145", dbg["qr5_chain_dir13"], dbg["qr5_chain_dir44"]),
        ("last_dir", dbg["qr5_dir_abs_13"], dbg["qr5_dir_abs_44"]),
        ("qr5_out", dbg["qr5_out_abs_13"], dbg["qr5_out_abs_44"]),
        ("dlaqr0_out", dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"]),
    ]
    for name, a13, a44 in chain_steps:
        print(
            f"    {name:22s} leader={_leader(a13, a44)} "
            f"13={a13:.6e} 44={a44:.6e}"
        )
    print(f"    chain_dir_eq_strict_post_M5={chain_eq_strict}")
    if live_13 is not None and live_44 is not None:
        print(
            f"    live_matlab_final     leader={_leader(live_13, live_44)} "
            f"13={live_13:.6e} 44={live_44:.6e}"
        )
    last_m1_eq_dir = (
        abs(dbg["qr5_z140_last_abs_13"] - dbg["qr5_dir_abs_13"]) < 1e-12
        and abs(dbg["qr5_z140_last_abs_44"] - dbg["qr5_dir_abs_44"]) < 1e-12
    )
    print(
        "  tail_drift "
        f"(DO140 M=1 pass index within DLAQR5 call; strict_145={dbg['qr5_strict_145']}): "
        f"first_m1_145={dbg['qr5_first_m1_145']} "
        f"tail_first_m1_145={dbg['qr5_tail_first_m1_145']} "
        f"last_m1_145={dbg['qr5_last_m1_145']} "
        f"of z140_iters={dbg['qr5_z140_iters']}"
    )
    print(
        f"    chain_dir->last_dir delta13="
        f"{dbg['qr5_dir_abs_13'] - dbg['qr5_chain_dir13']:.6e} "
        f"delta44={dbg['qr5_dir_abs_44'] - dbg['qr5_chain_dir44']:.6e} "
        f"last_m1_post_eq_last_dir={last_m1_eq_dir}"
    )
    ulp_rows = {
        "dlaqr0_out_vendored": _ulp_row_pick(
            dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"]
        ),
        "final_raw_vendored": _ulp_row_pick(
            float(np.abs(v_v[13, raw_j])), float(np.abs(v_v[44, raw_j]))
        ),
    }
    if live_13 is not None and live_44 is not None:
        ulp_rows["live_matlab_principal"] = _ulp_row_pick(live_13, live_44)
    print("  ulp_argmax (rows 13/44 within plateau; MATLAB max(abs) first-max on tie):")
    for name, row in ulp_rows.items():
        print(
            f"    {name:24s} pick={row['strict_pick']:4s} "
            f"diff13-44={row['diff_13_minus_44']:+.17e} "
            f"13={row['abs_13']:.17e} 44={row['abs_44']:.17e} "
            f"matlab_first_max={row['matlab_max_abs_first']}"
        )
    if live_kmax is not None:
        print(f"    live_matlab_kmax_0based={live_kmax}")
    st_rows = sweep_table["rows"]
    print(
        "  sweep_bisect "
        f"(DLAQR0 per-sweep row 13/44; tol=1e-15*max(|13|,|44|,1)):"
    )
    print(
        f"    recorded={sweep_table['count']} "
        f"first_13gt44={sweep_table['first_13gt44_sweep']} "
        f"last_13gt44={sweep_table['last_13gt44_sweep']} "
        f"first_44gt13={sweep_table['first_44gt13_sweep']} "
        f"last_44gt13={sweep_table['last_44gt13_sweep']}"
    )
    flips: list[dict[str, Any]] = []
    prev_leader: int | None = None
    for r in st_rows:
        leader = r["leader_0based"]
        if leader is not None and prev_leader is not None and leader != prev_leader:
            flips.append(
                {
                    "from_sweep": r["sweep"] - 1,
                    "to_sweep": r["sweep"],
                    "from_leader": prev_leader,
                    "to_leader": leader,
                    "route": r["route_name"],
                    "it": r["it"],
                }
            )
        if leader is not None:
            prev_leader = leader
    if flips:
        print(f"    leader_flips={len(flips)}")
        for f in flips:
            print(
                f"      sweep {f['from_sweep']}->{f['to_sweep']} "
                f"{f['from_leader']}->{f['to_leader']} "
                f"route={f['route']} it={f['it']}"
            )
    else:
        print("    leader_flips=0")
    if st_rows:
        last = st_rows[-1]
        endpoint_pick = _ulp_row_pick(last["abs_13"], last["abs_44"])
        print(
            f"    endpoint_sweep={last['sweep']} "
            f"route={last['route_name']} it={last['it']} "
            f"leader={last['leader_0based']} "
            f"pick={endpoint_pick['strict_pick']}"
        )
        print(
            f"      13={last['abs_13']:.17e} 44={last['abs_44']:.17e} "
            f"diff13-44={endpoint_pick['diff_13_minus_44']:+.17e}"
        )
        out_pick = _ulp_row_pick(
            dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"]
        )
        print(
            f"    endpoint_vs_dlaqr0_out pick_match="
            f"{endpoint_pick['strict_pick'] == out_pick['strict_pick']}"
        )
    show = min(len(st_rows), 12)
    for r in st_rows[:show]:
        ulp = _ulp_row_pick(r["abs_13"], r["abs_44"])
        print(
            f"    sweep {r['sweep']:2d} {r['route_name']:6s} it={r['it']:3d} "
            f"leader={r['leader_0based']} pick={ulp['strict_pick']:4s} "
            f"diff={ulp['diff_13_minus_44']:+.6e}"
        )
    if len(st_rows) > show:
        print(f"    ... ({len(st_rows) - show} more sweeps omitted)")
    bnd = boundary
    print("  sweep8_boundary (E2i-n0 - commit site vs intra-DLAQR5):")
    intra = bnd["intra_sweep8_dlaqr5"]
    d13 = intra.get("sweep7_to_8_delta_13")
    d44 = intra.get("sweep7_to_8_delta_44")
    print(
        "    sweep7_pre "
        f"diff13-44={intra.get('sweep7_pre_diff')} "
        f"delta13={(f'{d13:.6e}' if d13 is not None else 'n/a')} "
        f"delta44={(f'{d44:.6e}' if d44 is not None else 'n/a')} "
        f"sweep8_open={intra.get('sweep7_to_8_diff_open')}"
    )
    print(
        f"    qr5_in=({intra['qr5_in_abs_13']:.6e},{intra['qr5_in_abs_44']:.6e}) "
        f"strict_M5=({intra['strict_post_M5_abs_13']:.6e},"
        f"{intra['strict_post_M5_abs_44']:.6e}) "
        f"qr5_out=({intra['qr5_out_abs_13']:.6e},{intra['qr5_out_abs_44']:.6e}) "
        f"sweep8_post=({intra['sweep8_post_abs_13']:.6e},"
        f"{intra['sweep8_post_abs_44']:.6e})"
    )
    fr = bnd["frozen_span"]
    if fr:
        print(
            f"  frozen_sweeps {fr['from_sweep']}-{fr['through_sweep']}: "
            f"abs unchanged matches_sweep8={fr['matches_sweep8']} "
            f"diff13-44={fr['diff_13_minus_44']:.6e}"
        )
    j37 = bnd["sweep37_jump"]
    if j37:
        print(
            f"  sweep37_jump (DLAQR3 it={j37['it']}): "
            f"pre=({j37['pre_abs_13']:.6e},{j37['pre_abs_44']:.6e}) "
            f"post=({j37['post_abs_13']:.6e},{j37['post_abs_44']:.6e}) "
            f"d13={j37['delta_13']:.6e} d44={j37['delta_44']:.6e} "
            f"leader_preserved={j37['leader_preserved']}"
        )
    led = bnd["live_endpoint_delta"]
    if led:
        print(
            f"  live_vs_vend_endpoint: sign_opposite={led['sign_opposite']} "
            f"live_diff={led['live_diff_13_minus_44']:+.6e} "
            f"vend_diff={led['vend_diff_13_minus_44']:+.6e} "
            f"live-vend_13={led['live_minus_vend_13']:+.6e} "
            f"live-vend_44={led['live_minus_vend_44']:+.6e}"
        )
    s37 = sweep37
    if s37["hit"]:
        pre_pick = _ulp_row_pick(s37["pre_abs_13"], s37["pre_abs_44"])
        post_pick = _ulp_row_pick(s37["post_abs_13"], s37["post_abs_44"])
        ratio13 = (
            s37["post_abs_13"] / s37["pre_abs_13"]
            if s37["pre_abs_13"] != 0.0
            else float("nan")
        )
        ratio44 = (
            s37["post_abs_44"] / s37["pre_abs_44"]
            if s37["pre_abs_44"] != 0.0
            else float("nan")
        )
        print(
            f"  sweep37_instrument (DLAQR3 IT={s37['it']} ld={s37['ld']}): "
            f"pre=({s37['pre_abs_13']:.6e},{s37['pre_abs_44']:.6e}) "
            f"post=({s37['post_abs_13']:.6e},{s37['post_abs_44']:.6e})"
        )
        print(
            f"    pre_pick={pre_pick['strict_pick']} "
            f"post_pick={post_pick['strict_pick']} "
            f"leader_preserved={pre_pick['leader_0based'] == post_pick['leader_0based']} "
            f"ratio13={ratio13:.17f} ratio44={ratio44:.17f} "
            f"ratio_equal={abs(ratio13 - ratio44) < 1e-12}"
        )
    else:
        print("  sweep37_instrument: hit=0 (not armed)")
    s7 = sweep7_flip
    if int(s7.get("hit", 0)) == 1:
        print(
            f"  sweep7_flip_trace (DLAQR3 IT={s7['it']} ld={s7['ld']} "
            f"qrs_pre={s7['qrsweep_at_pre']}):"
        )
        print(
            f"    pre_post_unchanged={s7['pre_post_plate_unchanged']} "
            f"pre_z44_k_zero={s7['pre_z44_k_zero']} "
            f"sign_flipped={s7['kp1_sign_flipped_in_sweep7']}"
        )
        print(
            f"    pre_eq_sweep6_entry={s7['pre_eq_sweep6_dlaqr5_entry']} "
            f"post_eq_sweep8_qr5_in={s7['post_eq_sweep8_qr5_in']} "
            f"s6_kp1={s7['sweep6_kp1_delta']} "
            f"s8_kp1={s7['sweep8_kp1_delta']}"
        )
    else:
        print("  sweep7_flip_trace: hit=0 (not armed)")
    s6b = sweep6_body
    if int(s6b.get("hit", 0)) == 1:
        print(
            f"  sweep6_body_trace (DLAQR5 exit QRSWEEP={s6b['qrsweep']} "
            f"dlaqr0_sweep={s6b['dlaqr0_sweep']}):"
        )
        print(
            f"    entry_eq_exit={s6b['entry_eq_exit']} "
            f"exit_eq_sweep7_pre={s6b['exit_eq_sweep7_pre']} "
            f"rewrite_in_body={s6b['entry_rewrite_in_sweep6_body']} "
            f"z44_k_zero={s6b['z44_k_zero']}"
        )
        print(
            f"    entry_kp1={s6b['entry_kp1_delta']} "
            f"exit_kp1={s6b['exit_kp1_delta']:+.6e} "
            f"s7_pre_kp1={s6b['s7_pre_kp1_delta']}"
        )
        print(
            f"    exit plate z13_k={s6b['z13_k']:.6e} z44_k={s6b['z44_k']:.6e} "
            f"z13_kp1={s6b['z13_kp1']:.6e} z44_kp1={s6b['z44_kp1']:.6e}"
        )
    else:
        print("  sweep6_body_trace: hit=0 (not armed)")
    s6g = sweep6_gap
    if int(s6g.get("hit", 0)) == 1:
        print(
            f"  sweep6_gap_trace (dlaqr0 post-DLAQR5 IT={s6g['it']} "
            f"qrs_post={s6g['qrsweep_at_post']}):"
        )
        print(
            f"    qr5_out_eq_qr0_post={s6g['qr5_out_eq_qr0_post']} "
            f"qr0_post_eq_sweep7_pre={s6g['qr0_post_eq_sweep7_pre']} "
            f"asymmetric_at_qr0_post={s6g['asymmetric_at_qr0_post']} "
            f"gap_site={s6g['gap_site']}"
        )
        qp = s6g["qr0_post"]
        print(
            f"    qr0_post z13_k={qp['z13_k']:.6e} z44_k={qp['z44_k']:.6e} "
            f"z13_kp1={qp['z13_kp1']:.6e} z44_kp1={qp['z44_kp1']:.6e} "
            f"kp1_delta={qp['kp1_delta']:+.6e}"
        )
        print(
            f"    qr5_out_kp1={s6g['qr5_out_kp1_delta']} "
            f"qr0_post_kp1={s6g['qr0_post_kp1_delta']:+.6e} "
            f"s7_pre_kp1={s6g['s7_pre_kp1_delta']}"
        )
    else:
        print("  sweep6_gap_trace: hit=0 (not armed)")
    s6i = sweep6_intra
    if int(s6i.get("hit", 0)) == 1:
        print(
            f"  sweep6_intra_trace (DLAQR5 QRSWEEP={s6i['qrsweep']} "
            f"dlaqr0_sweep={s6i['dlaqr0_sweep']}):"
        )
        print(
            f"    zpre_hit={s6i['zpre_hit']} dir_hit={s6i['dir_hit']} "
            f"gem_hit={s6i['gem_hit']} out_hit={s6i['out_hit']} "
            f"fas_hit={s6i['fas_hit']} fas_stage={s6i['fas_stage']}"
        )
        print(
            f"    kacc22={s6i['kacc22']} zpre_iters={s6i['zpre_iters']} "
            f"z140_steps={s6i['z140_steps']} z140_iters={s6i['z140_iters']}"
        )
        print(
            f"    entry_eq_zpre={s6i['entry_eq_zpre']} "
            f"out_eq_qr0_post={s6i['out_eq_qr0_post']} "
            f"first_asymmetry_site={s6i['first_asymmetry_site']} "
            f"first_asymmetry_stage={s6i['first_asymmetry_stage']}"
        )
        for site in ("entry", "zpre", "dir", "gem", "fas", "out", "qr0_post"):
            st = s6i["stages"].get(site)
            if st is None:
                continue
            p = st["plate"]
            print(
                f"    {site:8s} stage={st['stage_id']:2d} "
                f"asym={st['asymmetric']} "
                f"z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e} "
                f"kp1_delta={p['kp1_delta']:+.6e}"
            )
    else:
        print("  sweep6_intra_trace: hit=0 (not armed)")
    s6z = sweep6_zpre_sub
    if int(s6z.get("hit", 0)) == 1:
        print(
            f"  sweep6_zpre_sub_trace (DLAQR5 QRSWEEP={s6z['qrsweep']} "
            f"dlaqr0_sweep={s6z['dlaqr0_sweep']}):"
        )
        print(
            f"    zpre_iters={s6z['zpre_iters']} zpa_iter={s6z['zpa_iter']} "
            f"rewrite_site={s6z['rewrite_site']}"
        )
        print(
            f"    entry_eq_zp1={s6z['entry_eq_zp1']} "
            f"zp1_eq_zlast={s6z['zp1_eq_zlast']} "
            f"zp1_asym={s6z['zp1_asymmetric']} "
            f"zlast_asym={s6z['zlast_asymmetric']}"
        )
        for site in ("entry", "zp1", "zpa", "zlast"):
            plate = s6z.get(site)
            if plate is None:
                continue
            print(
                f"    {site:5s} asym={_is_asymmetric_plate(plate)} "
                f"z44_k={plate['z44_k']:.6e} z13_kp1={plate['z13_kp1']:.6e} "
                f"kp1_delta={plate['kp1_delta']:+.6e}"
            )
    else:
        print("  sweep6_zpre_sub_trace: hit=0 (not armed)")
    s6d = sweep6_z1_do140
    if int(s6d.get("hit", 0)) == 1:
        print(
            f"  sweep6_z1_do140_trace (DLAQR5 QRSWEEP={s6d['qrsweep']} "
            f"zpre_iter={s6d['zpre_iter']}):"
        )
        print(
            f"    do140_steps={s6d['do140_steps']} "
            f"first_asym_m={s6d['first_asym_m']} "
            f"last_sym_m={s6d['last_sym_m_before_asym']} "
            f"rewrite_m={s6d['rewrite_m']}"
        )
        print(
            f"    entry_eq_m5={s6d['entry_eq_m5']} "
            f"zp1_eq_last_do140_m={s6d['zp1_eq_last_do140_m']}"
        )
        for m in (5, 4, 3, 2, 1):
            st = s6d["m_plates"].get(str(m))
            if st is None:
                continue
            p = st["plate"]
            print(
                f"    M={m} asym={st['asymmetric']} "
                f"z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e} "
                f"kp1_delta={p['kp1_delta']:+.6e}"
            )
    else:
        print("  sweep6_z1_do140_trace: hit=0 (not armed)")
    s6g = sweep6_z1_gap
    if int(s6g.get("hit", 0)) == 1:
        print(
            f"  sweep6_z1_gap_trace (DLAQR5 QRSWEEP={s6g['qrsweep']} "
            f"zpre_iter={s6g['zpre_iter']}):"
        )
        print(
            f"    first_asym_site={s6g['first_asym_site']} "
            f"rewrite_site={s6g['rewrite_site']}"
        )
        print(
            f"    entry_eq_zp1={s6g['entry_eq_zp1']} "
            f"zp1_eq_m5={s6g['zp1_eq_m5']} "
            f"m5_eq_post_do140={s6g['m5_eq_post_do140']} "
            f"post_eq_dir1={s6g['post_eq_dir1']}"
        )
        for st in s6g["stages"]:
            p = st["plate"]
            print(
                f"    {st['name']:16s} asym={st['asymmetric']} "
                f"eq_prev={st['eq_prev']} "
                f"z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e} "
                f"kp1_delta={p['kp1_delta']:+.6e}"
            )
    else:
        print("  sweep6_z1_gap_trace: hit=0 (not armed)")
    s6z145 = sweep6_z145
    if int(s6z145.get("hit", 0)) == 1:
        print(
            f"  sweep6_z145_pre_zp1_trace (DLAQR5 QRSWEEP={s6z145['qrsweep']}):"
        )
        print(
            f"    z41_hit={s6z145['z41_hit']} z41_steps={s6z145['z41_steps']} "
            f"first_asym_site={s6z145['first_asym_site']} "
            f"rewrite_site={s6z145['rewrite_site']}"
        )
        print(
            f"    last_sym_eq_entry={s6z145['last_sym_eq_entry']} "
            f"last_sym_eq_pre_zp1={s6z145['last_sym_eq_pre_zp1']} "
            f"pre_zp1_eq_zp1={s6z145['pre_zp1_eq_zp1']} "
            f"entry_eq_zp1={s6z145['entry_eq_zp1']}"
        )
        zfa = s6z145["z41_first_asym"]
        if int(zfa["hit"]) == 1:
            p = zfa["plate"]
            print(
                f"    z41_first_asym krcol={zfa['krcol']} k={zfa['k']} m={zfa['m']} "
                f"z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e}"
            )
        zls = s6z145["z41_last_sym"]
        if int(zls["hit"]) == 1:
            p = zls["plate"]
            print(
                f"    z41_last_sym asym={_is_asymmetric_plate(p)} "
                f"z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e}"
            )
        pz = s6z145["pre_zp1"]
        if int(pz["hit"]) == 1:
            p = pz["plate"]
            print(
                f"    pre_zp1      krcol={pz['krcol']} "
                f"asym={_is_asymmetric_plate(p)} "
                f"z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e}"
            )
    else:
        print("  sweep6_z145_pre_zp1_trace: hit=0 (not armed)")
    s6zb = sweep6_zp1_bnd
    if int(s6zb.get("hit", 0)) == 1:
        print(
            f"  sweep6_zp1_boundary_trace (DLAQR5 QRSWEEP={s6zb['qrsweep']}):"
        )
        print(
            f"    dbg_col={s6zb['dbg_col']} pre_zp1_col={s6zb['pre_zp1_col']} "
            f"zp1_col={s6zb['zp1_col']} col_match={s6zb['col_match']}"
        )
        print(
            f"    pre_zp1_krcol={s6zb['pre_zp1_krcol']} zp1_krcol={s6zb['zp1_krcol']} "
            f"krcol_match={s6zb['krcol_match']} boundary_kind={s6zb['boundary_kind']}"
        )
        print(
            f"    pend_it={s6zb['pend_it']} scope_it={s6zb['scope_it']} "
            f"s5inl_it={s6zb['s5inl_it']} s5inc_it={s6zb['s5inc_it']} "
            f"zp1_it={s6zb['zp1_it']} sweep6_capture_it={s6zb['sweep6_capture_it']} "
            f"scope_it_stale={s6zb['scope_it_stale_at_getter']} "
            f"capture_it_match={s6zb['capture_it_match']}"
        )
        print(
            f"    pre_eq_s5inl={s6zb['pre_zp1_eq_s5inl']} "
            f"s5inl_eq_s5inc={s6zb['s5inl_eq_s5inc']} "
            f"s5inc_eq_zp1={s6zb['s5inc_eq_zp1']} "
            f"s5inl_eq_zp1={s6zb['s5inl_eq_zp1']} "
            f"pre_eq_zp1={s6zb['pre_zp1_eq_zp1']} "
            f"entry_eq_s5inl={s6zb['entry_eq_s5inl']} "
            f"entry_eq_s5inc={s6zb['entry_eq_s5inc']} "
            f"entry_eq_zp1={s6zb['entry_eq_zp1']}"
        )
        print(
            f"    s6commit_hit={s6zb['s6commit_hit']} slot_eq_commit={s6zb['slot_eq_commit']} "
            f"commit_eq_s5inc={s6zb['commit_eq_s5inc']} alignment_kind={s6zb['alignment_kind']}"
        )
        print(
            f"    asym pre/s5inl/s5inc/zp1={s6zb['pre_zp1_asymmetric']}/"
            f"{s6zb['s5inl_asymmetric']}/{s6zb['s5inc_asymmetric']}/"
            f"{s6zb['zp1_asymmetric']} rewrite_site={s6zb['rewrite_site']}"
        )
        for name in ("pre_zp1", "s5inl", "s5inc", "zp1", "commit_zp1"):
            p = s6zb[name]
            print(
                f"    {name:10s} z44_k={p['z44_k']:.6e} z13_kp1={p['z13_kp1']:.6e} "
                f"z44_kp1={p['z44_kp1']:.6e} kp1_delta={p['kp1_delta']:+.6e}"
            )
    else:
        print("  sweep6_zp1_boundary_trace: hit=0 (not armed)")
    pin = qr5_in_plate
    if int(pin["hit"]) == 1:
        k_tied = abs(pin["z13_k"] - pin["z44_k"]) <= 1e-15 * max(
            abs(pin["z13_k"]), abs(pin["z44_k"]), 1.0
        )
        print(
            "  plate_asymmetry (qr5_in vs m5pre at sweep-8 DLAQR5 entry):"
        )
        print(
            f"    qr5_in row13=({pin['z13_km1']:.6e},{pin['z13_k']:.6e},"
            f"{pin['z13_kp1']:.6e}) "
            f"row44=({pin['z44_km1']:.6e},{pin['z44_k']:.6e},"
            f"{pin['z44_kp1']:.6e})"
        )
        print(
            f"    m5pre row13=({dbg['qr5_m5_z13k']:.6e},"
            f"{dbg['qr5_m5_z13k1']:.6e},{dbg['qr5_m5_z13k2']:.6e}) "
            f"row44=({dbg['qr5_m5_z44k']:.6e},"
            f"{dbg['qr5_m5_z44k1']:.6e},{dbg['qr5_m5_z44k2']:.6e})"
        )
        print(
            f"    qr5_in_k_tied={k_tied} "
            f"kp1_delta={pin['z13_kp1'] - pin['z44_kp1']:+.6e} "
            f"m5_kp1_delta={dbg['qr5_m5_z13k1'] - dbg['qr5_m5_z44k1']:+.6e}"
        )
        print(
            f"    qr5_in_abs_k13={dbg['qr5_in_abs_13']:.6e} "
            f"abs_k44={dbg['qr5_in_abs_44']:.6e} "
            f"sweep7_post13={bnd['sweep7_pre8']['abs_13'] if bnd['sweep7_pre8'] else 'n/a'}"
        )
    else:
        print("  plate_asymmetry: qr5_in plate hit=0 (not armed)")
    atr = asymmetry_trace
    print("  asymmetry_origin_trace (E2i-n1d):")
    fad = atr["first_abs_diff_sweep"]
    if fad:
        print(
            f"    first_abs_diff sweep={fad['sweep']} "
            f"route={fad['route_name']} it={fad['it']} "
            f"diff13-44={fad['diff_13_minus_44']:+.6e}"
        )
    else:
        print("    first_abs_diff: none")
    for slot in atr["plate_slots"]:
        print(
            f"    plate qrsweep={slot['qrsweep']} "
            f"dlaqr0_sweep={slot['dlaqr0_sweep']} "
            f"k_delta={slot['k_delta']:+.6e} "
            f"kp1_delta={slot['kp1_delta']:+.6e}"
        )
    fk = atr["first_kp1_asymmetry_slot"]
    if fk:
        print(
            f"    first_kp1_asymmetry qrsweep={fk.get('qrsweep')} "
            f"sweep={fk.get('dlaqr0_sweep')} "
            f"kp1_delta={fk['kp1_delta']:+.6e}"
        )
    print(
        f"    sweep6_equals_sweep8_plate={atr['sweep6_equals_sweep8_plate']}"
    )
    lvv = atr["live_vs_vend_plate"]
    if lvv:
        print(
            f"    live_vs_vend k_abs_sign_opposite={lvv['k_abs_sign_opposite']} "
            f"live_leader={lvv['live_leader_0based']} "
            f"vend_leader={lvv['vend_leader_0based']} "
            f"live_k_delta={lvv['live_k_abs_delta']:+.6e} "
            f"vend_k_delta={lvv['vend_k_abs_delta']:+.6e}"
        )
    if live_leader is not None:
        print(
            f"  live_matlab_dlaqr0_out_leader={live_leader} "
            f"(final plateau pick; per-sweep live history not captured)"
        )
    s8o = sweep8_m5_oracle
    print("  sweep8_m5_oracle_gap (E2i-n2a — replay vs live kmax target):")
    print(
        f"    oracle_kind={s8o['oracle_kind']} "
        f"replay_all_leader_13={s8o['replay_all_leader_13']} "
        f"replay_tied_post_m5={s8o['replay_tied_post_m5']}"
    )
    sp = s8o["strict_post_m5_pick"]
    print(
        f"    pre_m5 pick={s8o['pre_m5_pick']['strict_pick']} "
        f"strict_post pick={sp['strict_pick']} "
        f"diff13-44={sp['diff_13_minus_44']:+.6e}"
    )
    print(
        f"    live_kmax={s8o['live_kmax_0based']} "
        f"min_z44k_delta_for_replay_leader_44={s8o['min_z44k_delta_for_replay_leader_44']}"
    )
    s68 = sweep68_bridge
    print("  sweep68_z_plate_bridge (E2i-n2b-a -- signed K-row sweep-6->8->m5pre):")
    if int(s68.get("hit", 0)) == 1:
        print(
            f"    bridge_kind={s68['bridge_kind']} "
            f"first_k_asym={s68['first_k_asymmetry_stage']} "
            f"first_k_tied_after_asym={s68['first_k_tied_after_asym_stage']} "
            f"compute_patch_hint={s68['compute_patch_hint']}"
        )
        print(
            f"    s6_post_eq_s7_pre={s68['s6_post_eq_s7_pre']} "
            f"s6_post_eq_s8_qr5_in={s68['s6_post_eq_s8_qr5_in']}"
        )
        for st in s68["stages"]:
            print(
                f"    {st['stage']:18s} k_delta={st['k_delta']:+.6e} "
                f"k_tied={st['k_tied']} k_asym={st['k_asymmetric']} "
                f"kp1_delta={st['kp1_delta']:+.6e}"
            )
        for tr in s68["transitions"]:
            if tr.get("k_asym_to_tied"):
                print(
                    f"    transition {tr['from']}->{tr['to']}: "
                    f"k_asym_to_tied=True"
                )
        bn = s68.get("m5pre_bias_needed")
        if bn:
            print(
                f"    m5pre_bias_needed: k_tied={bn['m5pre_k_tied']} "
                f"min_z44k_delta={bn['min_z44k_delta_for_leader_44']:.6e}"
            )
    else:
        print("    hit=0 (plates not armed)")
    s8r = s8_restore
    print("  s8_entry_restoration_trace (E2i-n2b-b -- s7_post vs pre-DLAQR5 vs qr5_in):")
    if int(s8r.get("hit", 0)) == 1:
        print(
            f"    restoration_kind={s8r['restoration_kind']} "
            f"qrsweep_at_pre={s8r['qrsweep_at_pre']} "
            f"s7_post_eq_s8_pre={s8r['s7_post_eq_s8_pre']} "
            f"s8_pre_eq_qr5_in={s8r['s8_pre_eq_qr5_in']} "
            f"s7_post_eq_qr5_in={s8r['s7_post_eq_qr5_in']}"
        )
        for key in ("s7_post", "s8_pre_dlaqr5", "s8_qr5_in"):
            st = s8r.get(key)
            if st:
                print(
                    f"    {st['stage']:18s} z44_k={st['z44_k']:.6e} "
                    f"k_tied={st['k_tied']} k_asym={st['k_asymmetric']}"
                )
    else:
        print("    hit=0 (s8 pre-DLAQR5 latch not armed)")
    print(f"[dgeevx ladder] wrote={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
