"""
Variational Bayes active inference (`spm_MDP_VB_XXX.m`).

Pass 1 transliteration in progress: MATLAB source of truth is
``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` (staged from SPM).

Visualization: MATLAB calls ``spm_figure`` in some branches — **out of scope** for
this port; do not add ``spm_figure`` (or related UI) in Python.

Local helpers at the end of the MATLAB file (`spm_sample`, `spm_norm`, …) are kept
as private Python functions in this module.
"""

from __future__ import annotations

import copy
import os
import pickle
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from scipy import stats
from scipy.special import digamma

from matlab_compat import full as mfull, matlab_ndims
from python_src.spm_combinations import spm_combinations
from python_src.spm_cross import spm_cross
from python_src.spm_dot import spm_dot
from python_src.spm_Gcdf import spm_Gcdf
from python_src.spm_kron import spm_kron
from python_src.spm_zeros import spm_zeros
from python_src.spm_KL_dir import spm_KL_dir
from python_src.spm_MDP_MI import spm_MDP_MI
from python_src.spm_psi import spm_psi
from python_src.spm_softmax import spm_softmax
from python_src.spm_vec import spm_vec
from python_src.toolbox.DEM.spm_MDP_BMR import spm_MDP_BMR
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_index import spm_index
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size
from python_src.toolbox.DEM.spm_parents import spm_parents
from python_src.toolbox.DEM.spm_VBX import spm_VBX

_VB_TIMING_DEPTH = 0
_VB_TIMING_LOOP_12E = 0.0
_VB_TIMING_LOOP_12F = 0.0
_VB_TIMING_BAND_WALL: dict[str, float] = {}

_VB_RAND_REPLAY_ITER: Any = None
_VB_RAND_REPLAY_ORIG_RAND: Any = None
_PROBE_12F_PARENT: dict[str, Any] | None = None


def _vb_default_matlab_rand_buf_path() -> Path:
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        default_entry12_vb_matlab_rand_buf_mat_path,
    )

    return default_entry12_vb_matlab_rand_buf_mat_path()


def _vb_load_matlab_rand_buf(path: Path | None = None) -> np.ndarray:
    p = path if path is not None else _vb_default_matlab_rand_buf_path()
    if not p.is_file():
        raise FileNotFoundError(
            f"MATLAB VB rand buffer not found: {p}\n"
            "Run Entry 12 MATLAB dump (after entry12_preflight_vb_rand_k.py) to create it."
        )
    from scipy.io import loadmat

    raw = loadmat(str(p))
    if "vb_rand_buf" not in raw:
        keys = sorted(k for k in raw if not k.startswith("__"))
        raise KeyError(f"expected vb_rand_buf in {p}, got keys={keys}")
    return np.asarray(raw["vb_rand_buf"], dtype=np.float64).ravel(order="F")


class _VbMatlabRandReplay:
    """Replay MATLAB ``rand(K,1)`` scalars through ``numpy.random.rand`` for ``_spm_sample``."""

    __slots__ = ("_it", "_orig")

    def __init__(self, buf: np.ndarray) -> None:
        data = np.asarray(buf, dtype=np.float64).ravel(order="F").tolist()
        self._it = iter(data)
        self._orig = np.random.rand

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError(
                "spm_MDP_VB_XXX reuse_matlab_draws: only scalar np.random.rand() is supported"
            )
        try:
            return float(next(self._it))
        except StopIteration as e:
            raise RuntimeError(
                "spm_MDP_VB_XXX reuse_matlab_draws: exhausted MATLAB vb_rand_buf "
                "(Python drew more scalars than MATLAB; refresh K preflight and dump)"
            ) from e

    def __enter__(self) -> _VbMatlabRandReplay:
        global _VB_RAND_REPLAY_ITER, _VB_RAND_REPLAY_ORIG_RAND
        _VB_RAND_REPLAY_ITER = self._it
        _VB_RAND_REPLAY_ORIG_RAND = self._orig
        np.random.rand = self._shim  # type: ignore[method-assign]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        global _VB_RAND_REPLAY_ITER, _VB_RAND_REPLAY_ORIG_RAND
        np.random.rand = self._orig  # type: ignore[method-assign]
        _VB_RAND_REPLAY_ITER = None
        _VB_RAND_REPLAY_ORIG_RAND = None
        if exc_type is not None:
            return
        try:
            next(self._it)
        except StopIteration:
            return
        raise RuntimeError(
            "spm_MDP_VB_XXX reuse_matlab_draws: unused draws remain in vb_rand_buf "
            "(Python drew fewer scalars than MATLAB; K preflight / OPTIONS mismatch)"
        )


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


def _vb_dump_mdp_payload(models: list[dict[str, Any]]) -> Any:
    if len(models) == 1:
        return copy.deepcopy(models[0])
    return copy.deepcopy(models)


def _vb_isfield_mdp_array(models: list[dict[str, Any]], name: str) -> bool:
    """MATLAB ``elseif isfield(MDP,'field')`` on the VB struct array (nonempty & any present)."""
    if not models:
        return False
    return any(name in md for md in models)


def _vb_mdp_factor_field(md: dict[str, Any], name: str, f_idx: int) -> Any:
    """``MDP.(A|B|C|D|E|H){f}`` — list cell or top-level matrix when ``Nf==1``."""
    val = md.get(name)
    if val is None:
        return None
    if isinstance(val, list):
        v = val[f_idx]
        return v[0] if isinstance(v, list) and len(v) == 1 else v
    if f_idx == 0:
        return val
    raise IndexError(f"spm_MDP_VB_XXX: {name}{{f}} requested f={f_idx} but field is not a cell list")


def _vb_as_float64_array(x: Any) -> np.ndarray:
    if sparse.issparse(x):
        return np.asarray(mfull(x), dtype=np.float64)
    return np.asarray(x, dtype=np.float64)


