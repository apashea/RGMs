"""W2 Phase 5-S-1 — optim-owned timing, dump, Entry12 probe state."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM.vb_primitives_optim import _vb_as_float64_array

_VB_TIMING_DEPTH = 0
_VB_TIMING_LOOP_12E = 0.0
_VB_TIMING_LOOP_12F = 0.0
_VB_TIMING_BAND_WALL: dict[str, float] = {}

_VB_RAND_REPLAY_ITER: Any = None
_VB_RAND_REPLAY_ORIG_RAND: Any = None
_PROBE_12F_PARENT: dict[str, Any] | None = None
_ENTRY12_PROBE_CHILD_F_NPZ_DONE: bool = False
_INDUCTION_DBG: dict[str, Any] | None = None
def _vb_segment_timing_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_RUN_SEGMENT_TIMING", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _vb_timing_enter() -> None:
    global _VB_TIMING_DEPTH, _VB_TIMING_LOOP_12E, _VB_TIMING_LOOP_12F, _VB_TIMING_BAND_WALL
    _VB_TIMING_DEPTH += 1
    if _VB_TIMING_DEPTH == 1 and _vb_segment_timing_enabled():
        _VB_TIMING_LOOP_12E = 0.0
        _VB_TIMING_LOOP_12F = 0.0
        _VB_TIMING_BAND_WALL.clear()


def _vb_timing_leave() -> None:
    global _VB_TIMING_DEPTH
    try:
        if _VB_TIMING_DEPTH == 1 and _vb_segment_timing_enabled():
            _vb_timing_flush()
    finally:
        _VB_TIMING_DEPTH = max(0, _VB_TIMING_DEPTH - 1)


def _vb_timing_set_band_wall(label: str, wall_s: float) -> None:
    if _VB_TIMING_DEPTH == 1 and _vb_segment_timing_enabled():
        _VB_TIMING_BAND_WALL[label] = float(wall_s)


def _vb_timing_add_12e(dt: float) -> None:
    """Sum child ``spm_MDP_VB_XXX`` wall when the caller is top-level (depth 1)."""
    global _VB_TIMING_LOOP_12E
    if _VB_TIMING_DEPTH == 1 and _vb_segment_timing_enabled():
        _VB_TIMING_LOOP_12E += float(dt)


def _vb_timing_add_12f(dt: float) -> None:
    global _VB_TIMING_LOOP_12F
    if _VB_TIMING_DEPTH == 1 and _vb_segment_timing_enabled():
        _VB_TIMING_LOOP_12F += float(dt)


_VB_MONITOR_REQUESTED = False
_VB_DUMP_SPEC: dict[str, Any] | None = None


def _vb_dump_resolve_spec() -> dict[str, Any]:
    """Entry 12 subentry pickle output dir/tag (aligned with MATLAB capture)."""
    repo = Path(__file__).resolve().parents[3]
    raw_out = str(os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", "")).strip()
    out_dir = Path(raw_out) if raw_out else repo / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"
    tag = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "rgms_canonical")).strip() or "rgms_canonical"
    return {"enabled": True, "out_dir": out_dir, "run_tag": tag}


def _vb_dump_active() -> bool:
    return bool(_VB_DUMP_SPEC and _VB_DUMP_SPEC.get("enabled") and _VB_TIMING_DEPTH == 1)
_ENTRY12_VBX_ACC: dict[str, dict[str, Any]] = {}
_ENTRY12_PHASE_ACC: dict[str, list[dict[str, Any]]] = {}


def _vb_capture_y_probe_active() -> bool:
    """Entry-12 inspection probes: explicit env override, otherwise dump-only."""
    raw = os.getenv("RGMS_ENTRY12_CAPTURE_Y_PROBE")
    if raw is not None and str(raw).strip():
        return str(raw).strip().lower() not in ("0", "false", "no")
    return bool(_VB_DUMP_SPEC and _VB_DUMP_SPEC.get("enabled"))


def _entry12_vec_peak(v: Any) -> tuple[int | None, float | None]:
    if v is None:
        return None, None
    # MATLAB ``entry12_vec_peak_``: ``v = full(double(v(:)))`` then ``max(v)`` (column-major).
    arr = np.asarray(_vb_as_float64_array(v), dtype=np.float64).ravel(order="F")
    if arr.size == 0:
        return None, 0.0
    pk = int(np.argmax(arr)) + 1
    return pk, float(np.max(arr))
def _entry12_record_vbx_probe(
    mi: int,
    t_1b: int,
    Q_upd: list[Any],
    O_row: list[Any],
    P_row: list[Any],
    idm: dict[str, Any],
    F_vbx: float | None = None,
) -> None:
    if not _vb_capture_y_probe_active():
        return
    pr: dict[str, Any] = {"m": mi + 1, "t": int(t_1b)}
    if F_vbx is not None:
        pr["F_vbx"] = float(F_vbx)
    q_peaks: list[int | None] = []
    q_maxs: list[float | None] = []
    q_f: list[Any] = []
    for qv in Q_upd:
        if qv is None:
            q_f.append([])
            q_peaks.append(None)
            q_maxs.append(None)
            continue
        col = _vb_as_float64_array(qv).ravel()
        q_f.append(col.tolist())
        pk, mx = _entry12_vec_peak(col)
        q_peaks.append(pk)
        q_maxs.append(mx)
    pr["Q_f"] = q_f
    pr["Q_f_peak"] = q_peaks
    pr["Q_f_max"] = q_maxs
    o_peaks: list[int | None] = []
    o_maxs: list[float | None] = []
    for og in O_row:
        pk, mx = _entry12_vec_peak(og)
        o_peaks.append(pk)
        o_maxs.append(mx)
    pr["O_peaks"] = o_peaks
    pr["O_max"] = o_maxs
    pr["P_f_t"] = [_vb_as_float64_array(pv).ravel().tolist() for pv in P_row]
    for key in ("fp", "fu", "iH", "iI"):
        if key in idm:
            pr[f"id_{key}"] = np.asarray(idm[key], dtype=np.int64).ravel().tolist()
    _ENTRY12_VBX_ACC[f"m{mi + 1}t{t_1b}"] = pr


def _entry12_attach_vbx_to_model(models: list[dict[str, Any]], mi: int, t_1b: int) -> None:
    if not _vb_capture_y_probe_active():
        return
    key = f"m{mi + 1}t{t_1b}"
    if key in _ENTRY12_VBX_ACC:
        models[mi]["entry12_VBX"] = copy.deepcopy(_ENTRY12_VBX_ACC[key])


def _entry12_q_cells_at_mt(bundle: dict[str, Any], mi: int, t_1b: int) -> list[list[float]]:
    t_idx = int(t_1b) - 1
    out: list[list[float]] = []
    for f_idx in range(len(bundle["Q"][mi])):
        col = _vb_as_float64_array(bundle["Q"][mi][f_idx][t_idx]).ravel()
        out.append(col.tolist())
    return out


def _entry12_p_cells_at_mt(bundle: dict[str, Any], mi: int, t_1b: int) -> list[list[float]]:
    t_idx = int(t_1b) - 1
    out: list[list[float]] = []
    for f_idx in range(len(bundle["P"][mi])):
        col = _vb_as_float64_array(bundle["P"][mi][f_idx][t_idx]).ravel()
        out.append(col.tolist())
    return out


def _entry12_o_peaks_at_mt(bundle: dict[str, Any], mi: int, t_1b: int) -> list[int | None]:
    t_idx = int(t_1b) - 1
    peaks: list[int | None] = []
    for g_idx in range(len(bundle["O"][mi])):
        og = bundle["O"][mi][g_idx][t_idx]
        pk, _ = _entry12_vec_peak(og)
        peaks.append(pk)
    return peaks


def _entry12_a_peaks_for_model(A_list: list[Any], mi: int) -> list[int | None]:
    """Argmax (1-based) per modality on workspace ``A{m,g}`` passed into ``spm_forwards`` / ``spm_VBX``."""
    peaks: list[int | None] = []
    for g_idx in range(len(A_list[mi])):
        pk, _ = _entry12_vec_peak(A_list[mi][g_idx])
        peaks.append(pk)
    return peaks
def _entry12_phase_key(mi: int, t_1b: int) -> str:
    return f"m{mi + 1}t{t_1b}"
def _entry12_record_phase_belief_rows(
    mi: int,
    t_1b: int,
    phase_name: str,
    O: list[Any],
    P: list[Any],
    belief_row: list[Any],
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    """Record a phase when only belief rows (``spm_forwards`` VBX lane) are available."""
    if not _vb_dump_active():
        return
    o_peaks: list[int | None] = []
    for g_idx in range(len(O[mi])):
        pk, _ = _entry12_vec_peak(O[mi][g_idx][t_1b - 1])
        o_peaks.append(pk)
    rec: dict[str, Any] = {
        "phase": str(phase_name),
        "m": mi + 1,
        "t": int(t_1b),
        "Q_f": [_vb_as_float64_array(bv).ravel().tolist() for bv in belief_row],
        "P_f": [
            _vb_as_float64_array(P[mi][f_idx][t_1b - 1]).ravel().tolist()
            for f_idx in range(len(P[mi]))
        ],
        "O_peaks": o_peaks,
    }
    if extra:
        rec.update(extra)
    key = _entry12_phase_key(mi, t_1b)
    _ENTRY12_PHASE_ACC.setdefault(key, []).append(rec)

def _vb_monitoring_active() -> bool:
    return bool(_VB_MONITOR_REQUESTED and _VB_TIMING_DEPTH == 1)


def _vb_monitor_snapshot(*_args: Any, **_kwargs: Any) -> None:
    """Optim lane monitoring stub — full port deferred to 5-R-3."""


def _vb_timing_flush() -> None:
    """One ``total_s=`` line per band (loop bands summed like FSL ENTRY8/9)."""
    for label in ("12A", "12B", "12C", "12F", "12E", "12G", "12H"):
        if label in ("12F", "12E"):
            total = _VB_TIMING_LOOP_12F if label == "12F" else _VB_TIMING_LOOP_12E
        else:
            if label not in _VB_TIMING_BAND_WALL:
                continue
            total = _VB_TIMING_BAND_WALL[label]
        print(
            f"[spm_MDP_VB_XXX_optim {label}] total_s={total:.6f}",
            file=sys.stderr,
            flush=True,
        )


# Dump snap hooks — active only when ``dump_subentries=True`` (Entry 12 oracle, not 3f gate).
def _entry12_snap_12d(*_a: Any, **_k: Any) -> dict[str, Any]:
    return {}


def _entry12_snap_12e(*_a: Any, **_k: Any) -> dict[str, Any]:
    return {}


def _entry12_snap_12f(*_a: Any, **_k: Any) -> dict[str, Any]:
    return {}


def _entry12_assign_t_boundary(*_a: Any, **_k: Any) -> None:
    return None


def _entry12_attach_phase_log_to_snap(*_a: Any, **_k: Any) -> None:
    return None


def _entry12_record_phase(*_a: Any, **_k: Any) -> None:
    if not _vb_dump_active():
        return