def _vb_dump_save(
    code: str,
    options: dict[str, Any],
    meta_extra: dict[str, Any],
    bundle: dict[str, Any],
) -> None:
    if not _vb_dump_active() or _VB_DUMP_SPEC is None:
        return
    out_dir = Path(_VB_DUMP_SPEC["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = str(_VB_DUMP_SPEC["run_tag"])
    meta: dict[str, Any] = {
        "subentry": code,
        "run_tag": tag,
        "capture_instrument": "spm_MDP_VB_XXX.py",
    }
    meta.update(meta_extra)
    blob = {**bundle, "OPTIONS": copy.deepcopy(options), "meta": meta}
    path = out_dir / f"DEMAtariIII_entry12_{tag}_{code}.pkl"
    with path.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[XXX 12 dump] wrote {path}", file=sys.stderr, flush=True)


_ENTRY12_VBX_ACC: dict[str, dict[str, Any]] = {}
_ENTRY12_PHASE_ACC: dict[str, list[dict[str, Any]]] = {}


def _vb_capture_y_probe_active() -> bool:
    """Fill-time / VBX probes (parent and nested child VB). Default on; set env to 0 to disable."""
    v = str(os.getenv("RGMS_ENTRY12_CAPTURE_Y_PROBE", "1")).strip().lower()
    return v not in ("0", "false", "no")


def _entry12_vec_peak(v: Any) -> tuple[int | None, float | None]:
    if v is None:
        return None, None
    # MATLAB ``entry12_vec_peak_``: ``v = full(double(v(:)))`` then ``max(v)`` (column-major).
    arr = np.asarray(_vb_as_float64_array(v), dtype=np.float64).ravel(order="F")
    if arr.size == 0:
        return None, 0.0
    pk = int(np.argmax(arr)) + 1
    return pk, float(np.max(arr))


def _entry12_peak_Y_ot(ch: dict[str, Any], o_1b: int, t_1b: int) -> int | None:
    yf = ch.get("Y")
    if not isinstance(yf, list) or len(yf) < o_1b:
        return None
    row = yf[o_1b - 1]
    if not isinstance(row, list) or len(row) < t_1b:
        return None
    pk, _ = _entry12_vec_peak(row[t_1b - 1])
    return pk


def _entry12_peak_A_g(ch: dict[str, Any], g_1b: int) -> int | None:
    ag = ch.get("A")
    if not isinstance(ag, list) or len(ag) < g_1b:
        return None
    pk, _ = _entry12_vec_peak(ag[g_1b - 1])
    return pk


def _entry12_peak_X_ft(ch: dict[str, Any], f_1b: int, t_1b: int) -> int | None:
    xf = ch.get("X")
    if not isinstance(xf, list) or len(xf) < f_1b:
        return None
    col = np.asarray(xf[f_1b - 1], dtype=np.float64)
    if col.ndim < 2 or col.shape[1] < t_1b:
        return None
    pk, _ = _entry12_vec_peak(col[:, t_1b - 1])
    return pk


def _entry12_nested_child_from_parent(md: dict[str, Any]) -> dict[str, Any] | None:
    ch = md.get("MDP")
    if isinstance(ch, dict):
        return ch
    if isinstance(ch, list) and ch and isinstance(ch[0], dict):
        return ch[0]
    if isinstance(ch, np.ndarray) and ch.dtype == object and ch.size > 0:
        item = ch.ravel(order="F")[0]
        return item if isinstance(item, dict) else None
    return None


def _entry12_nested_y_summary(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mi, md in enumerate(models):
        ch = _entry12_nested_child_from_parent(md)
        if ch is None:
            continue
        row: dict[str, Any] = {"parent_m": mi + 1, "has_a": "a" in ch}
        if "L" in ch:
            row["L"] = ch["L"]
        row["Y21_peak"] = _entry12_peak_Y_ot(ch, 2, 1)
        row["Y22_peak"] = _entry12_peak_Y_ot(ch, 2, 2)
        row["A2_export_peak"] = _entry12_peak_A_g(ch, 2)
        row["X1_peak"] = _entry12_peak_X_ft(ch, 1, 1)
        yfill = ch.get("entry12_Yfill")
        if isinstance(yfill, list) and len(yfill) >= 2:
            row_g = yfill[1]
            if isinstance(row_g, list) and len(row_g) >= 1:
                row["yfill_g2t1"] = copy.deepcopy(row_g[0])
        if "entry12_VBX" in ch:
            row["entry12_VBX"] = copy.deepcopy(ch["entry12_VBX"])
        rows.append(row)
    return rows


def _entry12_prechild_from_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mi, md in enumerate(models):
        ch = _entry12_nested_child_from_parent(md)
        if ch is None:
            continue
        row: dict[str, Any] = {"parent_m": mi + 1, "A2_peak": _entry12_peak_A_g(ch, 2)}
        bg = ch.get("B")
        if isinstance(bg, list) and len(bg) >= 8:
            pk, mx = _entry12_vec_peak(bg[7])
            row["B8_peak"] = pk
            row["B8_max"] = mx
        rows.append(row)
    return rows


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


def _entry12_record_phase(
    mi: int,
    t_1b: int,
    phase_name: str,
    bundle: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    if not _vb_dump_active():
        return
    rec: dict[str, Any] = {
        "phase": str(phase_name),
        "m": mi + 1,
        "t": int(t_1b),
        "Q_f": _entry12_q_cells_at_mt(bundle, mi, t_1b),
        "P_f": _entry12_p_cells_at_mt(bundle, mi, t_1b),
        "O_peaks": _entry12_o_peaks_at_mt(bundle, mi, t_1b),
    }
    if extra:
        rec.update(extra)
    key = _entry12_phase_key(mi, t_1b)
    _ENTRY12_PHASE_ACC.setdefault(key, []).append(rec)


def _entry12_build_phase_log(t_1b: int, model_indices: list[int]) -> dict[str, Any]:
    logs: list[dict[str, Any]] = []
    for mi in model_indices:
        key = _entry12_phase_key(mi, t_1b)
        logs.append(
            {
                "m": mi + 1,
                "t": int(t_1b),
                "entries": copy.deepcopy(_ENTRY12_PHASE_ACC.get(key, [])),
            }
        )
    return {"t": int(t_1b), "model_logs": logs}


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


def _entry12_probe_y_fill_all(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """Mirror ``entry12_probe_y_fill_all_`` — workspace ``A``/``Q`` at ``OPTIONS.Y`` for every ``(g,t,o)``."""
    if int(options_vb.get("Y", 0)) == 0 or not _vb_capture_y_probe_active():
        return
    from python_src.toolbox.DEM import spm_parents as spm_parents_mod

    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        if ng_m <= 0:
            continue
        md["entry12_Yfill"] = [[[] for _ in range(t_int)] for _ in range(ng_m)]
        has_a = "a" in md
        id_m = bundle["id"][mi]
        qa_mi = bundle.get("qa")
        for g_1b in range(1, ng_m + 1):
            g_idx = g_1b - 1
            Ag = _vb_ag_for_posterior_predictive(md, bundle, mi, g_idx)
            for t_idx in range(t_int):
                Qrow = _vb_q_row_for_parents(bundle["Q"][mi], t_idx)
                j, i_ch = spm_parents_mod.spm_parents(id_m, g_1b, Qrow)
                j_store = _unwrap_id_a_entry(j)
                j_arr = np.atleast_1d(np.asarray(j_store, dtype=np.float64).ravel())
                sites: list[dict[str, Any]] = []
                for o in np.atleast_1d(np.asarray(i_ch, dtype=np.float64).ravel()).tolist():
                    o_int = int(np.round(float(o)))
                    q_list = _vb_q_list_at_mt(bundle["Q"][mi], j, t_idx)
                    pred = _vb_as_float64_array(
                        spm_dot(np.asarray(Ag, dtype=np.float64), q_list)
                    ).ravel().tolist()
                    A_ws = _vb_as_float64_array(bundle["A"][mi][g_idx]).ravel().tolist()
                    ji = int(j_arr[0])
                    Q_ws = _vb_as_float64_array(bundle["Q"][mi][ji - 1][t_idx]).ravel().tolist()
                    y_stored = md["Y"][o_int - 1][t_idx]
                    y_out_vec = _vb_as_float64_array(y_stored).ravel().tolist()
                    Aexp = md.get("A", [])
                    Aexp_col = (
                        _vb_as_float64_array(Aexp[g_idx]).ravel().tolist()
                        if isinstance(Aexp, list) and len(Aexp) > g_idx
                        else []
                    )
                    qa_g: list[float] = []
                    if isinstance(qa_mi, list) and len(qa_mi) > mi and len(qa_mi[mi]) > g_idx:
                        qa_g = _vb_as_float64_array(qa_mi[mi][g_idx]).ravel().tolist()
                    pr: dict[str, Any] = {
                        "m": mi + 1,
                        "g": g_1b,
                        "t": t_idx + 1,
                        "o": o_int,
                        "j": _unwrap_id_a_entry(j),
                        "i": i_ch,
                        "A_ws": A_ws,
                        "Q_ws": Q_ws,
                        "Y_out": y_out_vec,
                        "pred_replay": pred,
                        "has_a": has_a,
                    }
                    if "L" in md:
                        pr["L"] = md["L"]
                    for label, vec in (
                        ("A_ws", A_ws),
                        ("Q_ws", Q_ws),
                        ("Y_out", y_out_vec),
                        ("pred_replay", pred),
                        ("A_export", Aexp_col),
                        ("qa", qa_g),
                    ):
                        pk, mx = _entry12_vec_peak(vec)
                        pr[f"{label}_peak"] = pk
                        pr[f"{label}_max"] = mx
                    sites.append(pr)
                md["entry12_Yfill"][g_idx][t_idx] = sites


def _vb_monitoring_active() -> bool:
    """Top-level VB only (depth 1); survives nested child ``spm_MDP_VB_XXX`` calls."""
    return bool(_VB_MONITOR_REQUESTED and _VB_TIMING_DEPTH == 1)


def _vb_monitor_desc(v: Any) -> str:
    """Concise type/shape text aligned with ``spm_MDP_VB_XXX_monitor_desc_`` (MATLAB)."""
    import numpy as np

    def _size_bracket(shape: tuple[int, ...]) -> str:
        if not shape:
            return ""
        return " ".join(str(int(x)) for x in shape)

    try:
        if isinstance(v, list):
            if not v:
                return "list(len=0)"
            return f"list(len={len(v)},elem={_vb_monitor_desc(v[0])})"
        if isinstance(v, dict):
            return f"struct(len={len(v)})"
        if isinstance(v, np.ndarray):
            sh = tuple(int(x) for x in v.shape)
            if sh == ():
                sh = (1, 1)
            return f"ndarray[{_size_bracket(sh)}]"
        if hasattr(v, "toarray") and callable(getattr(v, "toarray")) and hasattr(v, "shape"):
            sh = tuple(int(x) for x in v.shape)
            return f"sparse[{_size_bracket(sh)}]"
        if isinstance(v, (bool, int, float, str)):
            return type(v).__name__
        return type(v).__name__
    except Exception as exc:
        return f"{type(v).__name__}(desc_error={type(exc).__name__})"


def _vb_monitor_unwrap_mdp(v: Any) -> Any | None:
    import numpy as np

    if v is None:
        return None
    if isinstance(v, list) and v:
        return v[0]
    if isinstance(v, dict):
        return v
    if isinstance(v, np.ndarray) and v.dtype == object and v.size > 0:
        return v.ravel(order="F")[0]
    return None


def _vb_monitor_chain(
    band: str,
    node: Any,
    path_str: str,
    m: int | None,
    t: int | None,
    iter_tag: str,
) -> None:
    if node is None:
        return
    if not isinstance(node, dict):
        print(
            f"[VB monitor {band}] path={path_str} iter={iter_tag} "
            f"<not a dict> type={type(node).__name__}",
            file=sys.stderr,
            flush=True,
        )
        return
    l_val = node.get("L")
    l_str = f" L={l_val}" if l_val is not None else ""
    m_str = f" m={m}" if m is not None else ""
    t_str = f" t={t}" if t is not None else ""
    print(
        f"[VB monitor {band}]{l_str} path={path_str} iter={iter_tag}{m_str}{t_str} (PY)",
        file=sys.stderr,
        flush=True,
    )
    for k in sorted(node.keys(), key=str):
        if k == "MDP":
            child = _vb_monitor_unwrap_mdp(node[k])
            if child is not None:
                _vb_monitor_chain(band, child, f"{path_str}.MDP", m, t, iter_tag)
            continue
        desc = _vb_monitor_desc(node[k])
        print(
            f"[VB monitor {band} PY field] path={path_str} {k}={desc}",
            file=sys.stderr,
            flush=True,
        )


def _vb_monitor_snapshot(
    band: str,
    mdp: Any,
    m: int | None,
    t: int | None,
    iter_tag: str,
) -> None:
    if not _vb_monitoring_active():
        return
    path_str = f"MDP({m})" if m is not None else "MDP"
    if band == "12E":
        path_str = f"{path_str}.MDP"
    _vb_monitor_chain(band, mdp, path_str, m, t, iter_tag)


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
            f"[spm_MDP_VB_XXX {label}] total_s={total:.6f}",
            file=sys.stderr,
            flush=True,
        )


def _spm_sample(p: Any) -> int:
    """
    File-local ``spm_sample`` from ``spm_MDP_VB_XXX.m`` (lines ~2613–2621).

    Mirrors ``spm_MDP_generate._spm_sample`` and MATLAB’s implementation in both
    files: logical masks use ``find`` + ``randperm`` semantics; numeric columns use
    ``cumsum`` + one ``rand`` (see ``notes/andrew Python Matlab Translation Issues.md``,
    RNG subsection).
    """
    if isinstance(p, np.ndarray) and p.dtype == bool:
        flat = np.flatnonzero(p.ravel(order="F"))
        k = int(flat.size)
        if k == 0:
            raise ValueError("spm_sample: empty logical mask")
        if k == 1:
            return int(flat[0] + 1)
        r1 = float(np.random.rand())
        if k <= 4:
            float(np.random.rand())
        pos = int(np.floor(r1 * k))
        if pos >= k:
            pos = k - 1
        return int(flat[pos] + 1)
    pv = np.asarray(p, dtype=np.float64).ravel(order="F")
    total = float(np.sum(pv))
    if (not np.isfinite(total)) or total <= 0.0 or (not np.all(np.isfinite(pv))):
        n = int(pv.size)
        if n <= 0:
            raise ValueError("spm_sample: empty numeric probability vector")
        # Degenerate / zero-mass (e.g. ``spm_norm`` of all-zero ``GP.E{f}``): uniform over supports.
        pv = np.ones((n,), dtype=np.float64) / float(n)
    cs = np.cumsum(pv)
    r = float(np.random.rand())
    hit = np.flatnonzero(r < cs)
    if hit.size == 0:
        idx = int(pv.size) - 1
    else:
        idx = int(hit[0])
    return idx + 1


def spm_children(id_dict: dict[str, Any]) -> np.ndarray:
    """Local ``spm_children`` from ``spm_MDP_VB_XXX.m`` (~2584)."""
    if "g" in id_dict:
        gcell = id_dict["g"]
        if "i" in id_dict:
            ii = int(np.asarray(id_dict["i"], dtype=np.int64).ravel()[0])
            gi = gcell[ii - 1]
            arr = np.atleast_1d(np.asarray(gi, dtype=np.int64).ravel())
            return arr.astype(np.int64).reshape(1, -1)
        flat: list[int] = []
        for gi in gcell:
            flat.extend(np.asarray(gi, dtype=np.int64).ravel().tolist())
        if len(flat) == 0:
            return np.zeros((1, 0), dtype=np.int64)
        u = np.unique(np.asarray(flat, dtype=np.int64))
        return u.astype(np.int64).reshape(1, -1)
    na = len(id_dict.get("A", []))
    return np.arange(1, na + 1, dtype=np.int64).reshape(1, -1)


def _numel(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, (list, tuple)):
        return len(x)
    return int(np.asarray(x, dtype=object).size)


def _cell_get_Qj(Q: list[Any], j: Any) -> list[Any]:
    jv = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
    return [Q[int(jj) - 1] for jj in jv.tolist()]


def _spm_induction_vb(
    B: list[list[np.ndarray]],
    H: list[Any],
    Q: list[Any],
    N: int,
    id_dict: dict[str, Any],
) -> tuple[Any, np.ndarray]:
    """Local ``spm_induction(B,H,Q,N,id)`` from ``spm_MDP_VB_XXX.m``."""
    global _PROBE_12F_PARENT
    _probe_ind = bool(os.getenv("RGMS_PROBE_12F_PARENT_T1")) and _PROBE_12F_PARENT is not None

    if "hid" in id_dict and id_dict["hid"] is not None:
        hid_m = id_dict["hid"]
        if callable(hid_m):
            raise NotImplementedError("spm_induction: id.hid function_handle not translated")
        hid_full = np.asarray(hid_m, dtype=np.float64)
        if hid_full.ndim < 2:
            # MATLAB ``id.hid`` is ``Nf×Ni``; a flat vector is ``1×Ni`` when ``Nf==1``, not ``Nf×1``.
            nf_h = len(H)
            if nf_h == 1:
                hid_full = np.reshape(hid_full, (1, -1), order="F")
            else:
                hid_full = np.reshape(hid_full, (-1, 1), order="F")
        hif = (np.flatnonzero(np.any(hid_full != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
        hid = hid_full
    else:
        hid_list: list[float] = []
        hif_list: list[int] = []
        for f in range(len(H)):
            Hf = H[f]
            if _numel(Hf) > 0:
                hf = np.asarray(mfull(Hf), dtype=np.float64).reshape(-1, order="F")
                s = int(np.argmax(hf) + 1)
                hid_list.append(float(s))
                hif_list.append(int(f + 1))
        if not hid_list:
            hid = np.zeros((0, 0), dtype=np.float64)
        else:
            hid = np.asarray(hid_list, dtype=np.float64).reshape(-1, 1)
        hif = np.asarray(hif_list, dtype=np.int64).reshape(1, -1)

    if "cid" in id_dict and id_dict["cid"] is not None:
        cid_raw = id_dict["cid"]
        if callable(cid_raw):
            raise NotImplementedError("spm_induction: id.cid function_handle not translated")
        cid_arr = np.asarray(cid_raw, dtype=np.float64)
        if cid_arr.size == 0:
            d_tensor: Any = True
            d_flat = None
        else:
            cid = cid_arr
            nid = cid.copy()
            hif = (np.flatnonzero(np.all(cid != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
            for f in hif.ravel().tolist():
                nid[int(f) - 1, :] = 0
            ns_list = [int(B[int(f) - 1][0].shape[0]) for f in hif.ravel().tolist()] + [1]
            ns_tuple = tuple(ns_list)
            d_tensor = np.ones(ns_tuple, dtype=bool)
            for i in range(cid.shape[1]):
                qv = 1.0
                for f0 in range(cid.shape[0]):
                    if nid[f0, i] != 0:
                        f1 = f0 + 1
                        cidx = int(nid[f0, i])
                        qcol = np.asarray(Q[f1 - 1], dtype=np.float64).reshape(-1, order="F")
                        qv *= float(qcol[cidx - 1])
                if qv > (1.0 - 1.0 / 8.0):
                    inds = [int(cid[int(f) - 1, i]) for f in hif.ravel().tolist()]
                    lin = int(np.ravel_multi_index(tuple(x - 1 for x in inds), tuple(ns_list[:-1]), order="F"))
                    d_tensor[np.unravel_index(lin, d_tensor.shape, order="F")] = False
            d_flat = d_tensor.reshape(-1, order="F")
    else:
        d_tensor = True
        d_flat = None

    hif_list = [int(x) for x in np.asarray(hif, dtype=np.int64).ravel().tolist()]
    hid = np.asarray(hid, dtype=np.float64)
    if hid.ndim == 2 and hid.shape[0] > len(hif_list) and len(hif_list) > 0:
        hid = hid[np.asarray(hif_list, dtype=int) - 1, :]

    if len(hif_list) == 0:
        if _probe_ind:
            _PROBE_12F_PARENT["ind_branch"] = "empty_hif"
        return np.array([]), np.array([], dtype=np.int64)
    if hid.size == 0:
        if _probe_ind:
            _PROBE_12F_PARENT["ind_branch"] = "empty_hid"
            _PROBE_12F_PARENT["hid_shape"] = list(np.asarray(hid).shape)
            _PROBE_12F_PARENT["hid_all_zero"] = bool(np.all(hid == 0)) if hid.size else False
            _PROBE_12F_PARENT["D_is_scalar"] = d_tensor is True
            if d_flat is not None:
                d_arr = np.asarray(d_flat, dtype=bool).ravel(order="F")
                _PROBE_12F_PARENT["D_nnz"] = int(np.count_nonzero(d_arr))
            else:
                _PROBE_12F_PARENT["D_nnz"] = 1
        if d_tensor is True:
            # MATLAB ``if isempty(hid), R = 32*D;`` with scalar ``D = true`` → ``R = 32``.
            return np.asarray(32.0, dtype=np.float64), np.asarray(hif_list, dtype=np.int64)
        r32 = (32.0 * np.asarray(d_flat, dtype=np.float32).ravel(order="F")).astype(np.float32)
        return r32, np.asarray(hif_list, dtype=np.int64)

    N = int(min(int(N), 64))
    if "D" in id_dict and N < 4:
        N = 64
    if N <= 0:
        return np.array([]), np.asarray(hif_list, dtype=np.int64)

    u_thr = 1.0 / 32.0
    if not B or len(B) == 0:
        return np.array([]), np.array([], dtype=np.int64)
    nk = len(B[0])
    if nk == 0:
        return np.array([]), np.array([], dtype=np.int64)
    b_map: dict[int, np.ndarray] = {}
    for f in hif_list:
        if f < 1 or f > len(B) or len(B[f - 1]) == 0:
            continue
        acc = None
        nk_f = len(B[f - 1])
        for k in range(min(nk, nk_f)):
            try:
                bfk = np.asarray(B[f - 1][k], dtype=np.float64)
            except Exception:
                bfk = np.asarray(B[f - 1][0], dtype=np.float64)
            thr = bfk > u_thr
            acc = thr if acc is None else (acc | thr)
        if acc is None:
            continue
        b_map[f] = np.asarray(acc, dtype=bool)
    if not b_map:
        return np.array([]), np.array([], dtype=np.int64)
    hif_kept = [f for f in hif_list if f in b_map]

    hid = np.asarray(hid, dtype=np.float64)
    if hid.ndim == 2 and len(hif_kept) > 0:
        idx_kept = [hif_list.index(f) for f in hif_kept]
        hid = hid[np.asarray(idx_kept, dtype=int), :]

    Bf = sparse.csr_matrix([[1.0]], dtype=np.float64)
    Qf = sparse.csr_matrix([[1.0]], dtype=np.float64)
    ns_by_pos: list[int] = []
    for f in hif_kept:
        ns_by_pos.append(int(B[f - 1][0].shape[0]))
        Bf = spm_kron(b_map[f], Bf)
        Qcol = np.asarray(Q[f - 1], dtype=np.float64).reshape(-1, 1, order="F")
        Qf = spm_kron(sparse.csr_matrix(Qcol), Qf)

    if d_flat is None:
        d_mul = np.ones(int(Bf.shape[0] * Bf.shape[1]), dtype=np.float64)
    else:
        d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")
        if d_mul.size != int(Bf.shape[0] * Bf.shape[1]):
            raise ValueError("spm_induction: D size mismatch with Bf")
    bf_dense = Bf.toarray(order="F")
    bf_dense = bf_dense * d_mul.reshape(bf_dense.shape, order="F")
    Bf = sparse.csr_matrix(bf_dense)

    hid_arr = np.asarray(hid, dtype=np.float64)
    if hid_arr.ndim == 1:
        hid_arr = hid_arr.reshape(-1, 1)
    nh = int(hid_arr.shape[1])
    pf_cols: list[np.ndarray] = []
    for i in range(nh):
        I = np.array([[True]], dtype=bool)
        for pos, f in enumerate(hif_kept):
            nsf = ns_by_pos[pos]
            hvec = np.zeros((nsf, 1), dtype=bool)
            hidx = int(hid_arr[pos, i])
            if hidx > 0:
                hvec[hidx - 1, 0] = True
            I = spm_kron(hvec, I).toarray().astype(bool)
        pf_cols.append(I.ravel(order="F"))

    l_dim = int(pf_cols[0].size)
    Pf = np.zeros((l_dim, nh), dtype=bool)
    for i in range(nh):
        Pf[:, i] = pf_cols[i]

    # MATLAB ``G(j,i) = I'*Qf`` with ``j = 1:size(I,2)`` may write row ``N+1``;
    # out-of-range assignment grows ``G`` — do not truncate to ``N`` rows here.
    G = np.zeros((N + 1, nh), dtype=np.float64)
    p_store: list[np.ndarray] = []
    qf_dense = Qf.toarray(order="F").ravel(order="F").reshape(-1, 1, order="F")

    for i in range(nh):
        I = np.asarray(Pf[:, i], dtype=bool).reshape(-1, 1)
        ncols = N + 1
        I_big = np.zeros((I.shape[0], ncols), dtype=bool)
        I_big[:, 0] = I.ravel()
        for n in range(N):
            prev = I_big[:, n]
            if not np.any(prev):
                break
            rows = np.flatnonzero(prev)
            sub = Bf[rows, :]
            nxt = np.asarray(sub.sum(axis=0) > 0).ravel()
            I_big[:, n + 1] = nxt
        vec = (I_big.astype(np.float64).T @ qf_dense).ravel(order="F")
        ncol = int(min(I_big.shape[1], G.shape[0]))
        G[:ncol, i] = vec[:ncol]
        p_store.append(I_big.copy())

    G[0, :] = 0.0
    dmx = np.max(G, axis=0)
    nmx = np.argmax(G, axis=0)
    mask = dmx > u_thr
    if not np.any(mask):
        return np.array([]), np.asarray(hif_kept, dtype=np.int64)

    p_sel = [p_store[j] for j in range(nh) if mask[j]]
    n_sel = nmx[mask]
    j0 = int(np.argmin(n_sel))
    p_use = p_sel[j0]
    n_use = int(n_sel[j0])
    # ``n_use`` is 0-based row from ``argmax``; MATLAB ``P(:,max(n-1,1))`` with 1-based ``n``.
    col_idx = max(int(n_use) - 1, 0)
    p_vec = p_use[:, col_idx].astype(np.float64)
    p_col = p_vec.reshape(-1, 1, order="F")
    if d_tensor is True:
        d_col = np.ones_like(p_col, dtype=bool)
    else:
        d_col = np.asarray(d_tensor, dtype=bool).reshape(p_col.shape, order="F")
    R = (32.0 * np.logical_and(p_col.astype(bool), d_col.astype(bool))).astype(np.float64)
    if os.getenv("RGMS_INDUCTION_DBG"):
        global _INDUCTION_DBG
        _INDUCTION_DBG = {
            "goal_i": int(j0),
            "n_col": int(n_use),
            "col_idx": int(col_idx),
            "P_nz": np.flatnonzero(p_col.ravel() > 0).tolist(),
            "dmx": np.asarray(dmx, dtype=np.float64).ravel().tolist(),
            "nmx": np.asarray(nmx, dtype=np.int64).ravel().tolist(),
            "Pf_col0_nnz": int(np.count_nonzero(Pf[:, 0])) if Pf.size else 0,
            "G_shape": list(G.shape),
        }
    if _probe_ind:
        _PROBE_12F_PARENT["ind_branch"] = "full_induction"
        _PROBE_12F_PARENT["hid_shape"] = list(np.asarray(hid).shape)
        _PROBE_12F_PARENT["hid_all_zero"] = bool(np.all(hid == 0))
        _PROBE_12F_PARENT["Nh"] = int(nh)
        _PROBE_12F_PARENT["D_is_scalar"] = d_tensor is True
        if d_flat is not None:
            _PROBE_12F_PARENT["D_nnz"] = int(np.count_nonzero(np.asarray(d_flat, dtype=bool)))
        else:
            _PROBE_12F_PARENT["D_nnz"] = int(np.count_nonzero(d_col))
        Rv = np.asarray(R, dtype=np.float64).ravel(order="F")
        _PROBE_12F_PARENT["R_nnz_ind"] = int(np.count_nonzero(Rv > 0.0))
    return R, np.asarray(hif_kept, dtype=np.int64)


def spm_forwards(
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
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None = None,
) -> tuple[np.ndarray, Any, float, list[Any], dict[int, Any]]:
    """Local ``spm_forwards`` from ``spm_MDP_VB_XXX.m`` (~1749)."""
    mi = int(m) - 1
    idm = id_list[mi]
    Ni = len(idm["g"])
    nk = len(B[mi][0])
    nf = len(B[mi])
    G = np.zeros((nk, Ni), dtype=np.float64)
    Pa: dict[int, Any] = {}

    O_row = [O[mi][g][t - 1] for g in range(len(O[mi]))]
    P_row = [P[mi][f][t - 1] for f in range(len(P[mi]))]
    A_row = A[mi]
    if _vb_dump_active():
        _entry12_record_phase_belief_rows(
            mi,
            t,
            "pre_vbx",
            O,
            P,
            P_row,
            extra={"A_peaks": _entry12_a_peaks_for_model(A, mi)},
        )
    Q_upd, F = spm_VBX(O_row, P_row, A_row, idm)
    F_vbx_here = float(F)
    if _vb_dump_active():
        _entry12_record_phase_belief_rows(
            mi, t, "post_vbx", O, P, Q_upd, extra={"F_vbx": F_vbx_here}
        )
    if _vb_capture_y_probe_active():
        _entry12_record_vbx_probe(mi, t, Q_upd, O_row, P_row, idm, F_vbx=F_vbx_here)
    for f in range(len(Q_upd)):
        P[mi][f][t - 1] = Q_upd[f]

    # MATLAB: ``if t > T || numel(G) == 1, return, end`` (policy×covert count, not ``numel`` of ``G`` array)
    if t > T or (nk * Ni == 1):
        return G, P, float(F_vbx_here), id_list, Pa

    B_slice = B[mi]
    H_slice = H[mi]
    P_now = [P[mi][f][t - 1] for f in range(nf)]
    global _PROBE_12F_PARENT
    if os.getenv("RGMS_PROBE_12F_PARENT_T1") and t == 1 and m == 1 and nk >= 6 and _PROBE_12F_PARENT is None:
        _PROBE_12F_PARENT = {}
    R, r = _spm_induction_vb(B_slice, H_slice, P_now, int(T - t), idm)
    if (
        os.getenv("RGMS_PROBE_12F_PARENT_T1")
        and t == 1
        and m == 1
        and nk >= 6
        and isinstance(_PROBE_12F_PARENT, dict)
    ):
        Rv0 = np.asarray(R, dtype=np.float64).ravel(order="F")
        _PROBE_12F_PARENT["R_sum_post_induction"] = float(np.sum(Rv0))
        _PROBE_12F_PARENT["R_nz_post_induction"] = np.flatnonzero(Rv0 > 0.0).tolist()[:8]
    if np.asarray(R).size:
        Rv = np.asarray(R, dtype=np.float64)
        if Rv.ndim == 1:
            R = Rv.reshape(1, -1, order="F")
        elif Rv.ndim == 2 and Rv.shape[1] == 1:
            R = Rv.reshape(1, -1, order="F")
        else:
            R = Rv

    Qp: list[Any] = [None] * nf
    id_fp = np.asarray(idm.get("fp", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    for f in id_fp.tolist():
        Bf1 = np.asarray(B_slice[int(f) - 1][0], dtype=np.float64)
        Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
        Qp[int(f) - 1] = Bf1 @ Pf

    id_fu = np.asarray(idm.get("fu", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_iH = np.asarray(idm.get("iH", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_iI = np.asarray(idm.get("iI", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()

    _probe_parent = bool(
        os.getenv("RGMS_PROBE_12F_PARENT_T1") and t == 1 and m == 1 and nk >= 6 and _PROBE_12F_PARENT is not None
    )

    for k in range(nk):
        for f in id_fu.tolist():
            Bfk = np.asarray(B_slice[int(f) - 1][k], dtype=np.float64)
            Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Qp[int(f) - 1] = Bfk @ Pf

        if _probe_parent and k == 0 and "G_before_iH" not in _PROBE_12F_PARENT:
            _PROBE_12F_PARENT["G_before_iH"] = float(np.asarray(G[k, 0], dtype=np.float64))

        for f in id_iH.tolist():
            Qf = np.asarray(Qp[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            Hf = np.asarray(H_slice[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            ih_term = float((Qf.T @ (_spm_log(Qf) - _spm_log(Hf))).reshape(-1)[0])
            G[k, :] -= ih_term
            if _probe_parent and k == 0:
                _PROBE_12F_PARENT["ih_term"] = ih_term
                _PROBE_12F_PARENT["G_after_iH"] = float(np.asarray(G[k, 0], dtype=np.float64))

        for f in id_iI.tolist():
            Pmf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(1, -1, order="F")
            Iblk = np.asarray(I[mi][int(f) - 1][k], dtype=np.float64)
            Qf = np.asarray(Qp[int(f) - 1], dtype=np.float64).reshape(-1, 1, order="F")
            G[k, :] += float(Pmf @ Iblk @ Qf)

        if _numel(R) > 0:
            q_cells = _cell_get_Qj(Qp, r)
            if _probe_parent and k == 0:
                Rv = np.asarray(R, dtype=np.float64)
                _PROBE_12F_PARENT["R_shape"] = list(Rv.shape)
                _PROBE_12F_PARENT["R_max"] = float(np.max(Rv)) if Rv.size else 0.0
                _PROBE_12F_PARENT["R_sum"] = float(np.sum(Rv))
                _PROBE_12F_PARENT["r_factors"] = np.atleast_1d(np.asarray(r, dtype=np.int64)).ravel().tolist()
                if len(q_cells) == 1:
                    Qflat = np.asarray(q_cells[0], dtype=np.float64).ravel(order="F")
                else:
                    Qflat = np.asarray(spm_cross(q_cells), dtype=np.float64).ravel(order="F")
                Rflat = Rv.ravel(order="F")
                nz = np.flatnonzero(Rflat > 0.0)
                _PROBE_12F_PARENT["R_nz_idx"] = nz[:8].tolist()
                _PROBE_12F_PARENT["Q_at_R_nz"] = Qflat[nz[:8]].tolist() if nz.size else []
                _PROBE_12F_PARENT["dot_manual_RQ"] = float((Rflat.reshape(1, -1) @ Qflat.reshape(-1, 1)).reshape(-1)[0])
                for fi in _PROBE_12F_PARENT["r_factors"]:
                    Qfi = np.asarray(Qp[int(fi) - 1], dtype=np.float64).ravel(order="F")
                    Pfi = np.asarray(P[mi][int(fi) - 1][t - 1], dtype=np.float64).ravel(order="F")
                    _PROBE_12F_PARENT[f"Qf_len_f{fi}"] = int(Qfi.size)
                    _PROBE_12F_PARENT[f"Qf_max_f{fi}"] = float(np.max(Qfi)) if Qfi.size else 0.0
                    _PROBE_12F_PARENT[f"Pf_sum_f{fi}"] = float(np.sum(Pfi))
            g_risk = np.asarray(spm_dot(R, q_cells), dtype=np.float64).reshape(-1)
            if _probe_parent and k == 0:
                _PROBE_12F_PARENT["spm_dot_R_Q"] = float(g_risk.reshape(-1)[0]) if g_risk.size else 0.0
                _PROBE_12F_PARENT["G_after_dot"] = float(np.asarray(G[k, 0], dtype=np.float64))
                _PROBE_12F_PARENT["done"] = True
            if g_risk.size == 1:
                G[k, :] += float(g_risk[0])
            elif g_risk.size == Ni:
                G[k, :] += g_risk
            else:
                G[k, :] += float(g_risk[0])

        No = np.zeros((1, Ni), dtype=np.float64)
        for i_cov in range(Ni):
            gi = idm["g"][i_cov]
            if "ge" in idm:
                ge = np.asarray(idm["ge"], dtype=np.int64).ravel()
                gi = np.array([x for x in np.atleast_1d(np.asarray(gi).ravel()) if x in set(ge.tolist())], dtype=np.int64)
            for ig in np.atleast_1d(np.asarray(gi, dtype=np.int64).ravel()):
                j, gg = spm_parents(idm, int(ig), Qp)
                for g in np.atleast_1d(np.asarray(gg, dtype=np.int64).ravel()):
                    Amg = A[mi][int(g) - 1]
                    qj = _cell_get_Qj(Qp, j)
                    if callable(Amg):
                        raise NotImplementedError("spm_forwards: A{m,g} function_handle not translated")
                    qo = np.asarray(spm_dot(Amg, qj), dtype=np.float64).reshape(-1, 1, order="F")
                    No[0, i_cov] += float(
                        np.asarray(_spm_log(np.array([[float(np.size(qo))]], dtype=np.float64)), dtype=np.float64).reshape(-1)[0]
                    )
                    G[k, i_cov] -= float((qo.T @ _spm_log(qo)).reshape(-1)[0])
                    Cmg = C[mi][int(g) - 1]
                    if _numel(Cmg) > 0:
                        c_cells = idm.get("C", [])
                        cg = None
                        if isinstance(c_cells, (list, tuple)) and len(c_cells) >= int(g):
                            cg = c_cells[int(g) - 1]
                        if cg is not None and _numel(cg) > 0:
                            fC = int(np.asarray(cg, dtype=np.int64).ravel()[0])
                            U = np.asarray(
                                spm_dot(_spm_log(np.asarray(Cmg, dtype=np.float64)), Qp[int(fC) - 1]),
                                dtype=np.float64,
                            ).reshape(-1, 1, order="F")
                        else:
                            U = np.asarray(_spm_log(np.asarray(Cmg, dtype=np.float64)), dtype=np.float64).reshape(-1, 1, order="F")
                        G[k, i_cov] += float((qo.T @ U).reshape(-1)[0])
                    Kmg = K[mi][int(g) - 1]
                    if _numel(Kmg) > 0:
                        G[k, i_cov] += float(np.asarray(spm_dot(Kmg, qj), dtype=np.float64).reshape(-1)[0])
                    Wmg = W[mi][int(g) - 1]
                    if _numel(Wmg) > 0:
                        G[k, i_cov] += float((qo.T @ np.asarray(spm_dot(Wmg, qj), dtype=np.float64).reshape(-1, 1)).reshape(-1)[0])
                    pAg = pA[mi][int(g) - 1]
                    if _numel(pAg) > 0:
                        if qa is None:
                            raise ValueError("spm_forwards: qa required when pA is non-empty")
                        da = spm_cross(qo, qj)
                        Pa[int(g)] = spm_MDP_BMR(np.asarray(qa[mi][int(g) - 1], dtype=np.float64), pAg)
                        Pg = spm_MDP_BMR(np.asarray(qa[mi][int(g) - 1], dtype=np.float64) + np.asarray(da, dtype=np.float64), pAg)
                        pal = np.asarray(Pa[int(g)], dtype=np.float64).reshape(-1, 1, order="F")
                        pgl = np.asarray(Pg, dtype=np.float64).reshape(-1, 1, order="F")
                        G[k, i_cov] += float((pgl.T @ (_spm_log(pgl) - _spm_log(pal))).reshape(-1)[0])
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
            for f in id_fu.tolist():
                Bfk = np.asarray(B_slice[int(f) - 1][k], dtype=np.float64)
                Pf = np.asarray(P[mi][int(f) - 1][t - 1], dtype=np.float64).reshape(-1, 1, order="F")
                Qp[int(f) - 1] = Bfk @ Pf

            j_acc: list[int] = []
            for g in ig.tolist():
                j1, _ = spm_parents(idm, int(g), Qp)
                j1a = np.unique(np.atleast_1d(np.asarray(j1, dtype=np.int64).ravel())).tolist()
                j_acc = sorted(set(j_acc + [int(x) for x in j1a]))
            jv = np.asarray(j_acc, dtype=np.int64)

            s_list: list[np.ndarray] = []
            S_list: list[np.ndarray] = []
            n_list: list[int] = []
            for jf in jv.tolist():
                Qjf = np.asarray(Qp[int(jf) - 1], dtype=np.float64).reshape(-1, order="F")
                s_idx = np.flatnonzero(Qjf > np.exp(-8.0)) + 1
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
                for g in ig.tolist():
                    fac, gg = spm_parents(idm, int(g), Qp)
                    ind_cell = [int(fi[int(ff) - 1]) for ff in np.atleast_1d(np.asarray(fac, dtype=np.int64).ravel())]
                    Amg = A[mi][int(g) - 1]
                    for o in np.atleast_1d(np.asarray(gg, dtype=np.int64).ravel()):
                        if callable(Amg):
                            raise NotImplementedError("spm_forwards: function_handle A in recursion")
                        sl = tuple(slice(int(x - 1), int(x)) for x in ind_cell)
                        if Amg.ndim == len(ind_cell) + 1:
                            col = np.asarray(Amg[(slice(None),) + sl], dtype=np.float64).reshape(-1, 1, order="F")
                        else:
                            col = np.asarray(Amg[sl], dtype=np.float64).reshape(-1, 1, order="F")
                        O[mi][int(o) - 1][t] = col
                for f in range(nf):
                    P[mi][f][t] = Qp[f]
                E = spm_forwards(O, P, A, B, C, H, K, W, I, t + 1, T, N, m, id_list, pA, qa)[0]
                Es = np.asarray(spm_softmax(E), dtype=np.float64).reshape(-1, 1, order="F")
                Ea = np.asarray(E, dtype=np.float64).reshape(-1, 1, order="F")
                EFE.ravel(order="F")[ii_lin] = float((Es.T @ Ea).reshape(-1)[0])

            G[k, 0] += float(np.sum(EFE * q))

    return G, P, float(F_vbx_here), id_list, Pa


def _pagetranspose_bw(a: Any) -> np.ndarray:
    a = np.asarray(mfull(a), dtype=np.float64)
    if a.ndim <= 2:
        return np.ascontiguousarray(a.T)
    return np.swapaxes(a, 0, 1)


def _unique_stable_bw(j: np.ndarray) -> np.ndarray:
    jv = np.asarray(j, dtype=np.int64).ravel()
    seen: set[int] = set()
    out: list[int] = []
    for v in jv.tolist():
        if int(v) not in seen:
            seen.add(int(v))
            out.append(int(v))
    return np.array(out, dtype=np.int64).reshape(1, -1)


def _numel_qb_row_bw(qb: list[Any], mi: int) -> int:
    row = qb[mi]
    if isinstance(row, list):
        return len(row)
    return int(np.asarray(row, dtype=object).size)


def _Q_row_m_t_bw(Q: list[Any], mi: int, t_m: int) -> list[Any]:
    ti = t_m - 1
    return [Q[mi][f][ti] for f in range(len(Q[mi]))]


def _sdot_mtimes_q_bw(s_dot_p: Any, q_next: np.ndarray) -> np.ndarray:
    a = np.asarray(mfull(s_dot_p), dtype=np.float64)
    b = np.asarray(q_next, dtype=np.float64).reshape(-1, 1, order="F")
    if a.ndim == 2 and a.shape[1] == b.shape[0]:
        return np.asarray((a @ b).reshape(-1, 1), dtype=np.float64, order="F")
    if a.size == b.size:
        return (a.reshape(-1, 1) * b.reshape(-1, 1)).astype(np.float64)
    return (np.asarray(a).reshape(-1, 1) * b.reshape(-1, 1)).astype(np.float64)


def _cell_get_Qjt_bw(Q: list[Any], mi: int, jv: np.ndarray, ti: int) -> Any:
    jv = np.asarray(jv, dtype=np.int64).ravel()
    if jv.size == 1:
        return Q[mi][int(jv[0]) - 1][ti]
    return [Q[mi][int(j) - 1][ti] for j in jv.tolist()]


def _Q_factors_subset_bw(Q: list[Any], mi: int, r: np.ndarray, ti: int) -> list[Any]:
    out: list[Any] = []
    for idx in r.tolist():
        fi = int(idx)
        out.append(Q[mi][fi][ti])
    return out


def spm_backwards(
    O: list[Any],
    P: list[Any],
    Q: list[Any],
    D: list[Any],
    E: list[Any],
    pa: list[Any],
    pb: list[Any],
    U: list[Any],
    m: int,
    id_list: list[Any],
) -> tuple[list[Any], list[Any], list[Any], list[Any], np.ndarray]:
    """Local ``spm_backwards`` from ``spm_MDP_VB_XXX.m`` (~2081–2332)."""
    mi = int(m) - 1
    idm = id_list[mi]
    tr = _pagetranspose_bw

    Nf = len(Q[mi])
    T = len(Q[mi][0])
    Z = -np.inf
    F_out = np.zeros(T, dtype=np.float64)

    for _v in range(16):
        F = np.zeros(T, dtype=np.float64)
        qa = copy.deepcopy(pa)
        qb = copy.deepcopy(pb)

        for t_m in range(1, T + 1):
            ti = t_m - 1
            Qrow = _Q_row_m_t_bw(Q, mi, t_m)
            for g in np.ravel(spm_children(idm)).tolist():
                g = int(g)
                j, i_ch = spm_parents(idm, g, Qrow)
                for o in np.atleast_1d(np.asarray(i_ch)).ravel():
                    o = int(o)
                    Omot = O[mi][o - 1][ti]
                    jv = np.atleast_1d(np.asarray(j)).ravel()
                    acc = spm_cross(Omot, _cell_get_Qjt_bw(Q, mi, jv, ti))
                    qa[mi][g - 1] = np.asarray(qa[mi][g - 1], dtype=np.float64) + np.asarray(acc, dtype=np.float64)
                    pa_mg = np.asarray(pa[mi][g - 1], dtype=np.float64)
                    qa[mi][g - 1] = qa[mi][g - 1] * (pa_mg > 0)

            if t_m < T:
                nqb = _numel_qb_row_bw(qb, mi)
                for f_1 in range(1, nqb + 1):
                    fi = f_1 - 1
                    acc = spm_cross(spm_cross(Q[mi][fi][ti + 1], Q[mi][fi][ti]), P[mi][fi][ti])
                    qb[mi][fi] = np.asarray(qb[mi][fi], dtype=np.float64) + np.asarray(acc, dtype=np.float64)
                    pb_mf = np.asarray(pb[mi][fi], dtype=np.float64)
                    qb[mi][fi] = qb[mi][fi] * (pb_mf > 0)

        for t_m in range(1, T + 1):
            ti = t_m - 1
            Qrow = _Q_row_m_t_bw(Q, mi, t_m)

            if isinstance(idm, dict) and "independent" in idm:
                Lcell: list[Any] = [0.0] * Nf
                for g in np.ravel(spm_children(idm)).tolist():
                    g = int(g)
                    j, k = spm_parents(idm, g, Qrow)
                    j = _unique_stable_bw(np.asarray(j, dtype=np.int64))
                    LL = None
                    for o in np.atleast_1d(np.asarray(k)).ravel():
                        o = int(o)
                        Omot = O[mi][o - 1][ti]
                        qa_mg = _spm_norm(qa[mi][g - 1])
                        dot_v = spm_dot(qa_mg, Omot)
                        logv = np.asarray(_spm_log(dot_v), dtype=np.float64)
                        LL = logv if LL is None else (LL + logv)
                    for jj in np.atleast_1d(j).ravel():
                        idx = int(jj) - 1
                        if isinstance(Lcell[idx], float):
                            Lcell[idx] = np.asarray(LL, dtype=np.float64)
                        else:
                            Lcell[idx] = np.asarray(Lcell[idx], dtype=np.float64) + np.asarray(LL, dtype=np.float64)

                nqb = _numel_qb_row_bw(qb, mi)
                f_last = nqb
                for _ii in range(1, Nf + 1):
                    Lf0 = np.asarray(Lcell[f_last - 1], dtype=np.float64)
                    Lf = Lf0.reshape(-1, 1, order="F")
                    dD = D[mi][f_last - 1]
                    n_s = int(np.asarray(dD, dtype=np.float64).shape[0])
                    LPv = np.zeros((n_s, 1), dtype=np.float64)
                    if t_m == 1:
                        LPv = LPv + np.asarray(_spm_log(D[mi][f_last - 1]), dtype=np.float64).reshape(-1, 1, order="F")
                    if t_m < T:
                        qbf = np.asarray(qb[mi][f_last - 1], dtype=np.float64)
                        Pmft = P[mi][f_last - 1][ti]
                        Qn = Q[mi][f_last - 1][ti + 1]
                        tdot = spm_dot(spm_psi(tr(qbf)), Pmft)
                        LPv = LPv + _sdot_mtimes_q_bw(tdot, np.asarray(Qn, dtype=np.float64))
                    if t_m > 1:
                        qbf = np.asarray(qb[mi][f_last - 1], dtype=np.float64)
                        Pprev = P[mi][f_last - 1][ti - 1]
                        Qp = Q[mi][f_last - 1][ti - 1]
                        tdot = spm_dot(spm_psi(qbf), Pprev)
                        LPv = LPv + _sdot_mtimes_q_bw(tdot, np.asarray(Qp, dtype=np.float64))
                    sm_in = Lf + LPv
                    Q[mi][f_last - 1][ti] = spm_softmax(np.asarray(sm_in, dtype=np.float64))
                    q_post = np.asarray(Q[mi][f_last - 1][ti], dtype=np.float64).reshape(-1, 1)
                    logq = _spm_log(q_post)
                    F[ti] = F[ti] + float(np.sum(q_post * (sm_in - logq)))

            else:
                L = np.asarray(0.0, dtype=np.float64)
                for g in np.ravel(spm_children(idm)).tolist():
                    g = int(g)
                    j, k = spm_parents(idm, g, Qrow)
                    j = _unique_stable_bw(np.asarray(j, dtype=np.int64))
                    LL = None
                    for o in np.atleast_1d(np.asarray(k)).ravel():
                        o = int(o)
                        Omot = O[mi][o - 1][ti]
                        qa_mg = _spm_norm(qa[mi][g - 1])
                        dot_v = spm_dot(qa_mg, Omot)
                        logv = np.asarray(_spm_log(dot_v), dtype=np.float64)
                        LL = logv if LL is None else (LL + logv)
                    jv = np.asarray(j, dtype=np.int64).ravel()
                    if jv.size > 1:
                        order = np.argsort(jv, kind="mergesort")
                        jv = jv[order]
                        perm_axes = (order + 1).tolist()
                        LL = np.transpose(np.asarray(LL, dtype=np.float64), np.asarray(perm_axes) - 1)
                    sz_ll = matlab_size(LL)
                    kdims = np.ones(Nf + 1, dtype=np.int64)
                    for ix, fac in enumerate(jv.tolist()):
                        if ix < len(sz_ll):
                            kdims[int(fac) - 1] = int(sz_ll[ix])
                    LLt = np.asarray(LL, dtype=np.float64).reshape(tuple(int(x) for x in kdims.tolist()), order="F")
                    if isinstance(L, (int, float)) and float(L) == 0.0:
                        L = LLt.astype(np.float64)
                    else:
                        L = np.asarray(L, dtype=np.float64) + LLt

                sz_L = np.array(L.shape, dtype=np.int64)
                r = np.flatnonzero(sz_L > 1).astype(np.int64)
                if r.size == 0:
                    F[ti] = float(np.asarray(L, dtype=np.float64).reshape(-1)[0])
                else:
                    new_shape = tuple(int(sz_L[int(i)]) for i in r.tolist()) + (1, 1)
                    L = np.asarray(L, dtype=np.float64).reshape(new_shape, order="F")
                    Q_rt = _Q_factors_subset_bw(Q, mi, r, ti)
                    for dim_i in range(r.size):
                        loop_i = dim_i + 1
                        f_dim = int(r[dim_i]) + 1
                        LLln = spm_vec(spm_dot(L, Q_rt, loop_i))
                        ll_col = np.asarray(LLln, dtype=np.float64).reshape(-1, 1, order="F")
                        LPv = np.zeros_like(ll_col, dtype=np.float64)
                        if t_m == 1:
                            LPv = LPv + np.asarray(_spm_log(D[mi][f_dim - 1]), dtype=np.float64).reshape(-1, 1, order="F")
                        if t_m < T:
                            qbf = np.asarray(qb[mi][f_dim - 1], dtype=np.float64)
                            Pmft = P[mi][f_dim - 1][ti]
                            Qn = Q[mi][f_dim - 1][ti + 1]
                            tdot = spm_dot(spm_psi(tr(qbf)), Pmft)
                            LPv = LPv + _sdot_mtimes_q_bw(tdot, np.asarray(Qn, dtype=np.float64))
                        if t_m > 1:
                            qbf = np.asarray(qb[mi][f_dim - 1], dtype=np.float64)
                            Pprev = P[mi][f_dim - 1][ti - 1]
                            Qp = Q[mi][f_dim - 1][ti - 1]
                            tdot = spm_dot(spm_psi(qbf), Pprev)
                            LPv = LPv + _sdot_mtimes_q_bw(tdot, np.asarray(Qp, dtype=np.float64))

                        sm_arg = ll_col + LPv
                        Q[mi][f_dim - 1][ti] = spm_softmax(sm_arg)
                        q_post = np.asarray(Q[mi][f_dim - 1][ti], dtype=np.float64).reshape(-1, 1)
                        logq = _spm_log(q_post)
                        F[ti] = F[ti] + float(np.sum(q_post * (ll_col + LPv - logq)))

        nqb_path = _numel_qb_row_bw(qb, mi)
        for f_1 in range(1, nqb_path + 1):
            fi = f_1 - 1
            qbf_cell = np.asarray(qb[mi][fi], dtype=np.float64)
            Urow = np.asarray(U[mi], dtype=np.float64).ravel()
            if int(Urow[f_1 - 1]) != 0:
                for t_m in range(2, T + 1):
                    ti = t_m - 1
                    LLp = spm_vec(spm_dot(spm_dot(spm_psi(qbf_cell), Q[mi][fi][ti]), Q[mi][fi][ti - 1]))
                    LPp = _spm_log(P[mi][fi][ti - 1])
                    ll_p = np.asarray(LLp, dtype=np.float64).reshape(-1, 1, order="F")
                    lp_p = np.asarray(LPp, dtype=np.float64).reshape(-1, 1, order="F")
                    P[mi][fi][ti - 1] = spm_softmax(ll_p + lp_p)
                    p_post = np.asarray(P[mi][fi][ti - 1], dtype=np.float64).reshape(-1, 1)
                    logp = _spm_log(p_post)
                    F[ti] = F[ti] + float(np.sum(p_post * (ll_p + lp_p - logp)))
            else:
                LLacc = np.zeros((1, 1), dtype=np.float64)
                for t_m in range(2, T + 1):
                    ti = t_m - 1
                    term = spm_vec(spm_dot(spm_dot(spm_psi(qbf_cell), Q[mi][fi][ti]), Q[mi][fi][ti - 1]))
                    tcol = np.asarray(term, dtype=np.float64).reshape(-1, 1, order="F")
                    if LLacc.size == 1 and LLacc.reshape(-1)[0] == 0.0:
                        LLacc = tcol.copy()
                    else:
                        LLacc = LLacc + tcol
                LPp = _spm_log(E[mi][fi])
                lp_e = np.asarray(LPp, dtype=np.float64).reshape(-1, 1, order="F")
                PP = spm_softmax(LLacc + lp_e)
                for t_m in range(1, T + 1):
                    ti = t_m - 1
                    P[mi][fi][ti] = PP
                p_post = np.asarray(PP, dtype=np.float64).reshape(-1, 1)
                logp = _spm_log(p_post)
                for t_m in range(1, T + 1):
                    ti = t_m - 1
                    F[ti] = F[ti] + float(np.sum(p_post * (LLacc + lp_e - logp)))

        F_out = F.copy()
        dF = float(np.sum(F)) - float(Z)
        if float(np.sum(F)) > 0:
            warnings.warn("positive ELBO in spm_backwards", UserWarning, stacklevel=1)
        if dF < 1.0 / 128.0:
            break
        Z = float(np.sum(F))

    return Q, P, qa, qb, F_out


def _spm_log(a: Any) -> np.ndarray | Any:
    """Local ``spm_log`` (~2624–2631)."""
    if isinstance(a, np.ndarray) and a.dtype == bool:
        return (-32.0 * (~a)).astype(np.float64)
    arr = np.asarray(a, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        lx = np.real(np.log(arr.astype(np.complex128)))
    out = np.maximum(lx, -32.0)
    return np.asarray(out, dtype=np.float64)


def _spm_multiply(p: Any, q: Any) -> np.ndarray:
    """
    Local ``spm_multiply`` (~2603–2606): renormalised product of probability distributions.

    MATLAB: ``p = spm_softmax(spm_log(p) + spm_log(q));`` — **not** elementwise ``p.*q`` then normalise.
    Used in hierarchical child ``id.E`` / ``id.D`` empirical prior updates (~1063, ~1071).
    """
    pc = np.asarray(p, dtype=np.float64).reshape(-1, 1, order="F")
    qc = np.asarray(q, dtype=np.float64).reshape(-1, 1, order="F")
    lp = np.asarray(_spm_log(pc), dtype=np.float64)
    lq = np.asarray(_spm_log(qc), dtype=np.float64)
    return np.asarray(spm_softmax(lp + lq), dtype=np.float64)


def _spm_action(
    MDP: dict[str, Any],
    A: list[Any] | Any,
    Q_in: list[Any] | Any,
    t: int,
) -> dict[str, Any]:
    """
    Nested ``spm_action`` from ``spm_MDP_VB_XXX.m`` ~2688–2766.

    ``FORMAT MDP = spm_action(MDP,A,Q,t)`` — explicit control for generative process models.
    Call sites: hierarchical (~1087) passes ``A = mdp.A``, ``Q = mdp.D``, ``t = mdp.T``;
    main generation loop (~816) passes ``A(m,:)``, ``Q(m,:,t)``, ``t - 1`` (mapped here as
    ``bundle['A'][m]``, per-factor ``Q`` at timestep ``t_idx``, fourth arg ``t_idx`` when
    ``t_idx`` is the Python time index matching MATLAB ``t-1``).
    """
    id_m = MDP.get("id")
    if id_m is None:
        id_m = {}
        MDP["id"] = id_m

    id_upper = MDP.get("ID")
    if id_upper is None:
        id_upper = {}
        MDP["ID"] = id_upper

    if "control" not in id_upper:
        a_sizes = id_m.get("A", [])
        n_a = len(a_sizes) if isinstance(a_sizes, (list, tuple)) else int(np.size(np.asarray(a_sizes)))
        id_upper["control"] = [i + 1 for i in range(int(n_a))]

    if "chi" not in MDP:
        MDP["chi"] = 512.0
    chi = float(np.asarray(MDP["chi"], dtype=np.float64).ravel()[0])

    A_list = list(A) if isinstance(A, (list, tuple)) else [A]
    if isinstance(Q_in, np.ndarray) and Q_in.dtype == object:
        Q_list = list(Q_in.ravel(order="F"))
    elif isinstance(Q_in, (list, tuple)):
        Q_list = list(Q_in)
    else:
        Q_list = [Q_in]

    qo: dict[int, np.ndarray] = {}
    for g in id_upper["control"]:
        g_i = int(g)
        j_par, _ = spm_parents(id_m, g_i, Q_list)
        jv = np.atleast_1d(np.asarray(j_par)).ravel().astype(np.int64)
        q_cells = [Q_list[int(jj) - 1] for jj in jv.tolist()]
        qo[g_i] = np.asarray(spm_dot(A_list[g_i - 1], q_cells), dtype=np.float64).reshape(-1, 1)

    GB = MDP["GB"]
    GV = np.asarray(MDP["GV"], dtype=np.float64)
    if GV.ndim == 1:
        GV = GV.reshape(-1, 1)
    Na = int(GV.shape[0])
    Nf = len(GB)
    h = np.any(GV != 0.0, axis=0)
    F = np.zeros((Na, 1), dtype=np.float64)

    t_mat = int(t)
    t_col = t_mat - 1
    u_mat = np.asarray(MDP["u"], dtype=np.float64)
    if u_mat.ndim == 1:
        u_mat = u_mat.reshape(-1, 1)
    s_mat = np.asarray(MDP["s"], dtype=np.float64)
    if s_mat.ndim == 1:
        s_mat = s_mat.reshape(-1, 1)

    if "ff" in id_upper:
        ff_arr = np.atleast_1d(np.asarray(id_upper["ff"], dtype=np.int64)).ravel()
        ff_iter = [int(x) for x in ff_arr.tolist()]
    else:
        ff_iter = list(range(1, Nf + 1))

    for k in range(Na):
        u_work = u_mat[:, t_col].astype(np.float64).copy()
        u_work[h] = GV[k, h]
        qs_list: list[Any] = [None] * Nf
        for f in ff_iter:
            f0 = int(f) - 1
            s_ft = int(round(float(s_mat[f0, t_col])))
            u_f = int(round(float(u_work[f0])))
            Gb = np.asarray(GB[f0], dtype=np.float64)
            qs_list[f0] = Gb[:, s_ft - 1, u_f - 1].reshape(-1, 1)

        F[k, 0] = 0.0
        for g in id_upper["control"]:
            g_i = int(g)
            # MATLAB ~2753 uses ``spm_parents(MDP.ID, ...)``; likelihood indices live on ``id``.
            j_inner, _ = spm_parents(id_m, g_i, qs_list)
            jv2 = np.atleast_1d(np.asarray(j_inner)).ravel().astype(np.int64)
            for f in jv2.tolist():
                f0 = int(f) - 1
                s_ft = int(round(float(s_mat[f0, t_col])))
                u_f = int(round(float(u_work[f0])))
                Gb = np.asarray(GB[f0], dtype=np.float64)
                qs_list[f0] = Gb[:, s_ft - 1, u_f - 1].reshape(-1, 1)
            q_dot = [qs_list[int(jj) - 1] for jj in jv2.tolist()]
            GA_g = np.asarray(MDP["GA"][g_i - 1], dtype=np.float64)
            po = np.asarray(spm_dot(GA_g, q_dot), dtype=np.float64).reshape(-1, 1)
            qog = qo[g_i]
            F[k, 0] += float(np.asarray(qog, dtype=np.float64).ravel() @ np.asarray(_spm_log(po), dtype=np.float64).ravel())

    k_one = int(_spm_sample(np.asarray(spm_softmax(F, chi), dtype=np.float64).reshape(-1, 1)))
    k0 = k_one - 1
    u_out = u_mat.copy()
    u_out[h, t_col] = GV[k0, h]
    MDP["u"] = u_out
    return MDP


def _spm_norm_inplace(a: np.ndarray) -> np.ndarray:
    """MATLAB ``spm_norm`` (~2633–2639): column-normalise **in place** (returns same array)."""
    if a.size == 0 or (a.ndim >= 1 and int(a.shape[0]) == 0):
        return a
    s = np.sum(a, axis=0, keepdims=True)
    np.divide(a, s, out=a, where=s != 0)
    nan_m = np.isnan(a)
    if np.any(nan_m):
        a[nan_m] = 1.0 / int(a.shape[0])
    return a


def _spm_norm(a: Any) -> Any:
    """Local ``spm_norm`` (~2633–2639): column-normalise stochastic matrix (out-of-place)."""
    if sparse.issparse(a):
        a = np.asarray(mfull(a), dtype=np.float64)
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return a
    if a.size == 0 or (a.ndim >= 1 and int(a.shape[0]) == 0):
        return np.asarray(a, dtype=np.float64)
    work = np.asarray(a, dtype=np.float64)
    if not work.flags.writeable:
        work = work.copy(order="F")
    return _spm_norm_inplace(work)


def _spm_wnorm(a: Any) -> np.ndarray | Any:
    """Local ``spm_wnorm`` (~2641–2657)."""
    if sparse.issparse(a):
        a = np.asarray(mfull(a), dtype=np.float64)
    else:
        a = np.asarray(a, dtype=np.float64)
    if a.size == 0:
        return a
    if np.nanmin(np.max(a, axis=0)) >= 256:
        return np.array([])
    a0 = np.sum(a, axis=0, keepdims=True)
    term = np.log(a0) - np.log(a) + (1.0 / a - 1.0 / a0) + (digamma(a) - digamma(a0))
    out = np.maximum(term, 0.0)
    out = np.where(np.isnan(out), 0.0, out)
    return out


def _spm_one_hot(o: Any, no: int) -> np.ndarray:
    """File-local ``spm_one_hot`` from ``spm_MDP_VB_XXX.m`` (~2660): ``O(o)=1``, ``No×1``."""
    oi = int(round(float(o)))
    ni = int(no)
    if ni < 1:
        raise ValueError("spm_one_hot: No must be positive")
    if oi < 1 or oi > ni:
        raise ValueError(f"spm_one_hot: index {oi} out of range 1..{ni}")
    mat = sparse.csr_matrix(([1.0], ([oi - 1], [0])), shape=(ni, 1))
    return np.asarray(mat.toarray(), dtype=np.float64)


def _spm_hnorm(a: Any) -> np.ndarray | Any:
    """Local ``spm_hnorm`` (~2665–2676)."""
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return np.array([])
    n = _spm_norm(a)
    ent = np.sum(n * _spm_log(n), axis=0)
    ent = np.asarray(mfull(ent), dtype=np.float64).ravel()
    if not np.any(ent):
        return np.array([])
    return ent


def _default_options_vb() -> dict[str, Any]:
    """MATLAB ``try/catch`` defaults on ``OPTIONS.*`` (``spm_MDP_VB_XXX.m`` ~197–203)."""
    return {
        "B": 0,
        "C": 0,
        "D": 0,
        "N": 0,
        "O": 1,
        "P": 0,
        "Y": 1,
    }


def _merge_options_vb(options: Any | None) -> dict[str, Any]:
    if options is None:
        return _default_options_vb()
    if not isinstance(options, dict):
        raise TypeError("OPTIONS must be a dict or None")
    out = _default_options_vb()
    out.update(options)
    return out


def _vb_has_multiple_epoch_columns(mdp_in: Any) -> bool:
    """True when MATLAB ``size(MDP,2) > 1`` (multi-trial loop; ``spm_MDP_VB_XXX.m`` ~212)."""
    if isinstance(mdp_in, list) and mdp_in and isinstance(mdp_in[0], list):
        return len(mdp_in[0]) > 1
    return False


def _spm_is_process(mdp: dict) -> bool:
    """Local ``spm_is_process`` (~2608–2611)."""
    return all(k in mdp for k in ("GA", "GB", "GU"))


def _vb_models_after_checkx(mdp_checked: Any) -> list[dict]:
    """MATLAB ``MDP(m)`` as a list of model dicts."""
    if isinstance(mdp_checked, dict):
        return [mdp_checked]
    if isinstance(mdp_checked, list) and mdp_checked and isinstance(mdp_checked[0], list):
        col: list[dict] = []
        for row in mdp_checked:
            if len(row) != 1:
                raise ValueError(
                    "spm_MDP_VB_XXX: expected exactly one epoch column from spm_MDP_checkX"
                )
            col.append(row[0])
        return col
    raise TypeError("spm_MDP_VB_XXX: unexpected layout returned by spm_MDP_checkX")


def _try_mdp_scalar(mdp: dict, name: str, default: float | int) -> float | int:
    """MATLAB ``try, MDP(1).field; catch, default; end``."""
    if name not in mdp:
        return default
    v = mdp[name]
    if v is None:
        return default
    if isinstance(default, bool):
        return bool(v)
    if isinstance(default, int) and not isinstance(default, bool):
        return int(np.asarray(v).reshape(-1)[0])
    return float(np.asarray(v).reshape(-1)[0])


def _vb_hyperparameters_mdp1(m1: dict) -> dict[str, Any]:
    """MATLAB defaults ~285–289."""
    return {
        "alpha": float(_try_mdp_scalar(m1, "alpha", 512.0)),
        "beta": float(_try_mdp_scalar(m1, "beta", 0.0)),
        "chi": float(_try_mdp_scalar(m1, "chi", 512.0)),
        "eta": float(_try_mdp_scalar(m1, "eta", 512.0)),
        "N": int(_try_mdp_scalar(m1, "N", 0)),
    }


def _vb_coerce_U_dense(U_raw: Any) -> np.ndarray:
    """``MDP.U`` / ``GP.U`` may be ``csr_matrix`` after assemble (~1694 ``U``←``V``); coerce for numeric ops."""
    if U_raw is None:
        return np.zeros((0, 0), dtype=np.float64)
    if sparse.issparse(U_raw):
        U_raw = U_raw.toarray()
    return np.asarray(U_raw, dtype=np.float64)


def _vb_mdp_U_as_float_array(md: dict[str, Any]) -> np.ndarray:
    """See ``_vb_coerce_U_dense``."""
    return _vb_coerce_U_dense(md["U"])


def _unwrap_id_a_entry(id_a_g: Any) -> Any:
    """MATLAB ``id.A{g}`` may be wrapped ``{1}`` in Python."""
    if isinstance(id_a_g, (list, tuple)) and len(id_a_g) == 1:
        return id_a_g[0]
    return id_a_g


def _b_nu_third_dim(Bg: Any) -> int:
    """MATLAB ``size(B{f},3)`` including trailing singleton omitted in NumPy."""
    arr = np.asarray(Bg)
    if arr.ndim >= 3:
        return int(arr.shape[2])
    return 1


def _numel_like_matlab(x: Any) -> int:
    """MATLAB ``numel`` for tensor / None."""
    if x is None:
        return 0
    return int(np.asarray(x).size)


def _vb_id_and_policy_blocks(
    *,
    nm: int,
    models: list[dict],
    Ng: np.ndarray,
    Nf: np.ndarray,
    NF: np.ndarray,
    NU: np.ndarray,
    Nu: np.ndarray,
    K_t: list[list[Any]],
    W_t: list[list[Any]],
    H_t: list[list[Any]],
    I_t: list[list[Any]],
    gp: list[dict[str, Any]],
    id_list: list[dict[str, Any]],
    ID_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    MATLAB ~597–652: ``id`` bookkeeping, ``GV`` / ``V`` via ``spm_combinations``,
    ``fu`` / ``fp`` indices.
    """
    GV_rows: list[sparse.csr_matrix] = []
    V_rows: list[sparse.csr_matrix] = []
    GU_rows: list[np.ndarray] = []
    U_dom_rows: list[np.ndarray] = []
    Na = np.zeros(nm, dtype=np.int64)
    Np = np.zeros(nm, dtype=np.int64)

    for m in range(nm):
        md = models[m]
        gpm = gp[m]
        ng_m = int(Ng[m])
        nf_m = int(Nf[m])
        idm = id_list[m]
        IDm = ID_list[m]

        if "control" not in IDm:
            IDm["control"] = np.arange(1, ng_m + 1, dtype=np.int64)

        ik = np.zeros(ng_m, dtype=np.int64)
        iw = np.zeros(ng_m, dtype=np.int64)
        for g_idx in range(ng_m):
            ik[g_idx] = _numel_like_matlab(K_t[m][g_idx])
            iw[g_idx] = _numel_like_matlab(W_t[m][g_idx])
        idm["iK"] = (np.flatnonzero(ik) + 1).astype(np.int64)
        idm["iW"] = (np.flatnonzero(iw) + 1).astype(np.int64)

        ih = np.zeros(nf_m, dtype=np.int64)
        ii = np.zeros(nf_m, dtype=np.int64)
        for f_idx in range(nf_m):
            ih[f_idx] = _numel_like_matlab(H_t[m][f_idx])
            ii[f_idx] = _numel_like_matlab(I_t[m][f_idx])
        idm["iH"] = (np.flatnonzero(ih) + 1).astype(np.int64)
        idm["iI"] = (np.flatnonzero(ii) + 1).astype(np.int64)

        nf_m_gp = int(NF[m])
        Ugp = _vb_coerce_U_dense(gpm["U"])
        if Ugp.ndim == 1:
            Ugp = Ugp.reshape(1, -1)
        GU_row = np.zeros(nf_m_gp, dtype=bool)
        if Ugp.size and nf_m_gp > 0:
            nc = min(int(Ugp.shape[1]), nf_m_gp)
            GU_row[:nc] = np.any(Ugp[:, :nc] != 0, axis=0)
        GU_rows.append(GU_row.astype(np.float64))
        k_gp = np.flatnonzero(GU_row) + 1
        if k_gp.size == 0:
            u_gen = np.zeros((0, 0), dtype=np.float64)
        else:
            nu_sel = NU[m, k_gp - 1].astype(np.int64).ravel()
            u_gen = spm_combinations(nu_sel)
        nug = int(u_gen.shape[0])
        GV = sparse.lil_matrix((nug, nf_m_gp))
        if u_gen.size and k_gp.size:
            for j, kf in enumerate(k_gp):
                GV[:, int(kf) - 1] = u_gen[:, j : j + 1]
        GV_csr = GV.tocsr()
        GV_rows.append(GV_csr)
        Na[m] = GV_csr.shape[0]

        U_md = _vb_mdp_U_as_float_array(md)
        if U_md.ndim == 1:
            U_md = U_md.reshape(1, -1)
        U_dom = np.zeros(nf_m, dtype=bool)
        if U_md.size and nf_m > 0:
            nc_u = min(int(U_md.shape[1]), nf_m)
            U_dom[:nc_u] = np.any(U_md[:, :nc_u] != 0, axis=0)
        U_dom_rows.append(U_dom.astype(np.float64))
        k_ld = np.flatnonzero(U_dom) + 1
        if k_ld.size == 0:
            u_lat = np.zeros((0, 0), dtype=np.float64)
        else:
            nu_lat = Nu[m, k_ld - 1].astype(np.int64).ravel()
            u_lat = spm_combinations(nu_lat)
        nvl = int(u_lat.shape[0])
        V = sparse.lil_matrix((nvl, nf_m))
        if u_lat.size and k_ld.size:
            for j, kf in enumerate(k_ld):
                V[:, int(kf) - 1] = u_lat[:, j : j + 1]

        if "V" in md:
            V_src = md["V"]
            if sparse.issparse(V_src):
                V = V_src.tocsr()
            else:
                V = sparse.csr_matrix(np.asarray(V_src, dtype=np.float64))
            Vd = V.toarray()
            U_dom = np.any(Vd != 0, axis=0)
            if U_dom.size < nf_m:
                pad = np.zeros(nf_m, dtype=bool)
                pad[: U_dom.size] = U_dom
                U_dom = pad
            elif U_dom.size > nf_m:
                U_dom = U_dom[:nf_m]
            U_dom_rows[m] = U_dom.astype(np.float64)

        V_csr = V.tocsr() if sparse.issparse(V) else sparse.csr_matrix(V)
        V_rows.append(V_csr)
        Np[m] = V_csr.shape[0]

        vd = V_csr.toarray()
        idm["fu"] = (np.flatnonzero(np.any(vd != 0, axis=0)) + 1).astype(np.int64)
        idm["fp"] = (np.flatnonzero(~np.any(vd != 0, axis=0)) + 1).astype(np.int64)
        gvd = GV_csr.toarray()
        IDm["fu"] = (np.flatnonzero(np.any(gvd != 0, axis=0)) + 1).astype(np.int64)
        IDm["fp"] = (np.flatnonzero(~np.any(gvd != 0, axis=0)) + 1).astype(np.int64)

    return {
        "GV": GV_rows,
        "V": V_rows,
        "GU": GU_rows,
        "Um": U_dom_rows,
        "Na": Na,
        "Np": Np,
    }


def _vb_mdp_field_matrix(md: dict[str, Any], key: str, n_rows: int, t_int: int) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~705–730: ``k = zeros(...); i = find(MDP.s); k(i)=MDP.s(i);``.

    Column-major linear indexing (MATLAB ``find`` / ``(:)``). Hierarchical prep sets
    ``mdp.s`` / ``mdp.u`` as ``nf×1`` vectors; ``find`` + ``k(i)=s(i)`` fills the
    leading column of ``zeros(NF,T)`` without resampling at generation time.
    """
    # Fortran-ordered so ``ravel(order='F')`` is a view (C-order ``ravel('F')`` copies).
    k = np.zeros((n_rows, t_int), dtype=np.float64, order="F")
    k_flat = k.ravel(order="F")
    try:
        if key not in md or md[key] is None:
            md[key] = k
            return
        s = np.asarray(md[key], dtype=np.float64)
        if s.size == 0:
            md[key] = k
            return
        s_lin = s.ravel(order="F")
        if s_lin.size == n_rows * t_int:
            idx = np.flatnonzero(s_lin)
            k_flat[idx] = s_lin[idx]
        else:
            idx = np.flatnonzero(s_lin)
            if idx.size:
                valid = idx[idx < k_flat.size]
                if valid.size:
                    k_flat[valid] = s_lin[valid]
    except Exception:
        pass
    md[key] = k


def _vb_mdp_O_is_cell_gt_layout(O_field: Any, ng: int, t_int: int) -> bool:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` init block ~732–752.

    MATLAB only enters ``O{m,g,t} = MDP(m).O{g,t}`` when curly indexing works (~741). A dense
    ``mdp.O`` matrix from hierarchical ``mdp.S(:,seg)`` (~1189–1191) does **not** support
    ``O{g,t}``; each ``(g,t)`` hits ``catch`` (~747–748) and leaves ``O{m,g,t} = []`` (~748).
    Do not mirror that with ``O_field[g,:]`` row reads on a numeric matrix (Pass 1 bug).
    """
    if isinstance(O_field, list) and O_field:
        return isinstance(O_field[0], (list, tuple)) and int(len(O_field)) == int(ng)
    if isinstance(O_field, np.ndarray) and O_field.dtype == object:
        sh = O_field.shape
        return len(sh) >= 2 and int(sh[0]) == int(ng)
    return False


def _get_mdp_O_gt(O_field: Any, g_idx: int, t_idx: int) -> Any:
    """MATLAB ``MDP.O{g,t}`` with zero-based ``g_idx``, ``t_idx``."""
    if isinstance(O_field, np.ndarray) and O_field.dtype == object:
        return O_field[g_idx, t_idx]
    row = O_field[g_idx]
    if isinstance(row, (list, tuple)):
        return row[t_idx]
    arr = np.asarray(row)
    if arr.ndim == 0:
        return arr.item()
    return arr[t_idx]


def _mode_matlab_dim1(arr: np.ndarray) -> np.ndarray:
    """MATLAB ``mode(A,1)``: mode along rows, length ``size(A,2)``."""
    a = np.asarray(arr, dtype=np.float64)
    if a.size == 0:
        return np.zeros((0,), dtype=np.float64)
    res = stats.mode(a, axis=0, keepdims=False)
    mo = res.mode
    return np.asarray(mo, dtype=np.float64).ravel()


def _spm_MDP_get_M(
    models: list[dict[str, Any]],
    t_int: int,
    Ng: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """
    Local ``spm_MDP_get_M`` from ``spm_MDP_VB_XXX.m`` (~2769–2819).

    Returns ``M`` with shape ``(T, Nm)`` — MATLAB ``M(t,:)`` is 1-based agent order per time.
    Mutates each ``models[m]['n']`` to ``Ng[m]``×``T``.
    """
    nm = len(models)
    n_acc = np.zeros((nm, t_int), dtype=np.float64)
    for m in range(nm):
        md = models[m]
        ng_m = int(Ng[m])
        if "n" not in md or md["n"] is None:
            md["n"] = np.zeros((ng_m, t_int), dtype=np.float64)
        else:
            arr = np.asarray(md["n"], dtype=np.float64)
            if arr.size == 0:
                md["n"] = np.zeros((ng_m, t_int), dtype=np.float64)
            else:
                if arr.ndim == 0:
                    arr = arr.reshape(1, 1)
                elif arr.ndim == 1:
                    arr = arr.reshape(1, -1)
                nr, nc = int(arr.shape[0]), int(arr.shape[1])
                if nr < ng_m:
                    arr = np.tile(arr[0:1, :], (ng_m, 1))
                if nc < t_int:
                    arr = np.tile(arr[:, 0:1], (1, t_int))
                md["n"] = arr

        n_mat = np.asarray(md["n"], dtype=np.float64)
        masked = n_mat * (n_mat > 0.0)
        n_acc[m, :] = _mode_matlab_dim1(masked)

    n_global = _mode_matlab_dim1(n_acc)
    if n_global.size < t_int:
        pad = np.zeros(t_int, dtype=np.float64)
        pad[: n_global.size] = n_global
        n_global = pad

    M = np.zeros((t_int, nm), dtype=np.int64)
    idx1 = np.arange(1, nm + 1, dtype=np.int64)
    for t in range(t_int):
        nt = float(n_global[t])
        if nt > 0.0:
            M[t, :] = np.roll(idx1, int(1 - nt))
        else:
            M[t, :] = idx1

    return M, models


def _vb_prealloc_BP_IP(bundle: dict[str, Any]) -> tuple[list, list]:
    """
    MATLAB ~742–743: ``BP = cell(Nm, Nf(m), Np(m));`` with ``m = Nm`` (value of ``m`` after ``for m=1:Nm``).

    When ``Np(m)==0``, MATLAB's cell still supports ``BP{m,f,1}`` on the uncontrolled
    factors branch (~1243–1249); allocate at least one slot in the policy dimension so
    ``BP[..., 0]`` / ``IP[..., 0]`` writes do not index an empty list.
    """
    nm = int(bundle["Nm"])
    m_last = nm - 1
    nf = int(bundle["Nf"][m_last])
    npp = int(bundle["Np"][m_last])
    npp_shell = max(1, npp)
    empty = np.array([], dtype=np.float64)
    BP = [[[empty for _ in range(npp_shell)] for _ in range(nf)] for _ in range(nm)]
    IP = [[[empty for _ in range(npp_shell)] for _ in range(nf)] for _ in range(nm)]
    return BP, IP


def _vb_policy_depth_and_get_M(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """MATLAB ~737–743: ``N = min(N,T)``, ``spm_MDP_get_M``, ``BP``/``IP`` shells."""
    t_int = int(bundle["T"])
    n_mdp = int(hp["N"])
    n_depth = int(min(n_mdp, t_int))
    M_upd, _ = _spm_MDP_get_M(models, t_int, bundle["Ng"])
    BP, IP = _vb_prealloc_BP_IP(bundle)
    nm = int(bundle["Nm"])
    Np_arr = bundle["Np"]
    # MATLAB ``R{m}(:,t) = spm_softmax(G)`` can grow a 1-row ``R`` when ``Np(m)==0`` (``BP{m,f,1}`` path).
    R_policy = [np.zeros((max(1, int(Np_arr[m])), t_int), dtype=np.float64) for m in range(nm)]
    w_policy = [np.zeros(t_int, dtype=np.float64) for _ in range(nm)]
    v_policy = [np.zeros(t_int, dtype=np.float64) for _ in range(nm)]
    return {
        "N_policy_depth": n_depth,
        "M_update": M_upd,
        "BP": BP,
        "IP": IP,
        "R_policy": R_policy,
        "w_policy": w_policy,
        "v_policy": v_policy,
    }


def _unwrap_gp_elem(x: Any) -> Any:
    """Single-element MATLAB cell wrapper → inner array."""
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _vb_gp_A_outcome_column(Ag: np.ndarray, ind_parts: list[int]) -> np.ndarray:
    """
    ``GP(m).A{g}(:, ind{:})`` (~961–967): column-major outcome vector for parent states ``s(j,t)``.

    ``ind_parts`` are 0-based state indices (from MATLAB 1-based ``num2cell(s(j,t))``).
    """
    if Ag.ndim == 2 and len(ind_parts) == 1:
        col = np.asarray(Ag[:, ind_parts[0]], dtype=np.float64)
    else:
        ind_tup = tuple(ind_parts)
        col = np.asarray(Ag[(slice(None),) + ind_tup], dtype=np.float64)
    return col.reshape(-1, 1, order="F")


def _vb_gp_transition_column(Bg: Any, s_1based: int, u_1based: int) -> np.ndarray:
    """MATLAB ``GP.B{f}(:, s, u)`` with 1-based indices; column ``Ns×1``."""
    Barr = np.asarray(_unwrap_gp_elem(Bg), dtype=np.float64)
    if Barr.ndim == 2:
        Barr = Barr[:, :, np.newaxis]
    nu_third = int(Barr.shape[2])
    if nu_third == 0:
        ns = int(Barr.shape[0])
        return np.zeros((max(ns, 1), 1), dtype=np.float64)
    si = max(0, min(int(s_1based) - 1, int(Barr.shape[1]) - 1))
    ui = max(0, min(int(u_1based) - 1, nu_third - 1))
    col = Barr[:, si, ui]
    return np.asarray(col.reshape(-1, 1), dtype=np.float64)


def _vb_gen_u_paths_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """MATLAB ~756–775: GP path dimension ``NF``."""
    md = models[mi]
    gpm = bundle["gp"][mi]
    nf_gp = int(bundle["NF"][mi])
    for f_idx in range(nf_gp):
        if float(md["u"][f_idx, t_idx]) != 0.0:
            continue
        if t_idx > 0:
            md["u"][f_idx, t_idx] = float(md["u"][f_idx, t_idx - 1])
        else:
            Ef = _unwrap_gp_elem(gpm["E"][f_idx])
            pu = _spm_norm(Ef)
            if int(np.asarray(pu).size) == 0:
                continue
            md["u"][f_idx, t_idx] = float(_spm_sample(pu))


def _vb_prior_QP_paths_states_one_model(
    mi: int,
    bundle: dict[str, Any],
    t_idx: int,
    Pu_vec: np.ndarray,
) -> None:
    """MATLAB ~779–804: policy sample ``Pu``, update ``P`` / ``Q`` over **generative** ``Nf`` factors."""
    Um = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
    vd = bundle["V"][mi].toarray()
    nf_gen = int(bundle["Nf"][mi])
    Nu_m = bundle["Nu"]
    Q_all = bundle["Q"]
    P_all = bundle["P"]
    B_t = bundle["B"]

    pu_col = np.asarray(Pu_vec, dtype=np.float64).reshape(-1, 1)
    if pu_col.size == 0:
        # ``Np==0``: MATLAB ``Pu = spm_softmax(G,alpha)`` is ``1×1``; ``spm_sample(Pu)`` still draws.
        pu_col = np.ones((1, 1), dtype=np.float64)
    k_pol = int(_spm_sample(pu_col))

    for f_idx in range(nf_gen):
        if f_idx < Um.size and float(Um[f_idx]) != 0.0:
            if vd.shape[0] == 0:
                continue
            u_mark = int(round(float(vd[k_pol - 1, f_idx])))
            P_arr = np.asarray(P_all[mi][f_idx][t_idx - 1], dtype=np.float64).ravel()
            P_arr[:] = 0.0
            if 1 <= u_mark <= P_arr.size:
                P_arr[u_mark - 1] = 1.0
            P_all[mi][f_idx][t_idx - 1] = P_arr.reshape(-1, 1)

        nu_mf = int(Nu_m[mi, f_idx])
        Q_prev = np.asarray(Q_all[mi][f_idx][t_idx - 1], dtype=np.float64)
        Bmf = B_t[mi][f_idx]
        if nu_mf > 1:
            P_prev = P_all[mi][f_idx][t_idx - 1]
            # ``spm_dot(B,P)`` with vector ``P`` contracts the first matching size (here ``ns``);
            # path belief needs last-axis contraction — MATLAB cell form ``{P}`` (~``spm_dot.m``).
            tp = np.asarray(spm_dot(Bmf, [P_prev]), dtype=np.float64)
            Q_new = tp @ Q_prev
        else:
            Bm = np.asarray(_unwrap_gp_elem(Bmf), dtype=np.float64)
            Q_new = Bm @ Q_prev
        Q_all[mi][f_idx][t_idx] = Q_new

    bundle["_entry12_last_k_pol"] = k_pol
    bundle["_entry12_last_Pu"] = pu_col


def _vb_gen_control_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """MATLAB ~806–827: ``spm_action`` (process) or sample ``u(:,t-1)`` from ``P`` (implicit)."""
    md = models[mi]
    if float(bundle["process"][mi]) > 0.0:
        if "GV" not in md:
            raise NotImplementedError(
                "spm_MDP_VB_XXX: process model without GV (nested spm_action requires GV)"
            )
        t_int = int(bundle["T"])
        nf = int(bundle["Nf"][mi])
        A_list = bundle["A"][mi]
        Q_all = bundle["Q"]
        Q_slice = [Q_all[mi][f][t_idx] for f in range(nf)]
        nf_gp = len(md["GB"])
        for key, fill in (("u", 1.0), ("s", 1.0)):
            if key not in md or md[key] is None:
                md[key] = np.full((nf_gp, t_int), fill, dtype=np.float64)
            else:
                arr = np.asarray(md[key], dtype=np.float64)
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)
                if arr.shape[0] < nf_gp:
                    arr = np.vstack(
                        [arr, np.full((nf_gp - arr.shape[0], arr.shape[1]), fill, dtype=np.float64)]
                    )
                if arr.shape[1] < t_int:
                    arr = np.hstack(
                        [arr, np.full((arr.shape[0], t_int - arr.shape[1]), fill, dtype=np.float64)]
                    )
                md[key] = arr
        # Fourth argument: MATLAB ``t-1`` with loop ``t`` = ``t_idx + 1`` → pass ``t_idx``.
        _spm_action(md, A_list, Q_slice, t_idx)
        return
    idm = bundle["id"][mi]
    P_all = bundle["P"]
    fu = np.asarray(idm.get("fu", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    for f_1 in fu:
        f_idx = int(f_1) - 1
        md["u"][f_idx, t_idx - 1] = float(_spm_sample(P_all[mi][f_idx][t_idx - 1]))


def _vb_gen_states_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """MATLAB ~830–851: sample ``s`` from ``GP``; ``NF`` factors."""
    md = models[mi]
    gpm = bundle["gp"][mi]
    nf_gp = int(bundle["NF"][mi])
    for f_idx in range(nf_gp):
        if float(md["s"][f_idx, t_idx]) != 0.0:
            continue
        if t_idx > 0:
            Bg = gpm["B"][f_idx]
            su = int(round(float(md["s"][f_idx, t_idx - 1])))
            uu = int(round(float(md["u"][f_idx, t_idx - 1])))
            ps = _vb_gp_transition_column(Bg, su, uu)
        else:
            Df = _unwrap_gp_elem(gpm["D"][f_idx])
            ps = _spm_norm(Df)
        md["s"][f_idx, t_idx] = float(_spm_sample(ps))


def _vb_generation_paths_states(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~756–920 (per ``t``, before share-states ~934).

    Order per model: **u** (``NF``) → if ``t>1``: **Pu**/**Q**/**P**, **control** → **s** (``NF``).
    """
    nm = int(bundle.get("Nm", len(models)))
    bundle.setdefault("Pu_carry", [None] * nm)
    Pu_carry: list[Any] = bundle["Pu_carry"]

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        _vb_gen_u_paths_one_model(mi, models, bundle, t_idx)
        if t_idx > 0:
            # MATLAB ~823: ``k = spm_sample(Pu)`` whenever ``t > 1`` (no guard on Pu defined).
            pu_v = Pu_carry[mi]
            if pu_v is None:
                npp = int(bundle["Np"][mi])
                pu_v = np.ones((max(1, npp), 1), dtype=np.float64)
            _vb_prior_QP_paths_states_one_model(mi, bundle, t_idx, np.asarray(pu_v, dtype=np.float64))
            if _vb_dump_active():
                k_pol = int(bundle.get("_entry12_last_k_pol", 1))
                pu_rec = np.asarray(bundle.get("_entry12_last_Pu", pu_v), dtype=np.float64)
                _entry12_record_phase(
                    mi,
                    t_idx + 1,
                    "post_generation",
                    bundle,
                    extra={
                        "k_policy": k_pol,
                        "Pu": _vb_as_float64_array(pu_rec).ravel().tolist(),
                    },
                )
            _vb_gen_control_one_model(mi, models, bundle, t_idx)
        _vb_gen_states_one_model(mi, models, bundle, t_idx)


def _vb_share_states_one_t(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """MATLAB ``spm_MDP_VB_XXX.m`` ~934–945 (share states via ``MDP.m``)."""
    NF_arr = bundle["NF"]
    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        if "m" not in md:
            continue
        m_src = np.asarray(md["m"], dtype=np.float64).ravel()
        nf_gp = int(NF_arr[mi])
        for f_idx in range(min(nf_gp, int(m_src.size))):
            n_agent = int(round(float(m_src[f_idx])))
            if n_agent > 0:
                md["s"][f_idx, t_idx] = float(models[n_agent - 1]["s"][f_idx, t_idx])


def _vb_generation_paths_states_share(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """Generation (~756–920) then share-states (~934–945). Outcomes (~873+) are separate."""
    _vb_generation_paths_states(models, bundle, t_idx, M_row)
    _vb_share_states_one_t(models, bundle, t_idx, M_row)


def _tensor_nonempty(x: Any) -> bool:
    """MATLAB ``numel(X) > 0``."""
    if x is None:
        return False
    return bool(np.asarray(x).size > 0)


def _vb_fill_BP_IP_at_t(bundle: dict[str, Any], t_idx: int) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1224–1256: belief propagators ``BP`` / ``IP`` from ``B``, ``I``, ``V``, ``P``.

    Uses generative-model factors ``Nf``, ``Um``, ``Nu``, policy matrix ``V``, and ``P{m,f,t}``.
    """
    nm = int(bundle["Nm"])
    Nf = bundle["Nf"]
    Nu = bundle["Nu"]
    Um_list = bundle["Um"]
    V_list = bundle["V"]
    B_t = bundle["B"]
    I_t = bundle["I"]
    P_all = bundle["P"]
    BP = bundle["BP"]
    IP = bundle["IP"]
    Np = bundle["Np"]

    for m in range(nm):
        nf_m = int(Nf[m])
        npp = int(Np[m])
        Um = np.asarray(Um_list[m], dtype=np.float64).ravel()
        V_csr = V_list[m]
        vd = V_csr.toarray()

        for f_idx in range(nf_m):
            controllable = f_idx < Um.size and float(Um[f_idx]) != 0.0
            Bmf = _unwrap_gp_elem(B_t[m][f_idx])
            Imf = I_t[m][f_idx]

            if controllable:
                Barr = np.asarray(Bmf, dtype=np.float64)
                if Barr.ndim == 2:
                    Barr = Barr[:, :, np.newaxis]
                Iarr = None
                if _tensor_nonempty(Imf):
                    Iarr = np.asarray(_unwrap_gp_elem(Imf), dtype=np.float64)
                    if Iarr.ndim == 2:
                        Iarr = Iarr[:, :, np.newaxis]
                for k in range(npp):
                    u_sel = int(round(float(vd[k, f_idx])))
                    if u_sel < 1:
                        u_sel = 1
                    nu_third = Barr.shape[2]
                    if u_sel > nu_third:
                        u_sel = nu_third
                    BP[m][f_idx][k] = np.asarray(Barr[:, :, u_sel - 1], dtype=np.float64)
                    if Iarr is not None:
                        IP[m][f_idx][k] = np.asarray(Iarr[:, :, u_sel - 1], dtype=np.float64)
            else:
                Pmf_t = P_all[m][f_idx][t_idx]
                if int(Nu[m, f_idx]) > 1:
                    BP[m][f_idx][0] = spm_dot(Bmf, [Pmf_t])
                    if _tensor_nonempty(Imf):
                        dotted = spm_dot(Imf, [Pmf_t])
                        for k in range(npp):
                            IP[m][f_idx][k] = dotted
                else:
                    BP[m][f_idx][0] = np.asarray(Bmf, dtype=np.float64)
                    if _tensor_nonempty(Imf):
                        Imf_u = _unwrap_gp_elem(Imf)
                        for k in range(npp):
                            IP[m][f_idx][k] = np.asarray(Imf_u, dtype=np.float64)


def _vb_fill_O_empty_from_realized_o(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    mi: int,
) -> None:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~973–979 (``o`` already set, ``O`` empty).

    ``isempty(O{m,o,t})`` → ``spm_one_hot(MDP(m).o(o,t), No(m,o))``. Band **12E**:
    ``_vb_generate_outcomes_if_options_o`` (~2541–2548); seam before **12F**:
    ``_vb_fill_O_empty_from_realized_o_at_t``.
    """
    md = models[mi]
    O_m = bundle["O"][mi]
    ng_m = len(O_m)
    for o_idx in range(ng_m):
        if _tensor_nonempty(O_m[o_idx][t_idx]):
            continue
        if float(md["o"][o_idx, t_idx]) == 0.0:
            continue
        no_mo = int(bundle["No"][mi, o_idx])
        oi = int(round(float(md["o"][o_idx, t_idx])))
        if no_mo > 0 and 0 < oi <= no_mo:
            O_m[o_idx][t_idx] = _spm_one_hot(oi, no_mo)


def _vb_fill_O_empty_from_realized_o_at_t(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """Band **12E → 12F** seam: apply ~977–978 for every active model before belief / ``spm_forwards``."""
    for mm in np.asarray(M_row, dtype=np.int64).ravel():
        mi = int(mm) - 1
        if mi >= 0:
            _vb_fill_O_empty_from_realized_o(models, bundle, t_idx, mi)


def _vb_ensure_per_t_traces(models: list[dict[str, Any]], mi: int, t_int: int) -> None:
    """Preallocate MATLAB-like ``MDP(m).F(t)``, ``G{t}``, ``Z(t)`` slots (length ``T``)."""
    md = models[mi]
    gg = md.get("G")
    if gg is None or not isinstance(gg, list):
        md["G"] = [None] * t_int
    elif len(gg) < t_int:
        md["G"] = list(gg) + [None] * (t_int - len(gg))
    # Do not shrink ``G`` when checkX left a longer structural cell row (MATLAB keeps ``1×4`` with ``T=2``).
    ff = md.get("F")
    if ff is None or (not isinstance(ff, np.ndarray)) or (int(ff.size) != t_int):
        md["F"] = np.zeros((t_int,), dtype=np.float64)
    zz = md.get("Z")
    if zz is None or (not isinstance(zz, np.ndarray)) or (int(zz.size) != t_int):
        md["Z"] = np.zeros((t_int,), dtype=np.float64)


def _vb_in_loop_id_ig_and_sn(
    mi: int,
    bundle: dict[str, Any],
    t_idx: int,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1418–1431 (after ``F``/``G``/``Z`` logging): ``id.ig`` and ``sn`` when
    ``OPTIONS.N``.
    """
    t_int = int(bundle["T"])
    id_m = bundle["id"][mi]
    if "i" in id_m:
        if "ig" not in id_m or id_m["ig"] is None:
            id_m["ig"] = np.zeros((t_int,), dtype=np.float64)
        else:
            ig0 = np.asarray(id_m["ig"], dtype=np.float64).ravel()
            if ig0.size < t_int:
                id_m["ig"] = np.concatenate([ig0, np.zeros(t_int - ig0.size, dtype=np.float64)])
            else:
                id_m["ig"] = ig0[:t_int].copy()
        iv = np.asarray(id_m["i"], dtype=np.float64).ravel()
        id_m["ig"][t_idx] = float(iv[0]) if iv.size > 0 else 0.0

    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("N", 0)) == 0:
        return
    sn_all = bundle.get("sn")
    if sn_all is None:
        return
    for f_idx in range(int(bundle["Nf"][mi])):
        snmf = sn_all[mi][f_idx]
        if snmf is None:
            continue
        ns = int(snmf.shape[0])
        for ii in range(t_int):
            q_src = np.asarray(bundle["Q"][mi][f_idx][ii], dtype=np.float64).reshape(-1)
            if ns <= 0:
                continue
            take = min(ns, int(q_src.size))
            if take <= 0:
                continue
            snmf[:take, ii, t_idx] = q_src[:take]
            if take < ns:
                snmf[take:, ii, t_idx] = 0.0


def _vb_trim_mdp_o_s_u_at_terminal_horizon(models: list[dict[str, Any]], bundle: dict[str, Any]) -> None:
    """MATLAB ``spm_MDP_VB_XXX.m`` ~1438–1443 when ``t == T``: keep first ``T`` outcome/state/control columns."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    Ng = bundle["Ng"]
    NF = bundle["NF"]
    for mi in range(nm):
        md = models[mi]
        ng_m = int(Ng[mi])
        nf_m = int(NF[mi])
        for key, n_rows in (("o", ng_m), ("s", nf_m), ("u", nf_m)):
            if key not in md:
                continue
            arr = np.asarray(md[key], dtype=np.float64)
            if arr.ndim < 2:
                continue
            if arr.shape[1] > t_int:
                md[key] = np.asarray(arr[:, :t_int], dtype=np.float64).copy()


def _vb_active_learning_in_loop(
    mi: int,
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    t_m: int,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1349–1409: online Dirichlet updates for ``a`` / ``b`` after
    control priors and **before** ``MDP(m).F(t)``/``G``/``Z`` logging (~1412–1416).
    """
    md = models[mi]
    id_m = bundle["id"][mi]
    nf_m = int(bundle["Nf"][mi])
    O_m = bundle["O"][mi]
    Q_row: list[Any] = [bundle["Q"][mi][f][t_idx] for f in range(nf_m)]

    if "a" in md:
        for g_1 in np.ravel(spm_children(id_m)).astype(np.int64):
            g_idx = int(g_1) - 1
            if g_idx < 0:
                continue
            jdom, kcod = spm_parents(id_m, int(g_1), Q_row)
            k_flat = np.atleast_1d(np.asarray(kcod, dtype=np.float64).ravel()).astype(np.int64).ravel()
            if k_flat.size == 0:
                continue
            j_flat = np.atleast_1d(np.asarray(jdom, dtype=np.float64).ravel()).astype(np.int64).ravel()
            if j_flat.size == 0:
                continue
            q_parts: list[np.ndarray] = []
            for jj in j_flat:
                ji = int(jj)
                if ji < 1 or ji > nf_m:
                    continue
                q_parts.append(np.asarray(Q_row[ji - 1], dtype=np.float64))
            if not q_parts:
                continue
            if len(q_parts) == 1:
                Qj = q_parts[0]
            else:
                Qj = spm_cross(*q_parts)

            qa_slot = bundle["qa"][mi][g_idx]
            qa_base = _unwrap_gp_elem(qa_slot)
            qa_arr = np.asarray(qa_base, dtype=np.float64)
            if qa_arr.size == 0:
                continue
            da = np.zeros_like(qa_arr, dtype=np.float64)
            for i_out in k_flat:
                io = int(i_out)
                if io < 1:
                    continue
                ocell = O_m[io - 1][t_idx]
                if ocell is None or not _tensor_nonempty(ocell):
                    continue
                Oi = np.asarray(ocell, dtype=np.float64)
                term = np.asarray(spm_cross(Oi, Qj), dtype=np.float64)
                # MATLAB ``reshape(da,size(qa{m,g}))`` requires ``numel(da)==numel(qa{m,g})``.
                if int(term.size) != int(qa_arr.size):
                    raise ValueError(
                        f"spm_MDP_VB_XXX: spm_cross(O,Qj) numel {int(term.size)} != qa numel {int(qa_arr.size)} "
                        f"(m={mi + 1}, g={g_1}, t={t_idx + 1})"
                    )
                if term.shape != qa_arr.shape:
                    term = np.reshape(term, qa_arr.shape, order="F")
                da = da + term
            supp = qa_arr != 0.0
            da = np.where(supp, da, 0.0)
            qa_new = np.asarray(qa_arr + da, dtype=np.float64)
            if not qa_new.flags.writeable:
                qa_new = np.asarray(qa_arr + da, dtype=np.float64).copy(order="F")
            _spm_norm_inplace(qa_new)
            if "A" in md:
                Agf = md["A"][g_idx]
                Agf = Agf[0] if isinstance(Agf, list) and len(Agf) == 1 else Agf
                if isinstance(Agf, np.ndarray) and Agf.dtype == bool:
                    qa_new = qa_new.astype(bool)
            if isinstance(qa_slot, list) and len(qa_slot) == 1:
                qa_slot[0] = qa_new
            else:
                bundle["qa"][mi][g_idx] = qa_new
            A_slot = bundle["A"][mi][g_idx]
            if isinstance(A_slot, list) and len(A_slot) == 1:
                A_slot[0] = qa_new
            else:
                bundle["A"][mi][g_idx] = qa_new
            # MATLAB ~1403–1432: workspace ``qa``/``A{m,g}`` only (not ``MDP(m).a`` / ``MDP(m).A``).
            bundle["W"][mi][g_idx] = _spm_wnorm(qa_new)
            bundle["K"][mi][g_idx] = _spm_hnorm(qa_new)

    if "b" in md and t_m > 1:
        for f_idx in range(nf_m):
            Qt = np.asarray(bundle["Q"][mi][f_idx][t_idx], dtype=np.float64)
            Qtm1 = np.asarray(bundle["Q"][mi][f_idx][t_idx - 1], dtype=np.float64)
            Ptm1 = np.asarray(bundle["P"][mi][f_idx][t_idx - 1], dtype=np.float64)
            db = np.asarray(
                spm_cross(spm_cross(Qt, Qtm1), Ptm1),
                dtype=np.float64,
            )
            qb_slot = bundle["qb"][mi][f_idx]
            qb_arr = np.asarray(_unwrap_gp_elem(qb_slot), dtype=np.float64)
            if qb_arr.size == 0:
                continue
            if db.shape != qb_arr.shape:
                db = np.reshape(db, qb_arr.shape, order="F")
            supp_b = qb_arr != 0.0
            db = np.where(supp_b, db, 0.0)
            qb_new = qb_arr + db
            if isinstance(qb_slot, list) and len(qb_slot) == 1:
                qb_slot[0] = qb_new
            else:
                bundle["qb"][mi][f_idx] = qb_new
            B_norm = _spm_norm(qb_new)
            if "B" in md:
                Bgf = md["B"][f_idx]
                Bgf = Bgf[0] if isinstance(Bgf, list) and len(Bgf) == 1 else Bgf
                if isinstance(Bgf, np.ndarray) and Bgf.dtype == bool:
                    B_norm = B_norm.astype(bool)
            bundle["B"][mi][f_idx] = B_norm
            I_w = _spm_wnorm(qb_new)
            bundle["I"][mi][f_idx] = I_w
            if "b" in md:
                b_sl = md["b"][f_idx]
                if isinstance(b_sl, list) and len(b_sl) == 1:
                    b_sl[0] = qb_new.copy()
                else:
                    md["b"][f_idx] = qb_new.copy()
            if "B" in md:
                bg = md["B"][f_idx]
                bn = np.array(B_norm, copy=True)
                if isinstance(bg, list) and len(bg) == 1:
                    bg[0] = bn
                else:
                    md["B"][f_idx] = bn


def _vb_belief_after_forwards(
    mi: int,
    bundle: dict[str, Any],
    t_m: int,
    t_idx: int,
    G_m: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, float]:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1264–1346 immediately after ``spm_forwards``.

    Augment ``G`` at ``t==1`` with log priors over policy rows from ``E`` / ``V``;
    ``R = spm_softmax(G)``, ``w``, ``v``; path posteriors ``P{m,f,t-1}`` when ``t>1``;
    path complexity ``Z`` (~1285–1317); ``Pu = spm_softmax(G,alpha)`` and current ``P{m,f,t}``
    from ``Pu`` and ``V``.

    Returns policy-column ``G`` after augmentation (for ``MDP(m).G{t}``) and scalar ``Z``.
    """
    Pu_carry: list[Any] = bundle["Pu_carry"]
    npp = int(bundle["Np"][mi])
    G_flat = np.asarray(G_m, dtype=np.float64).copy().ravel(order="F")
    if npp > 0:
        G_work = G_flat.reshape(npp, -1, order="F")
        if G_work.shape[1] != 1:
            G_work = np.sum(G_work, axis=1, keepdims=True)
        G_work = G_work.reshape(npp, 1)
        G_for_R = G_work
        n_rows_r = npp
    else:
        # ``MDP(m).G{t} = G`` from forwards (unchanged Pass-1 storage); ``R{m}(:,t)`` still 1×1 when ``Np==0``.
        G_work = np.zeros((0, 1), dtype=np.float64)
        if G_flat.size == 0:
            G_for_R = np.zeros((1, 1), dtype=np.float64)
        else:
            G_for_R = np.asarray(G_flat.reshape(-1, 1)[:1], dtype=np.float64)
        n_rows_r = 1

    V_csr = bundle["V"][mi]
    Vd = V_csr.toarray()
    Um_row = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
    E_list = bundle["gp"][mi]["E"]
    nf_m = int(bundle["Nf"][mi])
    Nu_arr = bundle["Nu"]

    if t_m == 1:
        for k in range(npp):
            le_acc = 0.0
            for f_idx in range(nf_m):
                if f_idx >= Um_row.size or Um_row[f_idx] == 0.0:
                    continue
                Ef = np.asarray(_unwrap_gp_elem(E_list[f_idx]), dtype=np.float64).reshape(-1, 1, order="F")
                vk = int(round(float(Vd[k, f_idx])))
                if vk < 1 or vk > Ef.shape[0]:
                    continue
                ev = float(Ef[vk - 1, 0])
                le_acc += float(np.asarray(_spm_log(np.array([[ev]], dtype=np.float64))).reshape(-1)[0])
            G_work[k, 0] += le_acc

    if bundle["R_policy"][mi].shape[0] < n_rows_r:
        old = np.asarray(bundle["R_policy"][mi], dtype=np.float64)
        grown = np.zeros((n_rows_r, old.shape[1]), dtype=np.float64)
        if old.size:
            grown[: old.shape[0], :] = old
        bundle["R_policy"][mi] = grown
    R_col = np.asarray(spm_softmax(G_for_R), dtype=np.float64).reshape(n_rows_r, 1)
    bundle["R_policy"][mi][:n_rows_r, t_idx] = R_col.reshape(-1)
    bundle["w_policy"][mi][t_idx] = float(
        (R_col.T @ np.asarray(_spm_log(R_col), dtype=np.float64).reshape(-1, 1)).reshape(-1)[0]
    )
    bundle["v_policy"][mi][t_idx] = float((R_col.T @ G_for_R).reshape(-1)[0])

    Q_all = bundle["Q"]
    P_all = bundle["P"]
    B_t = bundle["B"]

    Z_acc = 0.0
    if t_m > 1:
        for f_idx in range(nf_m):
            nu_mf = int(Nu_arr[mi, f_idx])
            if nu_mf > 1:
                Bmf = _unwrap_gp_elem(B_t[mi][f_idx])
                Qt = np.asarray(Q_all[mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1, order="F")
                Qtm1 = np.asarray(Q_all[mi][f_idx][t_idx - 1], dtype=np.float64).reshape(-1, 1, order="F")
                LL = np.asarray(spm_dot(spm_dot(Bmf, Qt), Qtm1), dtype=np.float64)
                LL = np.asarray(_spm_log(LL), dtype=np.float64).reshape(-1, 1)
                LP = np.asarray(_spm_log(P_all[mi][f_idx][t_idx - 1]), dtype=np.float64).reshape(-1, 1)
                post = np.asarray(spm_softmax(LL + LP), dtype=np.float64).reshape(-1, 1)
                P_all[mi][f_idx][t_idx - 1] = post
                logp = np.asarray(_spm_log(post), dtype=np.float64).reshape(-1, 1)
                Z_acc += float((post.T @ (LL + LP - logp)).reshape(-1)[0])
            else:
                P_all[mi][f_idx][t_idx - 1] = np.array([[1.0]], dtype=np.float64)

    if npp > 0:
        Pu = np.asarray(spm_softmax(G_work, float(alpha)), dtype=np.float64).reshape(npp, 1)
    else:
        g1 = G_flat.reshape(1, 1) if G_flat.size == 1 else np.zeros((1, 1), dtype=np.float64)
        Pu = np.asarray(spm_softmax(g1, float(alpha)), dtype=np.float64).reshape(1, 1)
    Pu_carry[mi] = Pu

    for f_idx in range(nf_m):
        if f_idx < Um_row.size and Um_row[f_idx] != 0.0:
            nu = int(Nu_arr[mi, f_idx])
            col = np.zeros((nu, 1), dtype=np.float64)
            for u in range(1, nu + 1):
                mask = (Vd[:, f_idx] == float(u)).astype(np.float64).reshape(npp, 1)
                col[u - 1, 0] = float((Pu.T @ mask).reshape(-1)[0])
            P_all[mi][f_idx][t_idx] = col
        else:
            if t_m > 1:
                P_all[mi][f_idx][t_idx] = copy.deepcopy(P_all[mi][f_idx][t_idx - 1])

    # MATLAB ~1464: ``MDP(m).G{t} = G`` — full forwards policy vector (same ``G`` as ``spm_softmax(G)``).
    if npp > 0:
        gw_out = np.asarray(G_work, dtype=np.float64).copy()
    elif G_flat.size >= 1:
        gw_out = np.asarray(G_flat, dtype=np.float64).copy().reshape(-1, 1)
    else:
        gw_out = np.asarray(G_for_R, dtype=np.float64).reshape(-1, 1).copy()
    return gw_out, float(Z_acc)


def _vb_generate_outcomes_if_options_o(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~911–985, **before** ``BP``/``IP``.

    Loop structure (~919–985): ``for g = 1:NG(m)`` → ``[j,i] = spm_parents(...,g,s(:,t))`` →
    ``for o = i`` (codomain children, **not** ``o == g``) → if ``~MDP(m).o(o,t)`` generate into
    ``O{m,o,t}`` using ``A{m,g}`` (ELBO / ``Fm``) or ``GP(m).A{g}(:,ind{:})`` when ``n==0`` (~961–967);
    else if ``isempty(O{m,o,t})`` one-hot from ``MDP(m).o(o,t)`` (~977–978). Workspace ``A{m,g}``
    updates later (~1424); ``GP(m).A`` is frozen (~368). Child hierarchical path: ``mdp.S→O`` matrix
    (~1189–1191) does not populate ``O{m,g,t}`` (~732–752 ``catch``); this block fills the shell.
    """
    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("O", 1)) == 0:
        return

    ID_list = bundle["ID"]
    gp_list = bundle["gp"]
    O_shell = bundle["O"]
    Ng_arr = bundle["Ng"]
    NG_arr = bundle["NG"]
    t_int = int(bundle["T"])
    Fm_store: dict[tuple[int, int, int], np.ndarray] = bundle.setdefault("_vb_Fm_neg_t_o_m", {})

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        gpm = gp_list[mi]
        ng_gen = int(NG_arr[mi])
        n_shell = len(O_shell[mi])
        ng_loop = min(ng_gen, n_shell)
        n_o_rows = int(md["o"].shape[0]) if isinstance(md.get("o"), np.ndarray) else ng_gen
        n_mat = np.asarray(md.get("n", np.zeros((max(ng_gen, n_o_rows), t_int))), dtype=np.float64)
        if n_mat.size == 0:
            n_mat = np.zeros((ng_loop, t_int), dtype=np.float64)
        if n_mat.ndim == 1:
            n_mat = n_mat.reshape(-1, 1)
        if n_mat.shape[0] < ng_loop:
            pad = np.zeros((ng_loop, t_int), dtype=np.float64)
            pad[: n_mat.shape[0], :] = n_mat
            n_mat = pad
        if n_mat.shape[1] < t_int:
            pad = np.zeros((n_mat.shape[0], t_int), dtype=np.float64)
            pad[:, : n_mat.shape[1]] = n_mat
            n_mat = pad

        for g_idx in range(ng_loop):
            g_1 = g_idx + 1
            s_col = np.asarray(md["s"][:, t_idx], dtype=np.float64).reshape(-1, 1)
            j_p, i_ch = spm_parents(ID_list[mi], g_1, s_col)
            i_vals = np.atleast_1d(np.asarray(i_ch, dtype=float)).ravel().tolist()
            for o_1based in i_vals:
                o_idx = int(round(float(o_1based))) - 1
                if o_idx < 0 or o_idx >= n_shell or o_idx >= n_o_rows:
                    continue
                if float(md["o"][o_idx, t_idx]) != 0.0:
                    # MATLAB ~933–939: when outcome realization is already specified,
                    # fill O{m,o,t} with one-hot if currently empty.
                    if not _tensor_nonempty(O_shell[mi][o_idx][t_idx]):
                        no_mo = int(bundle["No"][mi, o_idx])
                        oi = int(round(float(md["o"][o_idx, t_idx])))
                        if no_mo > 0 and oi > 0 and oi <= no_mo:
                            O_shell[mi][o_idx][t_idx] = _spm_one_hot(oi, no_mo)
                    continue
                n_ot = float(n_mat[o_idx, t_idx])

                if n_ot > 0:
                    ni = int(round(n_ot)) - 1
                    if ni == mi:
                        j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                        q_list = [bundle["Q"][mi][int(jv) - 1][t_idx] for jv in j_arr if int(jv) > 0]
                        Amg = _unwrap_gp_elem(bundle["A"][mi][g_idx])
                        if callable(Amg) and not isinstance(Amg, np.ndarray):
                            raise NotImplementedError(
                                "OPTIONS.O: likelihood function_handle A{g} not translated"
                            )
                        F = np.asarray(spm_dot(Amg, q_list), dtype=np.float64).reshape(-1, 1)
                        Fl = np.asarray(_spm_log(F), dtype=np.float64).reshape(-1, 1)
                        Ocell = np.asarray(spm_softmax(Fl * 512.0), dtype=np.float64).reshape(-1, 1)
                        O_shell[mi][o_idx][t_idx] = Ocell
                        md["o"][o_idx, t_idx] = float(_spm_sample(Ocell))
                    else:
                        O_shell[mi][o_idx][t_idx] = O_shell[ni][o_idx][t_idx]
                        md["o"][o_idx, t_idx] = float(models[ni]["o"][o_idx, t_idx])
                    continue

                if n_ot < 0:
                    j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                    q_list = [bundle["Q"][mi][int(jv) - 1][t_idx] for jv in j_arr if int(jv) > 0]
                    Amg = _unwrap_gp_elem(bundle["A"][mi][g_idx])
                    if callable(Amg) and not isinstance(Amg, np.ndarray):
                        raise NotImplementedError(
                            "OPTIONS.O: likelihood function_handle A{g} not translated (Fm branch)"
                        )
                    Fm_store[(t_idx, o_idx, mi)] = np.asarray(
                        _spm_log(np.asarray(spm_dot(Amg, q_list), dtype=np.float64)),
                        dtype=np.float64,
                    ).reshape(-1, 1)
                    continue

                Ag_raw = _unwrap_gp_elem(gpm["A"][g_idx])
                if callable(Ag_raw) and not isinstance(Ag_raw, np.ndarray):
                    raise NotImplementedError("OPTIONS.O: GP.A{g} function_handle not translated")
                # ``GP(m).A{g}(:,ind{:})`` (~967): frozen generative map, not workspace ``A{m,g}``.
                Ag = np.asarray(Ag_raw, dtype=np.float64)
                j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                ind_parts: list[int] = []
                for jx in j_arr:
                    jxi = int(round(float(jx)))
                    sv = float(md["s"][jxi - 1, t_idx])
                    ind_parts.append(int(round(sv)) - 1)
                try:
                    col = _vb_gp_A_outcome_column(Ag, ind_parts)
                except (IndexError, TypeError):
                    raise
                O_shell[mi][o_idx][t_idx] = col
                md["o"][o_idx, t_idx] = float(_spm_sample(col))


def _vb_shared_probabilistic_outcomes(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~952–969: ``Fm{g,j}`` from the ``n(o,t) < 0`` path (~914–917),
    summed over agents ``j ~= m``, ``O{m,g,t} = spm_softmax(F)``, sample ``o`` from ``spm_softmax(F*512)``.
    """
    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("O", 1)) == 0:
        return

    Fm_store: dict[tuple[int, int, int], np.ndarray] = bundle.get("_vb_Fm_neg_t_o_m", {})
    O_shell = bundle["O"]
    Ng_arr = bundle["Ng"]
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        ng_m = int(Ng_arr[mi])
        n_mat = np.asarray(md.get("n", np.zeros((ng_m, t_int))), dtype=np.float64)
        if n_mat.size == 0:
            n_mat = np.zeros((ng_m, t_int), dtype=np.float64)
        if n_mat.ndim == 1:
            n_mat = n_mat.reshape(ng_m, -1)
        if n_mat.shape[0] < ng_m:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[: n_mat.shape[0], :] = n_mat
            n_mat = pad
        if n_mat.shape[1] < t_int:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[:, : n_mat.shape[1]] = n_mat
            n_mat = pad

        for g_idx in range(ng_m):
            if float(n_mat[g_idx, t_idx]) >= 0.0:
                continue
            acc: np.ndarray | None = None
            for j_other in range(nm):
                if j_other == mi:
                    continue
                key = (t_idx, g_idx, j_other)
                vec = Fm_store.get(key)
                if vec is None:
                    continue
                v = np.asarray(vec, dtype=np.float64).reshape(-1, 1)
                acc = v.copy() if acc is None else (acc + v)
            if acc is None:
                continue
            F = acc
            O_dist = np.asarray(spm_softmax(F), dtype=np.float64).reshape(-1, 1)
            po = np.asarray(spm_softmax(F * 512.0), dtype=np.float64).reshape(-1, 1)
            O_shell[mi][g_idx][t_idx] = O_dist
            md["o"][g_idx, t_idx] = float(_spm_sample(po))


def _vb_hierarchical_q_O_prev_ncols(ol: Any, *, ng: int = 0) -> int:
    """MATLAB ``size(mdp.Q.O{mdp.L}, 2)`` — column count for hierarchical ``S`` segment offset."""
    if ol is None:
        return 0
    if isinstance(ol, np.ndarray):
        arr = np.asarray(ol, dtype=np.float64)
        if arr.ndim >= 2:
            return int(arr.shape[1])
        return int(arr.size > 0)
    if isinstance(ol, list):
        if not ol:
            return 0
        ng_i = int(ng)
        if ng_i > 0 and len(ol) % ng_i == 0:
            return len(ol) // ng_i
        if isinstance(ol[0], list):
            return int(len(ol))
        first = ol[0]
        if isinstance(first, np.ndarray) and int(np.asarray(first).ndim) <= 1:
            if ng_i > 0 and len(ol) % ng_i == 0:
                return len(ol) // ng_i
        try:
            arr = np.asarray(ol, dtype=np.float64)
            if arr.ndim >= 2:
                return int(arr.shape[1])
        except Exception:
            pass
        return int(len(ol))
    return 0


def _vb_no_list_from_mdp(md: dict[str, Any]) -> list[int]:
    """``No(m,g) = size(MDP(m).A{g},1)`` (~386) for hierarchical ``Q.O`` cell splits."""
    A = md.get("A", [])
    if not isinstance(A, list):
        return []
    out: list[int] = []
    for ag in A:
        try:
            out.append(int(np.asarray(ag, dtype=np.float64).shape[0]))
        except Exception:
            out.append(1)
    return out


def _vb_hierarchical_q_o_field_to_cell_row(
    O_field: Any,
    t_child: int,
    *,
    ng: int = 0,
    no: list[int] | None = None,
) -> list[Any]:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~1238 ``mdp.Q.O{mdp.L} = [.. mdp.O]``.

    After child VB, ``mdp.O`` is ``shiftdim(O,1)`` (~1759–1764) → ``T×Ng`` cells via
    ``_vb_shiftdim_o_ng_t_cells``. Flatten ``g`` then ``t`` (MATLAB ``(:)`` on ``T×Ng``,
    index ``t + g*T``) for ``mdp.Q.O{L}=[..mdp.O]`` (~1238). Variable ``No(g)`` splits
    use ``size(MDP(m).A{g},1)`` (~386), not equal row blocks.
    """
    t_child = int(t_child)
    if isinstance(O_field, list) and O_field and isinstance(O_field[0], (list, tuple)):
        n_outer = len(O_field)
        n_inner = len(O_field[0]) if O_field[0] else 0
        # ``_vb_shiftdim_o_ng_t_cells``: out[t][g]
        no_use = list(no) if no else []
        if t_child > 0 and n_outer == t_child and (ng <= 0 or n_inner == ng):
            # Post-``shiftdim`` ``mdp.O`` is ``T×Ng`` (~1764). ``[mdp.Q.O{L} mdp.O]`` (~1238) linearizes
            # that cell block as MATLAB ``(:)`` — column-major on ``T×Ng``, index ``t + g*T``.
            cells: list[Any] = []
            ng_use = int(ng) if int(ng) > 0 else n_inner
            ncol = min(t_child, n_outer)
            for g in range(ng_use):
                for t in range(ncol):
                    n_g = int(no_use[g]) if g < len(no_use) else 0
                    if t < len(O_field) and g < len(O_field[t]):
                        part = O_field[t][g]
                    else:
                        part = None
                    if part is None:
                        cells.append(np.zeros((max(1, n_g), 1), dtype=np.float64))
                    else:
                        cells.append(_vb_o_cell_to_column(part, n_g))
            return cells
        # Internal ``O{m,g,t}`` shell: ``O_mi[g][t]`` on ``Ng×T`` — MATLAB ``(:)`` uses ``g + t*Ng``.
        if ng > 0 and n_outer == ng:
            cells = []
            ncol = min(t_child, max((len(O_field[g]) for g in range(ng)), default=0))
            for g in range(ng):
                for t in range(ncol):
                    row_g = O_field[g]
                    if t < len(row_g) and row_g[t] is not None:
                        n_g = int(no_use[g]) if g < len(no_use) else 0
                        cells.append(_vb_o_cell_to_column(row_g[t], n_g))
                    else:
                        n_g = int(no_use[g]) if g < len(no_use) else 1
                        cells.append(np.zeros((max(1, n_g), 1), dtype=np.float64))
            return cells
    mat = _vb_hierarchical_O_field_to_matrix(O_field, t_child, no=no)
    if mat.size == 0:
        return []
    ncol = min(t_child, int(mat.shape[1]))
    if ncol < 1:
        return []
    ng_i = int(ng) if int(ng) > 0 else (len(no) if no else 0)
    if ng_i < 1:
        return [np.asarray(mat, dtype=np.float64).reshape(-1, 1, order="F")]
    no_use = list(no) if no else []
    if len(no_use) < ng_i:
        step = max(1, int(mat.shape[0] // ng_i))
        no_use = [step] * (ng_i - 1) + [max(1, int(mat.shape[0] - step * (ng_i - 1)))]
    cells: list[Any] = []
    for g in range(ng_i):
        n_g = int(no_use[g]) if g < len(no_use) else 0
        row0 = sum(int(no_use[gi]) for gi in range(g))
        for t in range(ncol):
            col = np.asarray(mat[:, t], dtype=np.float64).reshape(-1, order="F")
            if n_g < 1:
                cells.append(np.zeros((1, 1), dtype=np.float64))
            elif row0 + n_g <= col.shape[0]:
                cells.append(
                    np.asarray(col[row0 : row0 + n_g], dtype=np.float64).reshape(-1, 1, order="F")
                )
            else:
                cells.append(np.zeros((max(1, n_g), 1), dtype=np.float64))
    return cells


def _vb_o_cell_to_column(part: Any, n_g: int) -> np.ndarray:
    """One ``O{m,g,t}`` leaf as ``No(g)×1`` column (pad/truncate to ``size(A{g},1)``)."""
    col = np.asarray(part, dtype=np.float64).reshape(-1, 1, order="F")
    if n_g < 1:
        return col
    if col.shape[0] < n_g:
        col = np.vstack([col, np.zeros((n_g - col.shape[0], 1), dtype=np.float64)])
    elif col.shape[0] > n_g:
        col = col[:n_g, :]
    return col


def _vb_hierarchical_O_field_to_matrix(
    O_field: Any,
    t_int: int,
    *,
    no: list[int] | None = None,
) -> np.ndarray:
    """
    Normalize ``mdp.O`` / assembled ``shiftdim`` cells to a 2-D matrix for ``[Q.O{L} old new]``.

    MATLAB appends ``mdp.O`` horizontally; list-concat of ``shiftdim`` cells breaks ``size(...,2)``.
    """
    if O_field is None:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    if isinstance(O_field, np.ndarray):
        arr = np.asarray(O_field, dtype=np.float64)
        if arr.ndim == 1:
            return arr.reshape(-1, 1, order="F")
        return np.asfortranarray(arr)
    if isinstance(O_field, list) and O_field:
        if isinstance(O_field[0], list):
            cols: list[np.ndarray] = []
            n_t = int(t_int) if int(t_int) > 0 else len(O_field)
            no_use = list(no) if no else []
            for ti in range(min(n_t, len(O_field))):
                row = O_field[ti]
                ng_row = len(row)
                parts = [
                    _vb_o_cell_to_column(
                        row[g],
                        int(no_use[g]) if g < len(no_use) else 0,
                    )
                    for g in range(ng_row)
                ]
                if parts:
                    cols.append(np.vstack(parts))
            if not cols:
                return np.zeros((0, 0), dtype=np.float64, order="F")
            return np.asfortranarray(np.hstack(cols))
        try:
            arr = np.asarray(O_field, dtype=np.float64)
            if arr.ndim >= 2:
                return np.asfortranarray(arr)
        except Exception:
            pass
    return np.zeros((0, 0), dtype=np.float64, order="F")


def _vb_hierarchical_apply_S_as_O_if_present(child: dict[str, Any]) -> None:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~1178–1191.

    After ``rmfield(mdp,'O')`` / ``rmfield(mdp,'o')`` (~1169–1173), optional ``mdp.O = mdp.S(:,seg(j))``
    (dense matrix, **not** ``mdp.O{g,t}``). Child init ~732–752 must not treat that matrix as one row per ``g``
    (see ``_vb_mdp_O_is_cell_gt_layout``).
    """
    if "S" not in child or child.get("S") is None:
        return
    S = np.asarray(child["S"], dtype=np.float64)
    if S.size == 0:
        return
    t_md = int(np.asarray(child.get("T", 1)).ravel()[0])
    L = max(1, int(np.asarray(child.get("L", 1)).ravel()[0]))
    S2 = S.reshape(S.shape[0], -1, order="F") if S.ndim >= 2 else S.reshape(-1, 1, order="F")
    n_col_s = int(S2.shape[1])
    prev_cols = 0
    qrec = child.get("Q")
    if isinstance(qrec, dict) and "O" in qrec:
        Oc = qrec.get("O")
        if isinstance(Oc, (list, tuple)) and len(Oc) >= L:
            ol = Oc[L - 1]
            ng_m = len(child.get("A", [])) if isinstance(child.get("A"), list) else 0
            prev_cols = _vb_hierarchical_q_O_prev_ncols(ol, ng=ng_m)
    seg = np.arange(1, t_md + 1, dtype=np.int64) + int(prev_cols)
    mask = seg <= n_col_s
    use = seg[mask]
    n_row = int(S2.shape[0])
    if use.size == 0:
        child["O"] = np.zeros((n_row, 0), dtype=np.float64, order="F")
    else:
        idx0 = (use - 1).astype(np.int64, copy=False)
        child["O"] = np.asfortranarray(np.asarray(S2[:, idx0], dtype=np.float64))
    if os.getenv("RGMS_ENTRY12_PROBE_HIER"):
        import sys as _sys

        print(
            f"[12E S→O] T={t_md} prev_cols={prev_cols} seg={seg.ravel()[:6]} "
            f"O.shape={np.asarray(child.get('O')).shape}",
            file=_sys.stderr,
            flush=True,
        )


def _vb_hierarchical_q_ot_grid_to_cell_row(field: list[Any], *, t_child: int) -> list[Any]:
    """
    Flatten ``mdp.Y{o,t}`` / ``mdp.j{g,t}``-style nested lists ``field[o][t]`` to a cell row.

    MATLAB stores these as ``Ng``×``T`` cell matrices; ``[Q.*{L} mdp.*]`` uses ``(:)`` order
    (column-major): flat index ``o + t*Ng``.
    """
    cells: list[Any] = []
    n_o = len(field)
    for t in range(t_child):
        for o in range(n_o):
            row = field[o]
            if not isinstance(row, (list, tuple)) or t >= len(row) or row[t] is None:
                cells.append(np.zeros((1, 1), dtype=np.float64))
                continue
            cells.append(np.asarray(row[t], dtype=np.float64).reshape(-1, 1, order="F"))
    return cells


def _vb_hierarchical_q_field_to_cell_row(field: Any, *, t_child: int, kind: str) -> list[Any]:
    """
    Flatten one child ``mdp`` field to a MATLAB-style cell row for ``mdp.Q.*{L} = [old new]``.

  ``O`` uses ``_vb_hierarchical_q_o_field_to_cell_row`` (``shiftdim`` cells or ``S`` matrix); other keys use cell rows.
    """
    if field is None:
        return []
    if kind == "O":
        return _vb_hierarchical_q_o_field_to_cell_row(field, t_child)
    if kind in ("s", "u"):
        arr = np.asarray(field, dtype=np.float64).reshape(-1, 1)
        return [arr.copy()]
    if kind in ("P", "X") and isinstance(field, list):
        out_mats: list[Any] = []
        for pf in field:
            arr = np.asarray(pf, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            ncol = min(t_child, int(arr.shape[1]))
            out_mats.append(np.asfortranarray(arr[:, :ncol].copy()))
        return out_mats
    if isinstance(field, list) and len(field) == 1:
        return _vb_hierarchical_q_field_to_cell_row(field[0], t_child=t_child, kind=kind)
    if isinstance(field, list) and field and isinstance(field[0], (list, tuple)):
        if kind in ("Y", "j", "i", "o"):
            return _vb_hierarchical_q_ot_grid_to_cell_row(field, t_child=t_child)
    if kind in ("Y", "j", "o") or isinstance(field, (list, tuple)):
        arr = np.asarray(field, dtype=np.float64)
        if arr.ndim >= 3:
            ncol = min(t_child, int(arr.shape[1]))
            cells = []
            for t in range(ncol):
                slab = arr[:, t, ...]
                for g in range(int(slab.shape[0])):
                    cells.append(np.asarray(slab[g, ...], dtype=np.float64).reshape(-1, 1, order="F"))
            return cells
    arr = np.asarray(field, dtype=np.float64)
    if arr.ndim == 2:
        return [arr[:, t : t + 1].copy() for t in range(min(t_child, arr.shape[1]))]
    return [arr.reshape(-1, 1, order="F")]


def _vb_hierarchical_q_O_flat_cells_to_matrix(
    cells: list[Any],
    *,
    ng: int,
    no: list[int],
) -> np.ndarray:
    """Rebuild numeric ``mdp.Q.O{L}`` from flat ``Ng×T`` cell row (column-major ``t``, then ``g``)."""
    if not cells or ng < 1:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    n_leaf = len(cells)
    if n_leaf % ng != 0:
        return _vb_hierarchical_O_field_to_matrix(
            cells, max(1, n_leaf // max(1, ng)), no=no
        )
    ncol = n_leaf // ng
    no_use = list(no) if no else [1] * ng
    cols: list[np.ndarray] = []
    idx = 0
    for _t in range(ncol):
        parts: list[np.ndarray] = []
        for g in range(ng):
            n_g = int(no_use[g]) if g < len(no_use) else 1
            parts.append(_vb_o_cell_to_column(cells[idx], n_g))
            idx += 1
        cols.append(np.vstack(parts) if parts else np.zeros((0, 1), dtype=np.float64))
    if not cols:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    max_h = max(int(c.shape[0]) for c in cols)
    out = np.zeros((max_h, ncol), dtype=np.float64, order="F")
    for t, col in enumerate(cols):
        out[: col.shape[0], t : t + 1] = col
    return out


def _vb_hierarchical_q_O_level_to_matrix(
    level: Any,
    *,
    t_child: int,
    ng: int,
    no: list[int],
) -> np.ndarray:
    """
  MATLAB ``mdp.Q.O{mdp.L} = [mdp.Q.O{mdp.L} mdp.O]`` (~1238): horizontal matrix concat, not cell-list cat.
    """
    if level is None:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    if isinstance(level, np.ndarray):
        arr = np.asarray(level, dtype=np.float64)
        if arr.ndim == 1:
            return arr.reshape(-1, 1, order="F")
        return np.asfortranarray(arr)
    if isinstance(level, list) and level:
        if isinstance(level[0], (list, tuple)):
            return _vb_hierarchical_O_field_to_matrix(level, t_child, no=no)
        return _vb_hierarchical_q_O_flat_cells_to_matrix(level, ng=ng, no=no)
    return np.zeros((0, 0), dtype=np.float64, order="F")


def _vb_hierarchical_q_append_level(qv: list[Any], li: int, child_upd: dict[str, Any], ck: str, t_child: int) -> None:
    """Append one child field into ``qrec[qk]{li}`` (matrix ``O``, cell row otherwise)."""
    if ck not in child_upd:
        return
    while len(qv) <= li:
        qv.append(None)
    if ck == "O":
        ng_m = len(child_upd.get("A", [])) if isinstance(child_upd.get("A"), list) else 0
        new_cells = _vb_hierarchical_q_o_field_to_cell_row(
            child_upd[ck],
            t_child,
            ng=ng_m,
            no=_vb_no_list_from_mdp(child_upd),
        )
        if not new_cells:
            return
        if qv[li] is None:
            qv[li] = new_cells
        elif isinstance(qv[li], list):
            qv[li] = list(qv[li]) + list(new_cells)
        elif isinstance(qv[li], np.ndarray):
            old_ncol = int(np.asarray(qv[li], dtype=np.float64).shape[1])
            old_cells = _vb_hierarchical_q_o_field_to_cell_row(
                qv[li],
                old_ncol,
                ng=ng_m,
                no=_vb_no_list_from_mdp(child_upd),
            )
            qv[li] = list(old_cells) + list(new_cells)
        else:
            qv[li] = new_cells
        return
    if ck in ("P", "X"):
        new_level = _vb_hierarchical_q_field_to_cell_row(child_upd[ck], t_child=t_child, kind=ck)
        if qv[li] is None:
            qv[li] = new_level
        elif isinstance(qv[li], list) and new_level and isinstance(qv[li][0], np.ndarray):
            merged: list[Any] = []
            for f in range(len(new_level)):
                old_f = np.asarray(qv[li][f], dtype=np.float64) if f < len(qv[li]) else qv[li][-1]
                new_f = np.asarray(new_level[f], dtype=np.float64)
                merged.append(
                    np.asfortranarray(np.hstack([old_f, new_f]))
                    if old_f.size and new_f.size
                    else (new_f if new_f.size else old_f)
                )
            qv[li] = merged
        else:
            qv[li] = _vb_hierarchical_q_concat(qv[li], new_level)
        return
    if ck in ("s", "u"):
        new_m = np.asarray(child_upd[ck], dtype=np.float64)
        if new_m.ndim == 1:
            new_m = new_m.reshape(-1, 1, order="F")
        elif new_m.ndim == 2 and int(new_m.shape[1]) > t_child:
            new_m = np.asfortranarray(new_m[:, :t_child].copy())
        if qv[li] is None:
            qv[li] = np.asfortranarray(new_m.copy())
            return
        old = qv[li]
        if isinstance(old, list):
            mats = [np.asarray(x, dtype=np.float64) for x in old if x is not None]
            old_m = np.hstack(mats) if mats else np.zeros((new_m.shape[0], 0), dtype=np.float64, order="F")
        else:
            old_m = np.asarray(old, dtype=np.float64)
        qv[li] = np.asfortranarray(np.hstack([old_m, new_m]))
        return
    new_cells = _vb_hierarchical_q_field_to_cell_row(child_upd[ck], t_child=t_child, kind=ck)
    if qv[li] is None:
        qv[li] = new_cells
    elif isinstance(qv[li], list):
        qv[li] = list(qv[li]) + list(new_cells)
    else:
        qv[li] = _vb_hierarchical_q_concat(qv[li], new_cells)


def _vb_hierarchical_q_concat(existing: Any, new_value: Any) -> Any:
    """MATLAB ``[old new]`` append used for hierarchical ``mdp.Q`` records (~1186–1207)."""
    if existing is None:
        return copy.deepcopy(new_value)
    if isinstance(existing, list) and isinstance(new_value, list):
        return copy.deepcopy(existing) + copy.deepcopy(new_value)
    try:
        ea = np.asarray(existing, dtype=np.float64)
        na = np.asarray(new_value, dtype=np.float64)
        if ea.ndim == 1:
            ea = ea.reshape(-1, 1)
        if na.ndim == 1:
            na = na.reshape(-1, 1)
        if ea.size == 0:
            return na.copy()
        if na.size == 0:
            return ea.copy()
        return np.hstack([ea, na])
    except Exception:
        if isinstance(existing, list):
            return copy.deepcopy(existing) + [copy.deepcopy(new_value)]
        if isinstance(new_value, list):
            return [copy.deepcopy(existing)] + copy.deepcopy(new_value)
        return [copy.deepcopy(existing), copy.deepcopy(new_value)]


def _vb_hierarchical_update_parent_Q_from_child(parent: dict[str, Any], child_upd: dict[str, Any]) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1180–1209: update and append child trajectory record in ``mdp.Q``.
    """
    parent_q = parent.get("Q")
    if "Q" in child_upd:
        qrec = copy.deepcopy(child_upd["Q"])
    elif isinstance(parent_q, dict):
        qrec = copy.deepcopy(parent_q)
    else:
        qrec = {}
    if not isinstance(qrec, dict):
        parent["Q"] = qrec
        return
    L = max(1, int(np.asarray(child_upd.get("L", 1)).ravel()[0]))
    li = L - 1
    t_child = int(np.asarray(child_upd.get("T", 1)).ravel()[0])

    if "a" in child_upd:
        qa = qrec.get("a", [])
        if not isinstance(qa, list):
            qa = list(np.asarray(qa, dtype=object).ravel(order="F"))
        while len(qa) <= li:
            qa.append(None)
        qa[li] = copy.deepcopy(child_upd["a"])
        qrec["a"] = qa

    mapping = {
        "s": "s",
        "u": "u",
        "P": "P",
        "X": "X",
        "Y": "Y",
        "O": "O",
        "o": "o",
        "j": "j",
        "E": "F",
    }

    try:
        for qk, ck in mapping.items():
            qv = qrec.get(qk, [])
            if not isinstance(qv, list):
                qv = list(np.asarray(qv, dtype=object).ravel(order="F"))
            _vb_hierarchical_q_append_level(qv, li, child_upd, ck, t_child)
            qrec[qk] = qv

        f_old = float(np.sum(np.asarray(qrec.get("F", 0.0), dtype=np.float64)))
        f_new = float(np.sum(np.asarray(child_upd.get("F", 0.0), dtype=np.float64)))
        qrec["F"] = f_old + f_new
    except Exception:
        for qk, ck in mapping.items():
            qv = qrec.get(qk, [])
            if not isinstance(qv, list):
                qv = list(np.asarray(qv, dtype=object).ravel(order="F"))
            try:
                _vb_hierarchical_q_append_level(qv, li, child_upd, ck, t_child)
            except Exception:
                if ck in child_upd:
                    while len(qv) <= li:
                        qv.append(None)
                    qv[li] = copy.deepcopy(child_upd[ck])
            qrec[qk] = qv
        qrec["F"] = float(np.sum(np.asarray(child_upd.get("F", 0.0), dtype=np.float64)))

    parent["Q"] = qrec
    child_upd["Q"] = copy.deepcopy(qrec)


def _vb_hierarchical_subordinate_outcomes(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
    recurse_partial: bool,
    *,
    reuse_matlab_draws: bool = False,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~973+ (hierarchical ``MDP(m).MDP`` branch), partial Pass 1.

    Implemented here:
    - child extraction / B,D,E defaults
    - prior forwarding from child P/X into D/E
    - empirical prior updates from parent outcomes into child D/E (id.D/id.E)
    - non-process child path/state initial sampling
    - optional pass-through of ``MDP(m).Q`` to child
    - ``mdp.S`` → ``mdp.O`` transcription (~1138–1151) before child VB
    - process child with ``GV``: nested ``spm_action`` (~1087) then ``u``/``s`` narrowing (~1089–1105)
    - recurse into child ``spm_MDP_VB_XXX`` and map child posteriors back to parent O

    Still blocked:
    - none in this translated hierarchy window (~973–1210) beyond global partial-stub boundaries
    """
    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    O_shell = bundle["O"]
    t_int = int(bundle["T"])

    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        parent = models[mi]
        if "MDP" not in parent or parent["MDP"] is None:
            continue

        mdp_field = parent["MDP"]
        if isinstance(mdp_field, list) and len(mdp_field) > 0:
            child = copy.deepcopy(mdp_field[0])
        elif isinstance(mdp_field, np.ndarray) and mdp_field.dtype == object and mdp_field.size > 0:
            child = copy.deepcopy(mdp_field.ravel(order="F")[0])
        elif isinstance(mdp_field, dict):
            child = copy.deepcopy(mdp_field)
        else:
            raise NotImplementedError("hierarchical MDP.MDP layout not yet supported")

        nf, ns, nu, _, _ = spm_MDP_size(child)
        nf_i = int(nf)
        ns_v = np.asarray(ns, dtype=np.int64).reshape(-1)
        nu_v = np.asarray(nu, dtype=np.int64).reshape(-1)

        if "B" not in child:
            child["B"] = []
            for f in range(nf_i):
                child["B"].append(_spm_norm(np.asarray(child["b"][f], dtype=np.float64)))
        if "D" not in child:
            child["D"] = []
            for f in range(nf_i):
                child["D"].append(_spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64)))
        if "E" not in child:
            child["E"] = []
            for f in range(nf_i):
                child["E"].append(_spm_norm(np.ones((int(nu_v[f]), 1), dtype=np.float64)))

        # ~1003–1074 update priors, initial states and paths of child
        for f in range(nf_i):
            if "P" in child:
                T_child = int(np.asarray(child.get("T", 1)).reshape(-1)[0])
                U_raw = child.get("U", np.zeros((1, nf_i)))
                if sparse.issparse(U_raw):
                    U_raw = U_raw.toarray()
                U_child = np.asarray(U_raw, dtype=np.float64)
                if U_child.ndim == 1:
                    U_child = U_child.reshape(1, -1)
                has_u = bool(f < U_child.shape[1] and np.any(U_child[:, f]))

                if T_child > 1:
                    if has_u:
                        child["E"][f] = np.asarray(child["P"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                        ps = np.asarray(child["X"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                        pu = np.asarray(child["E"][f], dtype=np.float64).reshape(-1, 1)
                        if pu.size > 1:
                            child["D"][f] = np.asarray(spm_dot(child["B"][f], [pu]), dtype=np.float64) @ ps
                        else:
                            child["D"][f] = np.asarray(child["B"][f], dtype=np.float64) @ ps
                    else:
                        child["E"][f] = _spm_norm(np.ones((int(nu_v[f]), 1), dtype=np.float64))
                        child["D"][f] = _spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64))
                else:
                    if has_u:
                        child["E"][f] = np.asarray(child["P"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                    else:
                        child["E"][f] = _spm_norm(np.ones((int(nu_v[f]), 1), dtype=np.float64))
                    ps = np.asarray(child["X"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                    pu = np.asarray(child["E"][f], dtype=np.float64).reshape(-1, 1)
                    if pu.size > 1:
                        child["D"][f] = np.asarray(spm_dot(child["B"][f], [pu]), dtype=np.float64) @ ps
                    else:
                        child["D"][f] = np.asarray(child["B"][f], dtype=np.float64) @ ps
                    # MATLAB line ~1053 overwrite retained for fidelity.
                    child["D"][f] = _spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64))

            id_child = child.get("id", {})
            idE = id_child.get("E", [])
            if isinstance(idE, (list, tuple)) and f < len(idE):
                for g in np.atleast_1d(np.asarray(idE[f], dtype=np.int64).ravel()).tolist():
                    j = spm_parents(bundle["id"][mi], int(g), [bundle["Q"][mi][ff][t_idx] for ff in range(len(bundle["Q"][mi]))])[0]
                    j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                    q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr]
                    po = np.asarray(spm_dot(bundle["A"][mi][int(g) - 1], q_list), dtype=np.float64).reshape(-1, 1)
                    child["E"][f] = _spm_multiply(child["E"][f], po)

            idD = id_child.get("D", [])
            if isinstance(idD, (list, tuple)) and f < len(idD):
                for g in np.atleast_1d(np.asarray(idD[f], dtype=np.int64).ravel()).tolist():
                    j = spm_parents(bundle["id"][mi], int(g), [bundle["Q"][mi][ff][t_idx] for ff in range(len(bundle["Q"][mi]))])[0]
                    j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                    q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr]
                    po = np.asarray(spm_dot(bundle["A"][mi][int(g) - 1], q_list), dtype=np.float64).reshape(-1, 1)
                    child["D"][f] = _spm_multiply(child["D"][f], po)

        # ~1077–1119 states and paths of child process
        if _spm_is_process(child):
            if "GV" in child:
                t_act = int(np.asarray(child.get("T", 1)).ravel()[0])
                nf_gp = len(child["GB"])
                for key, fill in (("u", 1.0), ("s", 1.0)):
                    if key not in child or child[key] is None:
                        child[key] = np.full((nf_gp, t_act), fill, dtype=np.float64)
                    else:
                        arr = np.asarray(child[key], dtype=np.float64)
                        if arr.ndim == 1:
                            arr = arr.reshape(-1, 1)
                        if arr.shape[0] < nf_gp:
                            arr = np.vstack(
                                [arr, np.full((nf_gp - arr.shape[0], arr.shape[1]), fill, dtype=np.float64)]
                            )
                        if arr.shape[1] < t_act:
                            arr = np.hstack(
                                [arr, np.full((arr.shape[0], t_act - arr.shape[1]), fill, dtype=np.float64)]
                            )
                        child[key] = arr

                child = _spm_action(child, child["A"], child["D"], t_act)

                u_full = np.asarray(child["u"], dtype=np.float64)
                s_full = np.asarray(child["s"], dtype=np.float64)
                if u_full.ndim == 1:
                    u_full = u_full.reshape(-1, 1)
                if s_full.ndim == 1:
                    s_full = s_full.reshape(-1, 1)
                child["u"] = u_full[:, t_act - 1 : t_act].copy()
                child["s"] = s_full[:, t_act - 1 : t_act].copy()

                GU = np.asarray(child["GU"], dtype=np.float64).ravel()
                nfu = int(child["u"].shape[0])
                for f in range(nfu):
                    if f < GU.size and float(GU[f]) != 0.0:
                        Ge = np.asarray(child["GE"][f], dtype=np.float64).reshape(-1, 1).copy()
                        Ge[:] = 0.0
                        uf = int(round(float(child["u"][f, 0])))
                        if 1 <= uf <= Ge.shape[0]:
                            Ge[uf - 1, 0] = 1.0
                        child["GE"][f] = Ge

                    GBf = np.asarray(child["GB"][f], dtype=np.float64)
                    sf = int(round(float(child["s"][f, 0])))
                    uf2 = int(round(float(child["u"][f, 0])))
                    child["GD"][f] = np.asarray(GBf[:, sf - 1, uf2 - 1], dtype=np.float64).reshape(-1, 1)
                    child["s"][f, 0] = float(_spm_sample(child["GD"][f]))
        else:
            child["u"] = np.ones((nf_i, 1), dtype=np.float64)
            child["s"] = np.ones((nf_i, 1), dtype=np.float64)
            for f in range(nf_i):
                child["u"][f, 0] = float(_spm_sample(np.asarray(child["E"][f], dtype=np.float64).reshape(-1, 1)))
                child["s"][f, 0] = float(_spm_sample(np.asarray(child["D"][f], dtype=np.float64).reshape(-1, 1)))

        if "Q" in parent:
            child["Q"] = copy.deepcopy(parent["Q"])  # ~1163–1164
        child.pop("O", None)  # ~1169–1170
        child.pop("o", None)  # ~1172–1173
        _vb_hierarchical_apply_S_as_O_if_present(child)  # ~1178–1191 ``mdp.S→mdp.O`` matrix

        t_1based = t_idx + 1
        t_last = t_int
        if _vb_monitoring_active() and t_1based in (1, t_last):
            _vb_monitor_snapshot("12E", child, mi + 1, t_1based, "before")
        # MATLAB ~1160 recurses with full ``spm_MDP_VB_XXX(mdp)``; keep staged partial recurse only when parent run is partial.
        # ``spm_MDP_VB_XXX.m`` ~1203: ``spm_MDP_VB_XXX(mdp)`` one arg; child gets its own OPTIONS (~201–207).
        child_opts = _default_options_vb()
        if recurse_partial:
            child_opts["_rgms_partial_ok"] = 1
        t_child = time.perf_counter()
        child_upd = spm_MDP_VB_XXX(
            child,
            child_opts,
            reuse_matlab_draws=reuse_matlab_draws,
        )
        if _vb_monitoring_active() and t_1based in (1, t_last):
            _vb_monitor_snapshot("12E", child_upd, mi + 1, t_1based, "after")
        _vb_timing_add_12e(time.perf_counter() - t_child)

        id_child = child_upd.get("id", {})
        no_arr = np.asarray(bundle["No"], dtype=np.int64)
        idD = id_child.get("D", [])
        for f in range(len(idD)):
            for g in np.atleast_1d(np.asarray(idD[f], dtype=np.int64).ravel()).tolist():
                gi = int(g) - 1
                no_g = int(no_arr[mi, gi]) if no_arr.ndim >= 2 and gi < no_arr.shape[1] else 1
                O_shell[mi][gi][t_idx] = _vb_o_cell_to_column(
                    np.asarray(child_upd["X"][f], dtype=np.float64)[:, 0:1],
                    no_g,
                )

        idE = id_child.get("E", [])
        for f in range(len(idE)):
            for g in np.atleast_1d(np.asarray(idE[f], dtype=np.int64).ravel()).tolist():
                gi = int(g) - 1
                no_g = int(no_arr[mi, gi]) if no_arr.ndim >= 2 and gi < no_arr.shape[1] else 1
                Pf = np.asarray(child_upd["P"][f], dtype=np.float64)
                O_shell[mi][gi][t_idx] = _vb_o_cell_to_column(Pf[:, -1:], no_g)

        _vb_hierarchical_update_parent_Q_from_child(parent, child_upd)
        parent["MDP"] = child_upd
        if _vb_dump_active():
            _entry12_record_phase(mi, t_idx + 1, "post_hierarchical", bundle)


def _vb_build_partial_output(models: list[dict[str, Any]], bundle: dict[str, Any]) -> Any:
    """
    Internal staged return used for recursive child calls before full solver completion.

    Produces a MATLAB-like single-model struct shape from current partial state so
    hierarchical mapping can continue while the top-level function remains stubbed.
    """
    if len(models) != 1:
        return copy.deepcopy(models)
    out = copy.deepcopy(models[0])
    out["id"] = copy.deepcopy(bundle["id"][0])
    # ``~1693–1705``: ``X`` / ``P`` (paths ``S``) already assembled on ``models[0]`` by ``_vb_assemble_mdp_results_1691``.
    out["X"] = [np.asarray(x, dtype=np.float64).copy() for x in models[0]["X"]]
    out["P"] = [np.asarray(x, dtype=np.float64).copy() for x in models[0]["P"]]

    Q_cells: list[np.ndarray] = []
    for f in range(len(bundle["Q"][0])):
        cols = [np.asarray(bundle["Q"][0][f][t], dtype=np.float64).reshape(-1, 1) for t in range(int(bundle["T"]))]
        Q_cells.append(np.hstack(cols))
    out["Q"] = Q_cells
    if "Y" in models[0]:
        out["Y"] = copy.deepcopy(models[0]["Y"])
    if "j" in models[0]:
        out["j"] = copy.deepcopy(models[0]["j"])
    if "i" in models[0]:
        out["i"] = copy.deepcopy(models[0]["i"])
    for _k in ("xn", "wn", "dn", "un"):
        if _k in models[0]:
            out[_k] = copy.deepcopy(models[0][_k])
    if "sn" in models[0]:
        out["sn"] = copy.deepcopy(models[0]["sn"])
    out["_rgms_partial_v"] = 1
    return out


def _entry12_snap_12d(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_label: int,
    mrow: Any,
    *,
    enrich_y_probe: bool = True,
) -> dict[str, Any]:
    md = copy.deepcopy(_vb_dump_mdp_payload(models))
    t_int = int(bundle["T"])
    t_lab = int(t_label)
    # MATLAB ``snapD`` at ``t == T`` is before belief/outcomes at ``T`` (``F`` length ``T-1``).
    if t_lab == t_int:
        ff = md.get("F")
        if isinstance(ff, np.ndarray):
            flat = np.asarray(ff, dtype=np.float64).ravel()
            keep = max(0, t_int - 1)
            if flat.size > keep:
                md["F"] = np.asarray(flat[:keep], dtype=np.float64)
        gg = md.get("G")
        if isinstance(gg, list) and len(gg) > max(0, t_int - 1):
            md["G"] = gg[: max(0, t_int - 1)]
    snap: dict[str, Any] = {
        "t": t_lab,
        "MDP": md,
        "Mrow": np.asarray(mrow, dtype=np.int64).copy(),
    }
    if enrich_y_probe and _vb_capture_y_probe_active() and t_lab == 1:
        snap["entry12_prechild"] = _entry12_prechild_from_models(models)
    return snap


def _entry12_O_at_t(bundle: dict[str, Any], t_idx: int) -> list[list[Any]]:
    """``O{m,g,t}`` slice only (lean 12E boundary)."""
    o_shell = bundle["O"]
    out: list[list[Any]] = []
    for mi, o_mi in enumerate(o_shell):
        row: list[Any] = []
        for g in range(len(o_mi)):
            leaf = o_mi[g][t_idx]
            if isinstance(leaf, np.ndarray):
                row.append(np.asarray(leaf, dtype=np.float64).copy())
            else:
                row.append(copy.deepcopy(leaf))
        out.append(row)
    return out


def _entry12_snap_12e(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_label: int,
    *,
    t_idx: int | None = None,
    enrich_y_probe: bool = True,
) -> dict[str, Any]:
    snap: dict[str, Any] = {"t": int(t_label)}
    if t_idx is not None:
        snap["O"] = _entry12_O_at_t(bundle, t_idx)
    if enrich_y_probe and _vb_capture_y_probe_active():
        snap["nested_y_summary"] = _entry12_nested_y_summary(models)
    return snap


def _entry12_attach_phase_log_to_snap(
    snap: dict[str, Any],
    bundle: dict[str, Any],
    t_1b: int,
    M_row: np.ndarray,
) -> dict[str, Any]:
    if not _vb_dump_active():
        return snap
    mis = [int(mm) - 1 for mm in np.asarray(M_row, dtype=np.int64).ravel() if int(mm) >= 1]
    snap["entry12_phase_log"] = _entry12_build_phase_log(t_1b, mis)
    return snap


_ENTRY12_T_BOUNDARY_KEYS = ("out_t1", "out_t2", "out_t3", "out_tT")


def _entry12_assign_t_boundary(ws: dict[str, Any], snap: dict[str, Any], t_1based: int, t_int: int) -> None:
    """Mirror ``entry12_assign_t_boundary`` in ``spm_MDP_VB_XXX_entry12_dump.m``."""
    if t_1based == 1:
        ws["out_t1"] = snap
    elif t_1based == 2:
        ws["out_t2"] = snap
    elif t_1based == 3:
        ws["out_t3"] = snap
    if t_1based == t_int:
        ws["out_tT"] = snap


def _entry12_snap_12f(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_label: int,
    *,
    include_policy_traces: bool = False,
    enrich_y_probe: bool = True,
) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "t": int(t_label),
        "Q": copy.deepcopy(bundle["Q"]),
        "P": copy.deepcopy(bundle["P"]),
        "MDP": _vb_dump_mdp_payload(models),
    }
    if include_policy_traces:
        snap["R"] = copy.deepcopy(bundle["R_policy"])
        snap["v"] = copy.deepcopy(bundle["v_policy"])
        snap["w"] = copy.deepcopy(bundle["w_policy"])
    if enrich_y_probe and _vb_capture_y_probe_active():
        snap["nested_y_summary"] = _entry12_nested_y_summary(models)
    return snap


def _vb_run_partial_t_loop(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    alpha: float,
    recurse_partial: bool,
    *,
    reuse_matlab_draws: bool = False,
) -> None:
    """Per ``t``: generation → outcomes ~873–949 → ~952–969 → ``BP``/``IP`` → ``spm_forwards`` → belief."""
    M_upd = bundle["M_update"]
    t_int = int(bundle["T"])
    n_depth = int(bundle["N_policy_depth"])
    if _vb_dump_active():
        bundle["entry12_D"] = {
            "in": _entry12_snap_12d(models, bundle, 0, M_upd[0, :]),
        }
        bundle["entry12_E"] = {
            "in": _entry12_snap_12e(models, bundle, 0),
        }
        bundle["entry12_F"] = {
            "in": _entry12_snap_12f(models, bundle, 0, include_policy_traces=False),
        }
    for t_idx in range(t_int):
        t_iter = time.perf_counter()
        row = M_upd[t_idx, :]
        t_1based = t_idx + 1
        _vb_generation_paths_states(models, bundle, t_idx, row)
        if _vb_dump_active():
            _entry12_assign_t_boundary(
                bundle["entry12_D"],
                _entry12_snap_12d(models, bundle, t_1based, row),
                t_1based,
                t_int,
            )
        _vb_share_states_one_t(models, bundle, t_idx, row)
        if _vb_dump_active():
            for mm in np.asarray(row, dtype=np.int64).ravel():
                mi_s = int(mm) - 1
                if mi_s >= 0:
                    _entry12_record_phase(mi_s, t_idx + 1, "post_share", bundle)
        _vb_generate_outcomes_if_options_o(models, bundle, t_idx, row)
        _vb_shared_probabilistic_outcomes(models, bundle, t_idx, row)
        _vb_hierarchical_subordinate_outcomes(
            models,
            bundle,
            t_idx,
            row,
            recurse_partial,
            reuse_matlab_draws=reuse_matlab_draws,
        )
        _vb_fill_O_empty_from_realized_o_at_t(models, bundle, t_idx, row)
        if _vb_dump_active():
            snap_e = _entry12_snap_12e(models, bundle, t_1based, t_idx=t_idx)
            _entry12_attach_phase_log_to_snap(snap_e, bundle, t_1based, row)
            _entry12_assign_t_boundary(
                bundle["entry12_E"],
                snap_e,
                t_1based,
                t_int,
            )
        _vb_fill_BP_IP_at_t(bundle, t_idx)
        t_m = t_idx + 1
        n_horiz = int(min(t_int, t_m + n_depth))
        qa_b = bundle.get("qa")
        for mm in np.asarray(row, dtype=np.int64).ravel():
            if int(mm) < 1:
                continue
            mi = int(mm) - 1
            idm = bundle["id"][mi]
            if _vb_dump_active():
                ex: dict[str, Any] = {"A_peaks": _entry12_a_peaks_for_model(bundle["A"], mi)}
                for key in ("fp", "fu", "iH"):
                    if key in idm:
                        ex[f"id_{key}"] = np.asarray(idm[key], dtype=np.int64).ravel().tolist()
                _entry12_record_phase(mi, t_m, "pre_forwards", bundle, extra=ex)
            G_m, _, F_elbo, _, Pa_step = spm_forwards(
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
                int(mm),
                bundle["id"],
                bundle["pA"],
                qa_b,
            )
            if _vb_dump_active():
                _entry12_record_phase(
                    mi, t_m, "post_forwards", bundle, extra={"F_after_fwd": float(F_elbo)}
                )
            _entry12_attach_vbx_to_model(models, mi, t_m)
            Gw, Zt = _vb_belief_after_forwards(
                mi, bundle, t_m, t_idx, np.asarray(G_m, dtype=np.float64), float(alpha)
            )
            _vb_active_learning_in_loop(mi, models, bundle, t_idx, t_m)
            _vb_ensure_per_t_traces(models, mi, t_int)
            models[mi]["F"][t_idx] = float(F_elbo)
            if _vb_dump_active():
                _entry12_record_phase(
                    mi, t_m, "post_mdp_F", bundle, extra={"F_mdp_slot": float(F_elbo)}
                )
            if isinstance(Gw, (int, float)):
                models[mi]["G"][t_idx] = float(Gw)
            else:
                models[mi]["G"][t_idx] = np.asarray(Gw, dtype=np.float64).copy()
            models[mi]["Z"][t_idx] = float(Zt)
            models[mi]["Pa"] = copy.deepcopy(Pa_step)
            _vb_in_loop_id_ig_and_sn(mi, bundle, t_idx)
            if _vb_monitoring_active():
                t_1based = t_idx + 1
                if t_1based == 1:
                    _vb_monitor_snapshot("12F", models[mi], mi + 1, t_1based, "first")
                if t_1based == t_int:
                    _vb_monitor_snapshot("12F", models[mi], mi + 1, t_1based, "last")

        if _vb_dump_active():
            snap_f = _entry12_snap_12f(models, bundle, t_1based, include_policy_traces=True)
            _entry12_attach_phase_log_to_snap(snap_f, bundle, t_1based, row)
            _entry12_assign_t_boundary(
                bundle["entry12_F"],
                snap_f,
                t_1based,
                t_int,
            )
        if t_idx + 1 == t_int:
            _vb_trim_mdp_o_s_u_at_terminal_horizon(models, bundle)
        _vb_timing_add_12f(time.perf_counter() - t_iter)


def _vb_optional_backwards_replay(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """MATLAB ~1463–1481: optional ``OPTIONS.B`` replay via ``spm_backwards``."""
    if int(options_vb.get("B", 0)) == 0:
        return
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    for mi in range(nm):
        u_row = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
        nf_m = int(bundle["Nf"][mi])
        for f_idx in range(nf_m):
            if f_idx < u_row.size and int(u_row[f_idx]) == 0:
                p_last = copy.deepcopy(bundle["P"][mi][f_idx][t_int - 1])
                for t_idx in range(t_int):
                    bundle["P"][mi][f_idx][t_idx] = copy.deepcopy(p_last)

        Q_upd, P_upd, qa_upd, qb_upd, Fm = spm_backwards(
            bundle["O"],
            bundle["P"],
            bundle["Q"],
            bundle["D"],
            bundle["E"],
            bundle["pa"],
            bundle["pb"],
            bundle["Um"],
            mi + 1,
            bundle["id"],
        )
        bundle["Q"] = Q_upd
        bundle["P"] = P_upd
        bundle["qa"] = qa_upd
        bundle["qb"] = qb_upd
        models[mi]["F"] = np.asarray(Fm, dtype=np.float64).copy()


def _vb_mi_scalar_e(res: Any) -> float:
    """First element of ``spm_MDP_MI`` return (expected free-energy scalar)."""
    e = res[0] if isinstance(res, tuple) else res
    return float(np.asarray(e, dtype=np.float64).reshape(-1)[0])


def _vb_accumulate_dirichlet_parameter_learning(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """
    MATLAB ~1485–1587: accumulate Dirichlet parameters for ``a``/``b``/``c``/``d``/``e``
    and parameter KL terms ``Fa``–``Fe``. Posterior predictive ``Y`` is handled separately.
    """
    eta = float(hp["eta"])
    beta = float(hp["beta"])
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])

    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        nf_m = int(bundle["Nf"][mi])
        id_m = bundle["id"][mi]
        h_row = [bundle["H"][mi][ff] for ff in range(nf_m)]

        if "a" in md:
            for g_idx in range(ng_m):
                pa_mg = bundle["pa"][mi][g_idx]
                qa_mg = bundle["qa"][mi][g_idx]
                c_mg = bundle["C"][mi][g_idx]
                if beta != 0.0:
                    fa = np.zeros((2, 1), dtype=np.float64)
                    fa[0, 0] = _vb_mi_scalar_e(spm_MDP_MI(pa_mg, c_mg, h_row))
                    fa[1, 0] = _vb_mi_scalar_e(spm_MDP_MI(qa_mg, c_mg, h_row))
                    pa_w = spm_softmax(fa, beta)
                else:
                    pa_w = np.array([[0.0], [1.0]], dtype=np.float64)
                blend = (
                    pa_w[0, 0] * np.asarray(pa_mg, dtype=np.float64)
                    + pa_w[1, 0] * np.asarray(qa_mg, dtype=np.float64)
                ) * eta / (eta + pa_w[1, 0])
                ag = md["a"][g_idx]
                if isinstance(ag, (list, tuple)) and len(ag) == 1:
                    md["a"][g_idx] = [np.asarray(blend, dtype=np.float64).copy()]
                else:
                    md["a"][g_idx] = np.asarray(blend, dtype=np.float64).copy()

        if "b" in md:
            for f_idx in range(nf_m):
                pb_mf = bundle["pb"][mi][f_idx]
                qb_mf = bundle["qb"][mi][f_idx]
                h_mf = bundle["H"][mi][f_idx]
                if beta != 0.0:
                    fa_b = np.zeros((2, 1), dtype=np.float64)
                    # MATLAB ``spm_MI(pb,H)``: two-arg call maps to ``spm_MDP_MI``'s ``c`` slot.
                    fa_b[0, 0] = _vb_mi_scalar_e(spm_MDP_MI(pb_mf, h_mf))
                    fa_b[1, 0] = _vb_mi_scalar_e(spm_MDP_MI(qb_mf, h_mf))
                    pa_w = spm_softmax(fa_b, beta)
                else:
                    pa_w = np.array([[0.0], [1.0]], dtype=np.float64)
                blend_b = (
                    pa_w[0, 0] * np.asarray(pb_mf, dtype=np.float64)
                    + pa_w[1, 0] * np.asarray(qb_mf, dtype=np.float64)
                ) * eta / (eta + pa_w[1, 0])
                bf = md["b"][f_idx]
                if isinstance(bf, (list, tuple)) and len(bf) == 1:
                    md["b"][f_idx] = [np.asarray(blend_b, dtype=np.float64).copy()]
                else:
                    md["b"][f_idx] = np.asarray(blend_b, dtype=np.float64).copy()

        if "c" in md:
            for g_1b in np.ravel(spm_children(id_m)).astype(np.int64):
                g_idx = int(g_1b) - 1
                if g_idx < 0 or g_idx >= ng_m:
                    continue
                dc = np.asarray(bundle["O"][mi][g_idx][t_int - 1], dtype=np.float64)
                pc_mg = np.asarray(bundle["pc"][mi][g_idx], dtype=np.float64)
                if dc.size == 0 or pc_mg.size == 0:
                    continue
                dc = dc.reshape(pc_mg.shape) * (pc_mg > 0)
                c_new = (pc_mg + dc) * eta / (eta + 1.0)
                cg = md["c"][g_idx]
                if isinstance(cg, (list, tuple)) and len(cg) == 1:
                    md["c"][g_idx] = [np.asarray(c_new, dtype=np.float64).copy()]
                else:
                    md["c"][g_idx] = np.asarray(c_new, dtype=np.float64).copy()

        if "d" in md:
            for f_idx in range(nf_m):
                dd = np.asarray(bundle["Q"][mi][f_idx][0], dtype=np.float64)
                pd_mf = np.asarray(bundle["pd"][mi][f_idx], dtype=np.float64)
                if dd.size == 0 or pd_mf.size == 0:
                    continue
                dd = dd.reshape(pd_mf.shape) * (pd_mf > 0)
                d_new = (pd_mf + dd) * eta / (eta + 1.0)
                df = md["d"][f_idx]
                if isinstance(df, (list, tuple)) and len(df) == 1:
                    md["d"][f_idx] = [np.asarray(d_new, dtype=np.float64).copy()]
                else:
                    md["d"][f_idx] = np.asarray(d_new, dtype=np.float64).copy()

        if "e" in md:
            for f_idx in range(nf_m):
                de = np.asarray(bundle["P"][mi][f_idx][0], dtype=np.float64)
                pe_mf = np.asarray(bundle["pe"][mi][f_idx], dtype=np.float64)
                if de.size == 0 or pe_mf.size == 0:
                    continue
                de = de.reshape(pe_mf.shape) * (pe_mf > 0)
                e_new = (pe_mf + de) * eta / (eta + 1.0)
                ef = md["e"][f_idx]
                if isinstance(ef, (list, tuple)) and len(ef) == 1:
                    md["e"][f_idx] = [np.asarray(e_new, dtype=np.float64).copy()]
                else:
                    md["e"][f_idx] = np.asarray(e_new, dtype=np.float64).copy()

        learn_any = any(k in md for k in ("a", "b", "c", "d", "e"))
        if learn_any:
            md["Fa"] = np.zeros(ng_m, dtype=np.float64)
            md["Fb"] = np.zeros(nf_m, dtype=np.float64)
            md["Fc"] = np.zeros(ng_m, dtype=np.float64)
            md["Fd"] = np.zeros(nf_m, dtype=np.float64)
            md["Fe"] = np.zeros(nf_m, dtype=np.float64)

            for g_idx in range(ng_m):
                if "a" in md:
                    amg = md["a"][g_idx]
                    amg = amg[0] if isinstance(amg, (list, tuple)) and len(amg) == 1 else amg
                    pam = bundle["pa"][mi][g_idx]
                    md["Fa"][g_idx] = -float(
                        spm_KL_dir(np.asarray(amg, dtype=np.float64), np.asarray(pam, dtype=np.float64))
                    )
                if "c" in md:
                    cmg = md["c"][g_idx]
                    cmg = cmg[0] if isinstance(cmg, (list, tuple)) and len(cmg) == 1 else cmg
                    pcm = bundle["pc"][mi][g_idx]
                    md["Fc"][g_idx] = -float(
                        spm_KL_dir(np.asarray(cmg, dtype=np.float64), np.asarray(pcm, dtype=np.float64))
                    )

            for f_idx in range(nf_m):
                if "b" in md:
                    bmf = md["b"][f_idx]
                    bmf = bmf[0] if isinstance(bmf, (list, tuple)) and len(bmf) == 1 else bmf
                    pbm = bundle["pb"][mi][f_idx]
                    md["Fb"][f_idx] = -float(
                        spm_KL_dir(np.asarray(bmf, dtype=np.float64), np.asarray(pbm, dtype=np.float64))
                    )
                if "d" in md:
                    dmf = md["d"][f_idx]
                    dmf = dmf[0] if isinstance(dmf, (list, tuple)) and len(dmf) == 1 else dmf
                    pdm = bundle["pd"][mi][f_idx]
                    md["Fd"][f_idx] = -float(
                        spm_KL_dir(np.asarray(dmf, dtype=np.float64), np.asarray(pdm, dtype=np.float64))
                    )
                if "e" in md:
                    emf = md["e"][f_idx]
                    emf = emf[0] if isinstance(emf, (list, tuple)) and len(emf) == 1 else emf
                    pem = bundle["pe"][mi][f_idx]
                    md["Fe"][f_idx] = -float(
                        spm_KL_dir(np.asarray(emf, dtype=np.float64), np.asarray(pem, dtype=np.float64))
                    )


def _vb_q_row_for_parents(Qmi: list, t_idx: int) -> list:
    """MATLAB ``Q(m,:,t)`` as a list of length ``Nf`` (one entry per factor)."""
    return [Qmi[ff][t_idx] for ff in range(len(Qmi))]


def _vb_ag_for_posterior_predictive(
    md: dict[str, Any],
    bundle: dict[str, Any],
    mi: int,
    g_idx: int,
) -> np.ndarray:
    """Workspace ``A{m,g}`` for ``OPTIONS.Y`` (~1654); not input ``MDP(m).A{g}`` left unchanged in MATLAB."""
    _ = md
    Ag = bundle["A"][mi][g_idx]
    Ag = _unwrap_gp_elem(Ag)
    if isinstance(Ag, (list, tuple)) and len(Ag) == 1:
        Ag = Ag[0]
    if callable(Ag):
        raise NotImplementedError(
            "spm_MDP_VB_XXX: OPTIONS.Y with likelihood function_handle A{g} is not translated yet"
        )
    arr = np.asarray(Ag, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1, order="F")
    return arr


def _vb_q_list_at_mt(bundle_q_mi: list, j_dom: Any, t_idx: int) -> list[np.ndarray]:
    """MATLAB ``Q(m,j,t)`` as column vectors for ``spm_dot``."""
    j_arr = np.atleast_1d(np.asarray(_unwrap_id_a_entry(j_dom), dtype=np.int64).ravel())
    out: list[np.ndarray] = []
    for jj in j_arr.tolist():
        ji = int(jj)
        if ji < 1 or ji > len(bundle_q_mi):
            continue
        col = np.asarray(bundle_q_mi[ji - 1][t_idx], dtype=np.float64)
        out.append(col.reshape(-1, 1, order="F"))
    return out


def _vb_posterior_predictive_Y(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """MATLAB ~1591–1606: optional posterior predictive ``Y`` plus ``j`` / ``i`` bookkeeping."""
    if int(options_vb.get("Y", 0)) == 0:
        return
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        if ng_m <= 0:
            continue
        # MATLAB ``MDP.Y{o,t}`` — first index is outcome modality ``o`` (1..``Ng``), not ``max(No)``.
        md["Y"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        md["j"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        md["i"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        id_m = bundle["id"][mi]
        for g_1b in range(1, ng_m + 1):
            g_idx = g_1b - 1
            Ag = _vb_ag_for_posterior_predictive(md, bundle, mi, g_idx)
            for t_idx in range(t_int):
                Qrow = _vb_q_row_for_parents(bundle["Q"][mi], t_idx)
                j, i_ch = spm_parents(id_m, g_1b, Qrow)
                j_store = _unwrap_id_a_entry(j)
                j_arr = np.atleast_1d(np.asarray(j_store, dtype=np.float64).ravel())
                if j_arr.size == 1:
                    md["j"][g_idx][t_idx] = float(j_arr[0])
                else:
                    md["j"][g_idx][t_idx] = copy.deepcopy(j_store)
                i_arr = np.atleast_1d(np.asarray(i_ch, dtype=np.float64).ravel())
                if i_arr.size == 1:
                    md["i"][g_idx][t_idx] = float(i_arr[0])
                else:
                    md["i"][g_idx][t_idx] = copy.deepcopy(i_ch)
                q_list = _vb_q_list_at_mt(bundle["Q"][mi], j, t_idx)
                pred = np.asarray(spm_dot(Ag, q_list), dtype=np.float64).reshape(-1, 1)
                for o in i_arr.tolist():
                    o_int = int(np.round(float(o)))
                    if o_int < 1 or o_int > ng_m:
                        continue
                    md["Y"][o_int - 1][t_idx] = pred.copy()
        _entry12_probe_y_fill_all(models, bundle, options_vb)


def _vb_reorganize_X_S_from_QP(bundle: dict[str, Any]) -> None:
    """MATLAB ~1613–1617: ``X{m,f}(:,t) = Q{m,f,t}``, ``S{m,f}(:,t) = P{m,f,t}``."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    for mi in range(nm):
        nf_m = int(bundle["Nf"][mi])
        for f_idx in range(nf_m):
            Xmf = bundle["X"][mi][f_idx]
            Smf = bundle["S"][mi][f_idx]
            nrx, ncx = Xmf.shape
            nrs, ncs = Smf.shape
            for t_idx in range(t_int):
                qcol = np.asarray(bundle["Q"][mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1)
                pcol = np.asarray(bundle["P"][mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1)
                if qcol.shape[0] == nrx and ncx > t_idx:
                    Xmf[:, t_idx : t_idx + 1] = qcol
                if pcol.shape[0] == nrs and ncs > t_idx:
                    Smf[:, t_idx : t_idx + 1] = pcol


def _vb_options_N_neural_simulated_responses(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """MATLAB ~1623–1688: simulated electrophysiological responses when ``OPTIONS.N``."""
    if int(options_vb.get("N", 0)) == 0:
        return

    n = 16
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    Np_arr = bundle["Np"]
    Ns_arr = bundle["Ns"]

    for mi in range(nm):
        md = models[mi]
        nf_m = int(bundle["Nf"][mi])
        npp = int(Np_arr[mi])
        w_row = np.asarray(bundle["w_policy"][mi], dtype=np.float64).reshape(-1)
        R_mat = np.asarray(bundle["R_policy"][mi], dtype=np.float64)
        if R_mat.ndim == 1:
            R_mat = R_mat.reshape(-1, 1)

        h_exp = np.exp(-(np.arange(n, dtype=np.float64)) / 2.0)
        h_exp = h_exp / np.sum(h_exp)
        hz = np.asarray(spm_zeros(h_exp.reshape(-1, 1)), dtype=np.float64).ravel()
        kern = np.concatenate([hz, h_exp.ravel()])
        wn = np.kron(w_row.reshape(1, -1), np.ones((1, n))).ravel()
        wn = np.convolve(wn, kern, mode="same")
        dn = np.gradient(wn.astype(np.float64))

        x_axis = np.arange(0, n, dtype=np.float64)
        h_gamma = np.asarray(spm_Gcdf(x_axis, float(n) / 4.0, 1.0), dtype=np.float64).ravel()
        if h_gamma.size != n:
            h_gamma = np.reshape(h_gamma, (-1,))[:n]

        xn_cells: list[np.ndarray] = []
        for f_idx in range(nf_m):
            ns_mf = int(Ns_arr[mi, f_idx])
            xnf = np.zeros((n, ns_mf, t_int, t_int), dtype=np.float64)
            snmf = bundle["sn"][mi][f_idx]
            if snmf is None:
                snmf = np.zeros((max(1, ns_mf), t_int, t_int), dtype=np.float64)
            for ii in range(ns_mf):
                for j in range(t_int):
                    for k in range(t_int):
                        if k == 0:
                            h0 = 1.0 / max(ns_mf, 1)
                        else:
                            h0 = float(snmf[ii, j, k - 1])
                        ht = float(snmf[ii, j, k])
                        xnf[:, ii, j, k] = h_gamma * (ht - h0) + h0
            xn_cells.append(xnf)

        # MATLAB ~1663–1670: ``f`` left over from last ``for f = 1:Nf(m)`` loop is ``Nf(m)`` only.
        f_last = nf_m - 1
        xnf_last = xn_cells[f_last]
        for i in range(n):
            for j in range(t_int):
                for k in range(t_int):
                    row = xnf_last[i, :, j, k].reshape(-1, 1)
                    xnf_last[i, :, j, k] = np.asarray(_spm_norm(row), dtype=np.float64).ravel()
        xn_cells[f_last] = xnf_last

        u0 = np.asarray(spm_softmax(np.ones((max(npp, 1), 1))), dtype=np.float64).reshape(-1, 1)
        un_m = np.zeros((npp, max((t_int - 1) * n, 1)), dtype=np.float64)
        for k_pol in range(npp):
            for t_m in range(1, t_int):
                if t_m == 1:
                    h0 = float(u0[k_pol, 0])
                else:
                    h0 = float(R_mat[k_pol, t_m - 2])
                ht = float(R_mat[k_pol, t_m - 1])
                jcols = np.arange(n, dtype=np.int64) + (t_m - 1) * n
                un_m[k_pol, jcols] = h_gamma * (ht - h0) + h0

        md["xn"] = xn_cells
        md["wn"] = np.asarray(wn, dtype=np.float64).copy()
        md["dn"] = np.asarray(dn, dtype=np.float64).copy()
        md["un"] = np.asarray(un_m, dtype=np.float64).copy()


def _vb_shiftdim_o_ng_t_cells(O_mi: list[list[Any]], ng: int, t_int: int) -> list[list[Any]]:
    """
    MATLAB ``shiftdim(O, 1)`` on an ``Ng×T`` cell block → ``T×Ng`` (same cells, permuted indices).

    Internal ``O{m,g,t}`` uses Python layout ``O_mi[g][t]``; returned layout is ``out[t][g]``.
    """
    return [[copy.deepcopy(O_mi[g][t]) for g in range(ng)] for t in range(t_int)]


def _vb_normalize_AB_from_ab_if_missing(md: dict[str, Any], ng_m: int, nf_m: int) -> None:
    """MATLAB ~1710–1718: fill ``A``/``B`` from Dirichlet ``a``/``b`` when explicit tensors absent."""
    if "a" in md and "A" not in md:
        md["A"] = []
        for g_idx in range(ng_m):
            ag = md["a"][g_idx]
            ag = ag[0] if isinstance(ag, (list, tuple)) and len(ag) == 1 else ag
            md["A"].append(np.asarray(_spm_norm(np.asarray(ag, dtype=np.float64)), dtype=np.float64).copy())
    if "b" in md and "B" not in md:
        md["B"] = []
        for f_idx in range(nf_m):
            bf = md["b"][f_idx]
            bf = bf[0] if isinstance(bf, (list, tuple)) and len(bf) == 1 else bf
            md["B"].append(np.asarray(_spm_norm(np.asarray(bf, dtype=np.float64)), dtype=np.float64).copy())


def _vb_assemble_mdp_results_1691(models: list[dict[str, Any]], bundle: dict[str, Any]) -> None:
    """
    MATLAB ~1691–1718 (plus ~1721–1730 when ``OPTIONS.N`` filled ``xn``/``un``/``wn``/``dn`` on ``md``): populate ``MDP(m)``
    fields before plot/aux sections.

    Uses bundle ``R_policy`` / ``v_policy`` / ``w_policy`` (belief bookkeeping), ``V`` as policies ``U``,
    ``shiftdim`` on ``O``, and optional ``A``/``B`` from ``a``/``b``.
    """
    nm = int(bundle["Nm"])
    for mi in range(nm):
        if _vb_monitoring_active():
            _vb_monitor_snapshot("12H", models[mi], mi + 1, None, "first")
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        ng_out = min(len(bundle["O"][mi]), max(ng_m, int(bundle["NG"][mi])))
        nf_m = int(bundle["Nf"][mi])
        t_int = int(bundle["T"])
        md["T"] = float(t_int)
        V_mi = bundle["V"][mi]
        if int(V_mi.shape[0]) > 0:
            md["U"] = copy.deepcopy(V_mi)
        else:
            # ``V{m}`` is 0×Nf when ``Np==0``; nested dumps still carry generative ``MDP.U`` (1×Nf).
            U_gen = _vb_mdp_U_as_float_array(md)
            if U_gen.ndim == 1:
                U_gen = U_gen.reshape(1, -1)
            if U_gen.size:
                md["U"] = sparse.csr_matrix(np.asarray(U_gen, dtype=np.float64))
            else:
                md["U"] = copy.deepcopy(V_mi)
        md["R"] = np.asarray(bundle["R_policy"][mi], dtype=np.float64).copy()
        # MATLAB ~1663–1673: ``S{m,f}(:,t) = P{m,f,t}``, ``X{m,f}(:,t) = Q{m,f,t}`` before ``MDP.P`` / ``MDP.X``.
        t_asm = int(bundle["T"])
        for f_idx in range(nf_m):
            p_cols = [
                np.asarray(bundle["P"][mi][f_idx][t], dtype=np.float64).reshape(-1, 1)
                for t in range(t_asm)
            ]
            q_cols = [
                np.asarray(bundle["Q"][mi][f_idx][t], dtype=np.float64).reshape(-1, 1)
                for t in range(t_asm)
            ]
            if p_cols:
                bundle["S"][mi][f_idx] = np.asfortranarray(np.hstack(p_cols))
            if q_cols:
                bundle["X"][mi][f_idx] = np.asfortranarray(np.hstack(q_cols))
        md["X"] = [np.asarray(bundle["X"][mi][f], dtype=np.float64).copy() for f in range(nf_m)]
        md["P"] = [np.asarray(bundle["S"][mi][f], dtype=np.float64).copy() for f in range(nf_m)]
        # ``shiftdim(O,1)`` (~1764): include ``g=1:NG(m)`` slots written in ~919–985, not ``Ng`` only.
        md["O"] = _vb_shiftdim_o_ng_t_cells(bundle["O"][mi], ng_out, t_int)
        md["v"] = np.asarray(bundle["v_policy"][mi], dtype=np.float64).reshape(1, -1).copy()
        md["w"] = np.asarray(bundle["w_policy"][mi], dtype=np.float64).reshape(1, -1).copy()
        md["id"] = copy.deepcopy(bundle["id"][mi])
        opts_a = bundle.get("options_vb", _default_options_vb())
        if int(opts_a.get("N", 0)) != 0 and "sn" in bundle:
            md["sn"] = [
                copy.deepcopy(bundle["sn"][mi][f]) if bundle["sn"][mi][f] is not None else None
                for f in range(nf_m)
            ]
        _vb_normalize_AB_from_ab_if_missing(md, ng_m, nf_m)
        if _vb_monitoring_active():
            _vb_monitor_snapshot("12H", models[mi], mi + 1, None, "last")


def _vb_init_QXSP_outcomes_and_process(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options: dict[str, Any],
    chi: float,
) -> dict[str, Any]:
    """
    MATLAB ~652–733: ``Q``/``X``/``S``/``P``/``sn``, ``s``/``u``/``o`` matrices,
    probabilistic ``O`` outcome sampling, ``GP`` ``GV``/``chi`` on process models.
    """
    nm = int(bundle["Nm"])
    Ng = bundle["Ng"]
    Nf = bundle["Nf"]
    NF = bundle["NF"]
    Ns = bundle["Ns"]
    D_t = bundle["D"]
    E_t = bundle["E"]
    O_shell = bundle["O"]
    proc = bundle["process"]

    t_int = int(bundle["T"])

    Q: list[list[list[Any]]] = []
    X: list[list[np.ndarray]] = []
    S: list[list[np.ndarray]] = []
    P: list[list[list[Any]]] = []
    sn: list[list[np.ndarray | None]] = []
    opt_neural = int(options.get("N", 0)) != 0

    for m in range(nm):
        md = models[m]
        nf_m = int(Nf[m])
        ng_m = int(Ng[m])
        nf_proc = int(NF[m])

        Q.append([])
        X.append([])
        S.append([])
        P.append([])
        sn.append([])

        for f_idx in range(nf_m):
            Dmf = D_t[m][f_idx]
            Emf = E_t[m][f_idx]
            D_arr = np.asarray(Dmf, dtype=np.float64) if Dmf is not None else np.zeros((0, 0), dtype=np.float64)
            E_arr = np.asarray(Emf, dtype=np.float64) if Emf is not None else np.zeros((0, 0), dtype=np.float64)

            Q[m].append([copy.deepcopy(Dmf) for _ in range(t_int)])

            if D_arr.size == 0:
                Xmf = np.zeros((0, t_int), dtype=np.float64)
            else:
                dcol = np.asarray(D_arr.reshape(-1, 1, order="F"), dtype=np.float64)
                Xmf = np.tile(dcol, (1, t_int))
            X[m].append(Xmf)

            if E_arr.size == 0:
                Smf = np.zeros((0, t_int), dtype=np.float64)
            else:
                ecol = np.asarray(E_arr.reshape(-1, 1, order="F"), dtype=np.float64)
                Smf = np.tile(ecol, (1, t_int))
            S[m].append(Smf)

            if opt_neural:
                ns_mf = int(Ns[m, f_idx])
                if ns_mf > 0:
                    sn_mf = np.zeros((ns_mf, t_int, t_int), dtype=np.float64) + (1.0 / ns_mf)
                else:
                    sn_mf = np.zeros((0, t_int, t_int), dtype=np.float64)
                sn[m].append(sn_mf)
            else:
                sn[m].append(None)

            P[m].append([copy.deepcopy(Emf) for _ in range(t_int)])

        _vb_mdp_field_matrix(md, "s", nf_proc, t_int)
        _vb_mdp_field_matrix(md, "u", nf_proc, t_int)
        # ``MDP(m).o`` is ``Ng×T`` (~725); generation loops ``g=1:NG(m)`` (~919) and indexes ``n(o,t)``.
        ng_o_rows = max(ng_m, int(bundle["NG"][m]))
        _vb_mdp_field_matrix(md, "o", ng_o_rows, t_int)

        # ``spm_MDP_VB_XXX.m`` ~732–752 (band 12B): probabilistic ``MDP(m).O{g,t}`` only.
        # Hierarchical child after ``mdp.S→O`` (~1189–1191) carries a dense matrix, not ``O{g,t}``;
        # skip this block so ``O{m,g,t}`` stay empty until outcome generation (~913+), as in MATLAB
        # ``catch`` (~747–748). See ``_vb_mdp_O_is_cell_gt_layout``.
        if "O" in md and _vb_mdp_O_is_cell_gt_layout(md["O"], ng_m, t_int):
            # ``spm_MDP_VB_XXX.m`` ~732–752: load ``O{m,g,t}`` from ``MDP(m).O{g,t}`` only.
            options["O"] = False  # ~735 (inside block; generation ~913+ skipped until loaded)
            O_src = md["O"]
            for g_idx in range(ng_m):
                for t_idx in range(t_int):
                    try:
                        entry = _get_mdp_O_gt(O_src, g_idx, t_idx)  # ~741 ``MDP(m).O{g,t}``
                        O_shell[m][g_idx][t_idx] = entry
                        md["o"][g_idx, t_idx] = float(_spm_sample(entry))  # ~745
                    except Exception:
                        O_shell[m][g_idx][t_idx] = []  # ~748
                        options["O"] = True  # ~749 ``catch`` → fill via ~913–985

        if _vb_monitoring_active():
            _vb_monitor_snapshot("12B", models[m], m + 1, None, "last")

    for m in range(nm):
        if proc[m] > 0:
            models[m]["GV"] = bundle["GV"][m]
            models[m]["chi"] = chi

    return {"Q": Q, "X": X, "S": S, "P": P, "sn": sn}


def _any_u_factor_cols(U: np.ndarray, factor_cols_1based: np.ndarray) -> bool:
    """MATLAB ``any(MDP.U(:,f))`` for columns ``f`` (1-based)."""
    fc = np.asarray(factor_cols_1based, dtype=np.int64).ravel()
    if fc.size == 0:
        return False
    cols = fc - 1
    uu = np.asarray(U, dtype=np.float64)
    if uu.ndim == 1:
        uu = uu.reshape(1, -1)
    return bool(np.any(uu[:, cols]))


def _vb_tensors_through_H(
    models: list[dict],
    nm: int,
    t_h: float,
) -> dict[str, Any]:
    """
    MATLAB ~302–652: GP/id sizing, allocate ``O`` / likelihood / transition tensors through ``H``,
    then ``id`` domains / ``GV`` / ``V`` / ``spm_combinations``.

    Stops before ``Q`` / ``X`` / ``S`` / ``P`` (call ``_vb_init_QXSP_outcomes_and_process`` in the entrypoint).
    """
    proc = np.array([1.0 if _spm_is_process(models[m]) else 0.0 for m in range(nm)])
    gp: list[dict[str, Any]] = [{} for _ in range(nm)]
    id_list: list[dict[str, Any]] = []
    ID_list: list[dict[str, Any]] = []

    Ng = np.zeros(nm, dtype=np.int64)
    Nf = np.zeros(nm, dtype=np.int64)
    NG = np.zeros(nm, dtype=np.int64)
    NF = np.zeros(nm, dtype=np.int64)

    max_guess_ng = 1
    max_guess_nf = 1
    for m in range(nm):
        md = models[m]
        max_guess_ng = max(max_guess_ng, len(md.get("A", [])))
        max_guess_nf = max(max_guess_nf, len(md.get("B", [])))

    No = np.zeros((nm, max_guess_ng), dtype=np.int64)
    Ns = np.zeros((nm, max_guess_nf), dtype=np.int64)
    Nu = np.zeros((nm, max_guess_nf), dtype=np.int64)
    NS = np.zeros((nm, max_guess_nf), dtype=np.int64)
    NU = np.zeros((nm, max_guess_nf), dtype=np.int64)

    for m in range(nm):
        if _vb_monitoring_active():
            _vb_monitor_snapshot("12B", models[m], m + 1, None, "first")
        md = models[m]
        gpm = gp[m]
        if proc[m] > 0:
            # ``GP(m).A`` is fixed at init in MATLAB (~343–345); workspace ``A{m,g}`` updates (~1424).
            gpm["A"] = copy.deepcopy(md["GA"])
            gpm["B"] = copy.deepcopy(md["GB"])
            gpm["U"] = copy.deepcopy(md["GU"])
            id_m = copy.deepcopy(md["id"])
            id_list.append(id_m)
            if "ID" in md:
                ID_m = copy.deepcopy(md["ID"])
            else:
                n_g = len(gpm["A"])
                NG[m] = n_g
                ID_m = {
                    "g": [np.arange(1, n_g + 1, dtype=np.int64)],
                    "A": [],
                }
                for g_idx in range(n_g):
                    Ag = gpm["A"][g_idx]
                    Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
                    nda = int(matlab_ndims(np.asarray(Ag)))
                    ID_m["A"].append(np.arange(1, nda, dtype=np.int64))
                md["ID"] = ID_m
            ID_list.append(copy.deepcopy(md["ID"]))
        else:
            gpm["A"] = copy.deepcopy(md["A"])
            gpm["B"] = copy.deepcopy(md["B"])
            gpm["D"] = copy.deepcopy(md["D"])
            gpm["E"] = copy.deepcopy(md["E"])
            gpm["U"] = copy.deepcopy(md["U"])
            id_m = copy.deepcopy(md["id"])
            id_list.append(id_m)
            ID_m = copy.deepcopy(md["id"])
            ID_list.append(ID_m)

        Ng[m] = len(md["A"])
        Nf[m] = len(md["B"])
        NG[m] = len(gpm["A"])
        NF[m] = len(gpm["B"])

        for g_idx in range(int(Ng[m])):
            Ag = md["A"][g_idx]
            Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
            No[m, g_idx] = int(np.asarray(Ag).shape[0])
        for f_idx in range(int(Nf[m])):
            Bg = md["B"][f_idx]
            Bg = Bg[0] if isinstance(Bg, list) and len(Bg) == 1 else Bg
            Barr = np.asarray(Bg)
            Ns[m, f_idx] = int(Barr.shape[0])
            Nu[m, f_idx] = _b_nu_third_dim(Barr)

        for f_idx in range(int(NF[m])):
            GBf = gpm["B"][f_idx]
            GBf = GBf[0] if isinstance(GBf, list) and len(GBf) == 1 else GBf
            Barr = np.asarray(GBf)
            NS[m, f_idx] = int(Barr.shape[0])
            NU[m, f_idx] = _b_nu_third_dim(Barr)

        if proc[m] > 0:
            if "GD" in md:
                gpm["D"] = md["GD"]
            else:
                gpm["D"] = []
                for _ in range(int(NF[m])):
                    gpm["D"].append(None)
                for f_idx in range(int(NF[m])):
                    gpm["D"][f_idx] = _spm_norm(np.ones((int(NS[m, f_idx]), 1), dtype=np.float64))
            if "GE" in md:
                gpm["E"] = md["GE"]
            else:
                gpm["E"] = []
                for _ in range(int(NF[m])):
                    gpm["E"].append(None)
                for f_idx in range(int(NF[m])):
                    gpm["E"][f_idx] = _spm_norm(np.ones((int(NU[m, f_idx]), 1), dtype=np.float64))

    max_ng = int(np.max(Ng))
    max_nf = int(np.max(Nf))
    t_int = max(1, int(round(float(t_h))))

    O = [[[None for _ in range(t_int)] for _ in range(max_ng)] for _ in range(nm)]

    def cell_nm_ng() -> list[list[Any]]:
        return [[None for _ in range(max_ng)] for _ in range(nm)]

    def cell_nm_nf() -> list[list[Any]]:
        return [[None for _ in range(max_nf)] for _ in range(nm)]

    A_t = cell_nm_ng()
    qa_t = cell_nm_ng()
    pa_t = cell_nm_ng()
    C_t = cell_nm_ng()
    qc_t = cell_nm_ng()
    pc_t = cell_nm_ng()
    K_t = cell_nm_ng()
    W_t = cell_nm_ng()

    B_t = cell_nm_nf()
    qb_t = cell_nm_nf()
    pb_t = cell_nm_nf()
    D_t = cell_nm_nf()
    qd_t = cell_nm_nf()
    pd_t = cell_nm_nf()
    E_t = cell_nm_nf()
    qe_t = cell_nm_nf()
    pe_t = cell_nm_nf()
    H_t = cell_nm_nf()
    qh_t = cell_nm_nf()
    ph_t = cell_nm_nf()
    I_t = cell_nm_nf()

    pA_rows: list[list[Any]] = []

    for m in range(nm):
        md = models[m]
        ng_m = int(Ng[m])
        nf_m = int(Nf[m])

        if "pA" in md:
            pA_rows.append(copy.deepcopy(md["pA"]))
        else:
            pA_rows.append([None] * ng_m)

        U_arr = _vb_mdp_U_as_float_array(md)

        for g_idx in range(ng_m):
            id_ag = _unwrap_id_a_entry(md["id"]["A"][g_idx])
            f_parents = np.asarray(id_ag, dtype=np.int64).ravel()

            if "a" in md:
                qa_mg = md["a"][g_idx]
                qa_mg = qa_mg[0] if isinstance(qa_mg, list) and len(qa_mg) == 1 else qa_mg
            else:
                Ag = md["A"][g_idx]
                Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
                if sparse.issparse(Ag):
                    qa_mg = _vb_as_float64_array(Ag) * 512.0
                else:
                    Ag_arr = np.asarray(Ag)
                    if np.issubdtype(Ag_arr.dtype, np.number) and Ag_arr.dtype != bool:
                        qa_mg = Ag_arr.astype(np.float64) * 512.0
                    else:
                        qa_mg = Ag

            # MATLAB ~482–486: ``pa{m,g}=qa{m,g}`` then ``A{m,g}=spm_norm(qa{m,g})`` in place.
            qa_ws = np.asarray(qa_mg, dtype=np.float64)
            if not qa_ws.flags.writeable:
                qa_ws = np.asarray(qa_mg, dtype=np.float64).copy(order="F")
            _spm_norm_inplace(qa_ws)
            if "A" in md:
                Agf = md["A"][g_idx]
                Agf = Agf[0] if isinstance(Agf, list) and len(Agf) == 1 else Agf
                if isinstance(Agf, np.ndarray) and Agf.dtype == bool:
                    qa_ws = qa_ws.astype(bool)
            if "a" in md:
                slot = md["a"][g_idx]
                if isinstance(slot, list) and len(slot) == 1:
                    slot[0] = qa_ws
                else:
                    md["a"][g_idx] = qa_ws
            pa_t[m][g_idx] = qa_ws
            qa_t[m][g_idx] = qa_ws
            A_t[m][g_idx] = qa_ws

            if _any_u_factor_cols(U_arr, f_parents):
                W_t[m][g_idx] = _spm_wnorm(qa_ws)
                K_t[m][g_idx] = _spm_hnorm(qa_ws)

            if "c" in md:
                qc_m = md["c"][g_idx]
                qc_m = qc_m[0] if isinstance(qc_m, list) and len(qc_m) == 1 else qc_m
            elif "C" in md:
                Cg = md["C"][g_idx]
                Cg = Cg[0] if isinstance(Cg, list) and len(Cg) == 1 else Cg
                qc_m = _vb_as_float64_array(Cg) * 512.0
            else:
                qc_m = np.zeros((0, 0), dtype=np.float64)

            qc_t[m][g_idx] = qc_m
            pc_t[m][g_idx] = qc_m

            if isinstance(qc_m, np.ndarray) and qc_m.size == 0:
                C_t[m][g_idx] = qc_m
            else:
                C_t[m][g_idx] = _spm_norm(qc_m)

        for f_idx in range(nf_m):
            if "b" in md:
                qb_m = md["b"][f_idx]
                qb_m = qb_m[0] if isinstance(qb_m, list) and len(qb_m) == 1 else qb_m
            else:
                Bg = md["B"][f_idx]
                Bg = Bg[0] if isinstance(Bg, list) and len(Bg) == 1 else Bg
                qb_m = _vb_as_float64_array(Bg) * 512.0

            qb_t[m][f_idx] = qb_m
            pb_t[m][f_idx] = qb_m

            B_norm = _spm_norm(qb_m)
            if "B" in md:
                Bgf = md["B"][f_idx]
                Bgf = Bgf[0] if isinstance(Bgf, list) and len(Bgf) == 1 else Bgf
                if isinstance(Bgf, np.ndarray) and Bgf.dtype == bool:
                    B_norm = B_norm.astype(bool)
            B_t[m][f_idx] = B_norm

            if "b" in md:
                if bool(np.any(U_arr[:, f_idx])):
                    qb_src = md["b"][f_idx]
                    qb_src = qb_src[0] if isinstance(qb_src, list) and len(qb_src) == 1 else qb_src
                    I_t[m][f_idx] = _spm_wnorm(qb_src)

            if "d" in md:
                qd_m = md["d"][f_idx]
                qd_m = qd_m[0] if isinstance(qd_m, list) and len(qd_m) == 1 else qd_m
            elif "D" in md:
                Dg = md["D"][f_idx]
                Dg = Dg[0] if isinstance(Dg, list) and len(Dg) == 1 else Dg
                qd_m = _vb_as_float64_array(Dg) * 512.0
            else:
                qd_m = np.ones((int(Ns[m, f_idx]), 1), dtype=np.float64)

            qd_t[m][f_idx] = qd_m
            pd_t[m][f_idx] = qd_m
            D_t[m][f_idx] = _spm_norm(qd_m)

            if "e" in md:
                qe_m = md["e"][f_idx]
                qe_m = qe_m[0] if isinstance(qe_m, list) and len(qe_m) == 1 else qe_m
            elif "E" in md:
                Eg = md["E"][f_idx]
                Eg = Eg[0] if isinstance(Eg, list) and len(Eg) == 1 else Eg
                qe_m = _vb_as_float64_array(Eg) * 512.0
            else:
                qe_m = np.ones((int(Nu[m, f_idx]), 1), dtype=np.float64)

            qe_t[m][f_idx] = qe_m
            pe_t[m][f_idx] = qe_m
            E_t[m][f_idx] = _spm_norm(qe_m)

            if "h" in md:
                qh_m = md["h"][f_idx]
                qh_m = qh_m[0] if isinstance(qh_m, list) and len(qh_m) == 1 else qh_m
            elif _vb_isfield_mdp_array(models, "H"):
                Hg = _vb_mdp_factor_field(md, "H", f_idx)
                qh_m = _vb_as_float64_array(Hg) * 512.0
            else:
                qh_m = np.zeros((0, 0), dtype=np.float64)

            qh_t[m][f_idx] = qh_m
            ph_t[m][f_idx] = qh_m

            if isinstance(qh_m, np.ndarray) and qh_m.size == 0:
                H_t[m][f_idx] = qh_m
            else:
                H_t[m][f_idx] = _spm_norm(qh_m)

    pol = _vb_id_and_policy_blocks(
        nm=nm,
        models=models,
        Ng=Ng,
        Nf=Nf,
        NF=NF,
        NU=NU,
        Nu=Nu,
        K_t=K_t,
        W_t=W_t,
        H_t=H_t,
        I_t=I_t,
        gp=gp,
        id_list=id_list,
        ID_list=ID_list,
    )

    return {
        "Nm": nm,
        "T": t_int,
        "Ng": Ng,
        "Nf": Nf,
        "No": No,
        "Ns": Ns,
        "Nu": Nu,
        "NG": NG,
        "NF": NF,
        "NS": NS,
        "NU": NU,
        "process": proc,
        "gp": gp,
        "id": id_list,
        "ID": ID_list,
        "O": O,
        "A": A_t,
        "qa": qa_t,
        "pa": pa_t,
        "C": C_t,
        "qc": qc_t,
        "pc": pc_t,
        "K": K_t,
        "W": W_t,
        "B": B_t,
        "qb": qb_t,
        "pb": pb_t,
        "D": D_t,
        "qd": qd_t,
        "pd": pd_t,
        "E": E_t,
        "qe": qe_t,
        "pe": pe_t,
        "H": H_t,
        "qh": qh_t,
        "ph": ph_t,
        "I": I_t,
        "pA": pA_rows,
        **pol,
    }


def _spm_MDP_update(mdp: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    """
    File-local ``spm_MDP_update`` from ``spm_MDP_VB_XXX.m`` (~2821–2843).

    Moves Dirichlet parameters from prior-trial ``OUT`` into the next-trial ``MDP``.
    """
    mdp = copy.deepcopy(mdp)
    for key in ("a", "b", "c", "d", "e"):
        if key in out:
            mdp[key] = copy.deepcopy(out[key])
    nested_mdp = out.get("mdp")
    if nested_mdp is not None and "MDP" in mdp:
        child = mdp["MDP"]
        if isinstance(child, list) and child:
            child0 = child[0]
        else:
            child0 = child
        if isinstance(child0, dict) and isinstance(nested_mdp, list) and nested_mdp:
            last_out = nested_mdp[-1]
            if isinstance(last_out, dict):
                for key in ("a", "b", "c", "d", "e"):
                    if key in last_out:
                        child0[key] = copy.deepcopy(last_out[key])
    return mdp


def spm_MDP_VB_XXX(
    mdp_in: Any,
    options: Any | None = None,
    *,
    monitoring: bool = False,
    dump_subentries: bool = False,
    reuse_matlab_draws: bool = False,
) -> Any:
    """
    FORMAT ``MDP = spm_MDP_VB_XXX(MDP, OPTIONS)``

    Pass 1: OPTIONS, ``spm_MDP_checkX``, GP/id sizing, likelihood / transition tensors through ``H``,
    ``id`` / ``ID`` domains, ``GV`` / ``V`` policies, ``Q`` / ``X`` / ``S`` / ``P`` / ``sn``,
    ``s`` / ``u`` / ``o``, probabilistic ``O`` sampling, process-model ``GV``/``chi``,
    local ``spm_MDP_get_M``, ``N = min(N,T)``, ``BP``/``IP`` preallocation,
    then a partial **per-t** sweep: per-model **GP ``u`` → (``Pu``/**``Q``**/**``P``** if ``Pu_carry[m]``)
    → implicit control → GP ``s`` (~756–855); agent share (~858–869); ``BP``/``IP`` (~1224–1256);
    when ``O`` is ready, ``spm_forwards`` then belief bookkeeping **~1264–1346** (``R``/``w``/``v``,
    path ``P``, ``Pu``, policy ``P`` at ``t``); active likelihood / transition learning **~1349–1409**
    (``spm_cross`` updates to ``qa``/``qb`` and tensors ``A``/``B``, ``W``/``K``, ``I``); per-time **``F``**/**``G``**/**``Z``**.

    ``Pu_carry`` is filled after ``BP``/``IP`` using ``spm_softmax(0, alpha)`` (uniform) when the
    ``O{m,:,t}`` row is not ready; otherwise ``spm_forwards`` (which calls ``spm_VBX``) supplies ``G``
    and ``Pu_carry = spm_softmax(G, alpha)``.

    Outcomes: generation ~913–985 (incl. ~952–969 shared outcomes) runs **before** ``BP``/``IP``.
    ``OPTIONS.B`` replay (~1463–1481) now calls standalone ``spm_backwards``.
    Dirichlet learning (~1485–1587): accumulate ``a``/``b``/``c``/``d``/``e`` and ``Fa``–``Fe``
    (via ``spm_MDP_MI`` when ``beta``, ``spm_softmax``, ``spm_KL_dir``).
    Predictive density (~1591–1606): ``OPTIONS.Y`` fills ``Y`` / ``j`` / ``i`` via ``spm_parents`` +
    ``spm_dot`` (function-handle ``A{g}`` not translated).
    Posterior layout (~1613–1617): ``X`` / ``S`` columns align with ``Q`` / ``P`` at each ``t``.
    Simulated electrophysiology (~1623–1688 when ``OPTIONS.N``): ``xn``/``wn``/``dn``/``un`` (uses ``spm_Gcdf``,
    ``spm_zeros``; sum-to-one on **last** factor only per MATLAB).

    Assemble (~1691–1718 plus neural carry-forward): ``T``, ``U``←``V``, ``R``/``v``/``w``, ``X``/``P``/``O``
    (with ``O`` ``shiftdim``), ``id``, optional ``A``/``B`` from ``a``/``b`` when partial return is allowed.

    Hierarchical ``MDP.MDP`` (~971+) is translated through the current staged scope; child recurse follows parent
    mode (partial recurse only when caller is partial). Main generation-time ``spm_action`` (~814–816) is wired
    through ``_vb_gen_control_one_model`` + ``_spm_action``.

    ``spm_figure`` / graphics branches from MATLAB are intentionally omitted.
    """
    global _VB_MONITOR_REQUESTED, _VB_DUMP_SPEC, _ENTRY12_VBX_ACC, _ENTRY12_PHASE_ACC
    _vb_timing_enter()
    if _VB_TIMING_DEPTH == 1 and _vb_capture_y_probe_active():
        _ENTRY12_VBX_ACC = {}
    if _VB_TIMING_DEPTH == 1 and dump_subentries:
        _ENTRY12_PHASE_ACC = {}
    rand_replay: _VbMatlabRandReplay | None = None
    if reuse_matlab_draws and _VB_TIMING_DEPTH == 1:
        rand_replay = _VbMatlabRandReplay(_vb_load_matlab_rand_buf())
        rand_replay.__enter__()
    if monitoring and _VB_TIMING_DEPTH == 1:
        _VB_MONITOR_REQUESTED = True
    if dump_subentries and _VB_TIMING_DEPTH == 1:
        _VB_DUMP_SPEC = _vb_dump_resolve_spec()
    try:
        t_band = time.perf_counter()
        opts = _merge_options_vb(options)
        partial_ok = bool(int(opts.pop("_rgms_partial_ok", 0)))
        if _vb_has_multiple_epoch_columns(mdp_in):
            raise NotImplementedError(
                "spm_MDP_VB_XXX: multiple epochs (size(MDP,2)>1) are not translated yet"
            )
        mdp_checked = spm_MDP_checkX(copy.deepcopy(mdp_in))
        models = _vb_models_after_checkx(mdp_checked)
        if _vb_dump_active():
            _vb_dump_save("12A", opts, {"note": "post-checkX"}, {"MDP": _vb_dump_mdp_payload(models)})
        _vb_timing_set_band_wall("12A", time.perf_counter() - t_band)
        nm = len(models)
        if _vb_monitoring_active():
            for mi in range(nm):
                _vb_monitor_snapshot("12A", models[mi], mi + 1, None, "once")
        hp = _vb_hyperparameters_mdp1(models[0])
        t_h = float(models[0]["T"])
        t_band = time.perf_counter()
        bundle = _vb_tensors_through_H(models, nm, t_h)
        post = _vb_init_QXSP_outcomes_and_process(
            models, bundle, opts, float(hp["chi"])
        )
        bundle.update(post)
        _vb_timing_set_band_wall("12B", time.perf_counter() - t_band)
        if _vb_dump_active():
            _vb_dump_save(
                "12B",
                opts,
                {"note": "post-setup"},
                {
                    "process": copy.deepcopy(bundle["process"]),
                    "GP": copy.deepcopy(bundle["gp"]),
                    "id": copy.deepcopy(bundle["id"]),
                    "ID": copy.deepcopy(bundle["ID"]),
                    "Ng": copy.deepcopy(bundle["Ng"]),
                    "Nf": copy.deepcopy(bundle["Nf"]),
                    "No": copy.deepcopy(bundle["No"]),
                    "Ns": copy.deepcopy(bundle["Ns"]),
                    "Nu": copy.deepcopy(bundle["Nu"]),
                    "NG": copy.deepcopy(bundle["NG"]),
                    "NF": copy.deepcopy(bundle["NF"]),
                    "NS": copy.deepcopy(bundle["NS"]),
                    "NU": copy.deepcopy(bundle["NU"]),
                    "Nm": int(bundle["Nm"]),
                    "T": int(bundle["T"]),
                    "MDP": _vb_dump_mdp_payload(models),
                },
            )
        t_band = time.perf_counter()
        bundle.update(_vb_policy_depth_and_get_M(models, bundle, hp))
        bundle["options_vb"] = opts
        _vb_timing_set_band_wall("12C", time.perf_counter() - t_band)
        if _vb_dump_active():
            _vb_dump_save(
                "12C",
                opts,
                {"note": "before for t"},
                {
                    "M": copy.deepcopy(bundle["M_update"]),
                    "N": int(bundle["N_policy_depth"]),
                    "MDP": _vb_dump_mdp_payload(models),
                    "O": copy.deepcopy(bundle["O"]),
                    "A": copy.deepcopy(bundle["A"]),
                    "B": copy.deepcopy(bundle["B"]),
                    "BP": copy.deepcopy(bundle["BP"]),
                    "IP": copy.deepcopy(bundle["IP"]),
                },
            )
        if _vb_monitoring_active():
            for mi in range(nm):
                _vb_monitor_snapshot("12C", models[mi], mi + 1, None, "once")
        _vb_run_partial_t_loop(
            models,
            bundle,
            float(hp["alpha"]),
            partial_ok,
            reuse_matlab_draws=reuse_matlab_draws,
        )
        if _vb_dump_active():
            opts_loop = bundle.get("options_vb", opts)
            _vb_dump_save(
                "12D",
                opts_loop,
                {"note": "early band boundaries"},
                copy.deepcopy(bundle.get("entry12_D", {})),
            )
            _vb_dump_save(
                "12E",
                opts_loop,
                {"note": "outcomes/hierarchical boundaries"},
                copy.deepcopy(bundle.get("entry12_E", {})),
            )
            _vb_dump_save(
                "12F",
                opts_loop,
                {"note": "belief-update boundaries"},
                copy.deepcopy(bundle.get("entry12_F", {})),
            )
            _vb_dump_save(
                "12G",
                opts_loop,
                {"note": "after time loop"},
                {
                    "Q": copy.deepcopy(bundle["Q"]),
                    "P": copy.deepcopy(bundle["P"]),
                    "O": copy.deepcopy(bundle["O"]),
                    "R": copy.deepcopy(bundle["R_policy"]),
                    "v": copy.deepcopy(bundle["v_policy"]),
                    "w": copy.deepcopy(bundle["w_policy"]),
                    "id": copy.deepcopy(bundle["id"]),
                    "MDP": _vb_dump_mdp_payload(models),
                },
            )
        t_band = time.perf_counter()
        if _vb_monitoring_active():
            for mi in range(nm):
                _vb_monitor_snapshot("12G", models[mi], mi + 1, None, "first")
        _vb_optional_backwards_replay(models, bundle, opts)
        _vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
        _vb_posterior_predictive_Y(models, bundle, opts)
        _vb_reorganize_X_S_from_QP(bundle)
        _vb_options_N_neural_simulated_responses(models, bundle, opts)
        if _vb_monitoring_active():
            for mi in range(nm):
                _vb_monitor_snapshot("12G", models[mi], mi + 1, None, "last")
        _vb_timing_set_band_wall("12G", time.perf_counter() - t_band)
        t_band = time.perf_counter()
        _vb_assemble_mdp_results_1691(models, bundle)
        _vb_timing_set_band_wall("12H", time.perf_counter() - t_band)
        if partial_ok:
            out_partial = _vb_build_partial_output(models, bundle)
            return out_partial
        if len(models) == 1:
            out_final = copy.deepcopy(models[0])
        else:
            out_final = copy.deepcopy(models)
        if _vb_dump_active():
            _vb_dump_save("12H", opts, {"subentry": "12H"}, {"PDP": copy.deepcopy(out_final)})
            _vb_dump_save(
                "12I",
                opts,
                {"subentry": "12I"},
                {
                    "spine": {
                        "T": int(bundle["T"]),
                        "Nm": int(bundle["Nm"]),
                        "N": int(bundle["N_policy_depth"]),
                    }
                },
            )
        return out_final
    finally:
        if rand_replay is not None and _VB_TIMING_DEPTH == 1:
            rand_replay.__exit__(None, None, None)
        _vb_timing_leave()
        if _VB_TIMING_DEPTH == 0:
            _VB_MONITOR_REQUESTED = False
            _VB_DUMP_SPEC = None


__all__ = ["spm_MDP_VB_XXX", "_spm_sample"]
