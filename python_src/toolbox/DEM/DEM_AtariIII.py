"""
Driver-lane transliteration scaffold for DEM_AtariIII.m (non-visual path).

This module is intentionally entry-aligned with `Atari_example.md`. It orchestrates
already-translated `spm_*` functions and keeps per-entry checkpoint/capture hooks so
later entries can be isolated against MATLAB boundary states. `entry_stop` returns for
**1..12** (Entry 11: ``spm_set_goals`` → ``spm_set_costs`` → nested ``RDP`` / ``T``; Entry 12: ``PDP = spm_MDP_VB_XXX(RDP)`` in partial
MATLAB-faithful mode until the global VB stub is removed). MATLAB capture artifacts live in
``tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12.py``.
"""

from __future__ import annotations

import copy
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_faster_structure_learning import spm_faster_structure_learning
from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _checkpoint_dir() -> Path:
    return _repo_root() / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"


def _env_flag(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in ("1", "true", "yes", "on")


def _training_horizon() -> int:
    raw = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    try:
        t = int(raw)
    except ValueError as exc:
        raise ValueError(f"RGMS_ATARI_TRAINING_T must be int-like, got {raw!r}") from exc
    return max(t, 1000)


def _tag() -> str:
    raw = str(os.getenv("RGMS_ATARI_TAG", "baseline")).strip()
    return "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw) or "baseline"


# Full-depth ledger integration (FSL 1–11): ``tests/oracle/toolbox/DEM/test_DEM_AtariIII_full_staged_atari_ledger_1_11.py``
#   (``RGMS_ATARI_RUN_FULL_STAGED_LEDGER_1_11=1`` structural; MATLAB nested-``RDP`` vs ``.mat`` via ``tests/oracle/toolbox/DEM/fsl_1_11_compare_ctx_pkl_to_mat.py`` + PKL written automatically after successful FSL; path override ``RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH``).
# --- Optional integrated-run tracing (ENTRY 1–11 gate; ``Atari_example.md`` § ENTRY 1-11) ---
# Wall limit (``time.perf_counter()``): **prefer ``RGMS_ATARI_RUN_DEADLINE_MINUTES``** (e.g. ``"40"``)
# as the single knob — first deadline check seeds the ceiling and the same string labels ``RuntimeError``.
# Legacy: **only** ``RGMS_ATARI_RUN_DEADLINE_MONO`` (absolute cutoff); message uses ``MINUTES`` if set, else ``?``.
# If **both** are set, **minutes win** for the cutoff (avoids a stale shell ``MONO`` overriding a fresh budget).
# Optional: ``RGMS_ATARI_RUN_SEGMENT_TIMING=1`` → stderr segment timings between labels.
_RGMS_RUN_LAST_LABEL = ""
_RGMS_RUN_SEGMENT_T0 = 0.0
# Lazy perf_counter ceiling when only ``RGMS_ATARI_RUN_DEADLINE_MINUTES`` is set (reset each ``run_dem_atariiii``).
_RGMS_ACTIVE_DEADLINE_CUTOFF: float | None = None
_RGMS_ACTIVE_DEADLINE_MINUTES_DISP: str = ""


def get_dem_atariiii_run_last_label() -> str:
    """Last high-level operation label set during ``run_dem_atariiii`` (for error / timeout diagnostics)."""
    return _RGMS_RUN_LAST_LABEL


def _rgms_run_reset_segment_timer() -> None:
    """Reset segment baseline so the first timing line reports +0s from run start."""
    global _RGMS_RUN_SEGMENT_T0
    _RGMS_RUN_SEGMENT_T0 = 0.0


def _rgms_run_set_last_label(label: str) -> None:
    global _RGMS_RUN_LAST_LABEL, _RGMS_RUN_SEGMENT_T0
    _RGMS_RUN_LAST_LABEL = label
    if _env_flag("RGMS_ATARI_RUN_SEGMENT_TIMING"):
        now = time.perf_counter()
        dt = now - _RGMS_RUN_SEGMENT_T0 if _RGMS_RUN_SEGMENT_T0 > 0.0 else 0.0
        _RGMS_RUN_SEGMENT_T0 = now
        print(f"[DEM_AtariIII run trace] {label}  (+{dt:.6f}s since previous segment)", file=sys.stderr, flush=True)


def _rgms_deadline_reset_for_run() -> None:
    """Clear lazy deadline anchor so each ``run_dem_atariiii`` honors fresh ``MINUTES``-only limits."""
    global _RGMS_ACTIVE_DEADLINE_CUTOFF, _RGMS_ACTIVE_DEADLINE_MINUTES_DISP
    _RGMS_ACTIVE_DEADLINE_CUTOFF = None
    _RGMS_ACTIVE_DEADLINE_MINUTES_DISP = ""


def _rgms_run_deadline_enabled() -> bool:
    if str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MONO", "")).strip():
        return True
    raw = str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MINUTES", "")).strip()
    if not raw:
        return False
    try:
        return float(raw) > 0.0
    except ValueError:
        return False


def _rgms_run_deadline_check() -> None:
    """Abort when ``time.perf_counter()`` exceeds the active ceiling.

    **Primary:** ``RGMS_ATARI_RUN_DEADLINE_MINUTES`` (positive float string). The first check
    records ``time.perf_counter() + minutes*60`` and reuses that string in ``RuntimeError``.

    **Legacy:** if ``MINUTES`` is unset, ``RGMS_ATARI_RUN_DEADLINE_MONO`` may be set to
    ``str(time.perf_counter() + minutes*60)`` explicitly; the message then uses ``MINUTES`` if
    present, else ``?``.

    If **both** are set, **``MINUTES`` wins** for the cutoff (avoids a stale shell ``MONO`` from an
    older process overriding a fresh minute budget).
    """
    global _RGMS_ACTIVE_DEADLINE_CUTOFF, _RGMS_ACTIVE_DEADLINE_MINUTES_DISP
    if not _rgms_run_deadline_enabled():
        return

    mins_raw = str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MINUTES", "")).strip()
    mono_raw = str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MONO", "")).strip()

    if mins_raw:
        try:
            minutes = float(mins_raw)
        except ValueError:
            return
        if minutes <= 0.0:
            return
        if _RGMS_ACTIVE_DEADLINE_CUTOFF is None:
            _RGMS_ACTIVE_DEADLINE_CUTOFF = time.perf_counter() + minutes * 60.0
            _RGMS_ACTIVE_DEADLINE_MINUTES_DISP = mins_raw
        limit_mono = float(_RGMS_ACTIVE_DEADLINE_CUTOFF)
        mins_disp = _RGMS_ACTIVE_DEADLINE_MINUTES_DISP or mins_raw
    elif mono_raw:
        limit_mono = float(mono_raw)
        mins_disp = str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MINUTES", "")).strip() or "?"
    else:
        return

    if time.perf_counter() > limit_mono:
        msg = f"TIME LIMIT OF {mins_disp} MINUTES EXCEEDED. Last call = {_RGMS_RUN_LAST_LABEL}"
        raise RuntimeError(msg)


def _rgms_entry_timing_print(entry: int, total_s: float) -> None:
    print(f"[DEM_AtariIII entry timing] ENTRY{entry} total_s={total_s:.6f}", file=sys.stderr, flush=True)


def _ck_path(entry: int, phase: str) -> Path:
    return _checkpoint_dir() / f"dem_atari_entry{int(entry)}_{phase}_{_tag()}.pkl"


def _capture_enabled(entry: int, phase: str) -> bool:
    return _env_flag(f"RGMS_ATARI_CAPTURE_ENTRY{int(entry)}_{phase.upper()}")


def _use_checkpoint(entry: int) -> bool:
    return _env_flag(f"RGMS_ATARI_ENTRY{int(entry)}_USE_CHECKPOINT")


def _save_context(entry: int, phase: str, context: dict[str, Any]) -> None:
    path = _ck_path(entry, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(context, f, protocol=pickle.HIGHEST_PROTOCOL)


def _load_context(entry: int, phase: str) -> dict[str, Any]:
    path = _ck_path(entry, phase)
    if not path.exists():
        raise FileNotFoundError(
            f"DEM_AtariIII checkpoint not found for Entry {entry} {phase}: {path}"
        )
    with path.open("rb") as f:
        return pickle.load(f)


def _entry5_forget_parameters(mdp: list[dict[str, Any]]) -> tuple[int, int, list[dict[str, Any]]]:
    """ENTRY 5: clear `a{g}` and `b{f}` per model, preserving container structure."""
    mdp_out = copy.deepcopy(mdp)
    nm = len(mdp_out)
    ne = max(2 ** (nm - 1), 1)
    for n in range(nm):
        for g in range(len(mdp_out[n]["a"])):
            mdp_out[n]["a"][g] = []
        for f in range(len(mdp_out[n]["b"])):
            mdp_out[n]["b"][f] = []
    return nm, ne, mdp_out


def _entry6_find_events_and_windows(
    pdp_o: np.ndarray, gdp_id: dict[str, Any], ne: int
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """ENTRY 6: rewarded/costly event indices and assimilation windows."""
    ridx = int(np.asarray(gdp_id["reward"], dtype=np.int64).reshape(-1)[0]) - 1
    cidx = int(np.asarray(gdp_id["contraint"], dtype=np.int64).reshape(-1)[0]) - 1
    r = np.flatnonzero(np.asarray(pdp_o[ridx, :], dtype=np.float64) > 1.0) + 1
    c = np.flatnonzero(np.asarray(pdp_o[cidx, :], dtype=np.float64) > 1.0) + 1
    windows: list[dict[str, Any]] = []
    for i in range(r.size):
        ri = int(r[i])
        s = int(c[np.flatnonzero(c < ri)[-1]])
        t = np.arange(s + int(ne), ri + int(ne) + 1, dtype=np.int64)
        if t.size > 0:
            windows.append({"reward": ri, "start": s, "t": t})
    return r, c, windows


def _entry7_assimilate_sequences(
    pdp_o_cells: list[list[Any]], mdp: list[dict[str, Any]], entry6_windows: list[dict[str, Any]], ne: int
) -> list[dict[str, Any]]:
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    for rec in entry6_windows:
        t = np.asarray(rec["t"], dtype=np.int64).ravel(order="F")
        for s in range(1, int(ne) + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
    return mdp_out


def _entry8_timing_enabled() -> bool:
    """When true, `_entry8_training_assimilations` prints per-outer-iteration wall times to stderr."""
    return _env_flag("RGMS_ATARI_ENTRY8_TIMING")


def _entry8_outer_loop_count() -> int:
    """MATLAB `for i = 1:128`; optional env override for harness speed only."""
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "128")).strip()
    try:
        n = int(raw)
    except ValueError as exc:
        raise ValueError(f"RGMS_ATARI_ENTRY8_OUTER must be int-like, got {raw!r}") from exc
    return int(np.clip(n, 1, 128))


def _entry8_training_assimilations(
    pdp_o_cells: list[list[Any]], mdp: list[dict[str, Any]], ne: int, nt: int = 100, n_outer: int = 128
) -> tuple[list[dict[str, Any]], float]:
    """ENTRY 8: merge additional training windows under random play (no basin step).

    Returns ``(mdp_out, total_merge_loop_s)`` — per-outer merge-loop wall times summed.
    """
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    ne_i = int(ne)
    nt_i = int(nt)
    timing = _entry8_timing_enabled()
    total_merge_loop_s = 0.0
    for i in range(1, int(n_outer) + 1):
        _rgms_run_set_last_label(f"ENTRY8: outer i={i}/{int(n_outer)}")
        _rgms_run_deadline_check()
        t_outer = time.perf_counter()
        offset = int(np.remainder(i, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        t_merge = time.perf_counter()
        for s in range(1, ne_i + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
            _rgms_run_deadline_check()
        total_merge_loop_s += time.perf_counter() - t_merge
        if timing:
            print(
                f"[DEM_AtariIII entry8] outer {i}/{int(n_outer)} wall_s={time.perf_counter() - t_outer:.6f}",
                file=sys.stderr,
                flush=True,
            )
    return mdp_out, total_merge_loop_s


def _entry9_basin_training_loop(
    pdp_o_cells: list[list[Any]],
    mdp: list[dict[str, Any]],
    ne: int,
    c_value: float,
    nt: int = 100,
    n_outer: int = 128,
) -> dict[str, Any]:
    """ENTRY 8+9 combined loop with basin reduction and counters."""
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    ne_i = int(ne)
    nt_i = int(nt)

    ns_hist: list[int] = []
    nu_hist: list[int] = []
    na_hist: list[int] = []
    no_hist: list[int] = []
    nh_hist: list[int] = []
    entry8_loop_s = 0.0
    entry9_loop_s = 0.0

    for i in range(1, int(n_outer) + 1):
        _rgms_run_set_last_label(f"ENTRY9: outer i={i}/{int(n_outer)}")
        _rgms_run_deadline_check()
        offset = int(np.remainder(i, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        t_merge = time.perf_counter()
        for s in range(1, ne_i + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
            _rgms_run_deadline_check()
        entry8_loop_s += time.perf_counter() - t_merge

        _rgms_run_set_last_label(f"ENTRY9: spm_RDP_basin outer i={i}/{int(n_outer)}")
        _rgms_run_deadline_check()
        t_basin = time.perf_counter()
        mdp_out, d, o, h, _ = spm_RDP_basin(mdp_out, [2, 3], [float(c_value), -float(c_value)])
        b1 = np.asarray(mdp_out[len(mdp_out) - 1]["b"][0][0], dtype=np.float64)
        ns_hist.append(int(b1.shape[1]) if b1.ndim >= 2 else 1)
        nu_hist.append(int(b1.shape[2]) if b1.ndim >= 3 else 1)
        na_hist.append(int(np.sum(~np.asarray(d, dtype=bool).ravel(order="F"))))
        no_hist.append(int(np.sum(~np.asarray(o, dtype=bool).ravel(order="F"))))
        nh_hist.append(int(np.asarray(h, dtype=np.int64).ravel(order="F").size))
        entry9_loop_s += time.perf_counter() - t_basin
        if np.all(np.asarray(d, dtype=bool).ravel(order="F")):
            break

    return {
        "MDP": mdp_out,
        "NS": ns_hist,
        "NU": nu_hist,
        "NA": na_hist,
        "NO": no_hist,
        "NH": nh_hist,
        "entry8_loop_s": entry8_loop_s,
        "entry9_loop_s": entry9_loop_s,
    }


def dem_atariiii_paths_to_hits_P(
    B_mask: np.ndarray, hid_1based: np.ndarray | list[int], nt: int
) -> np.ndarray:
    """Paths-to-hits matrix ``P`` (DEM_AtariIII ledger after ``spm_set_goals``).

    MATLAB::

        B = sum(MDP{Nm}.b{1},3) > 0;
        h = sparse(1,hid,1,1,Ns);
        for t = 1:Nt
            P(t,:) = h;
            h = (h + h*B) > 0;
        end

    ``hid_1based`` are 1-based state indices (``MDP{end}.id.hid`` layout).
    """
    B = np.asarray(B_mask, dtype=np.float64)
    ns = int(B.shape[0])
    if B.shape != (ns, ns):
        raise ValueError("B_mask must be square")
    hid = np.asarray(hid_1based, dtype=np.int64).ravel(order="F")
    nt_i = int(nt)
    h = np.zeros((1, ns), dtype=np.float64)
    for idx in hid.tolist():
        j0 = int(idx) - 1
        if 0 <= j0 < ns:
            h[0, j0] = 1.0
    p_out = np.zeros((nt_i, ns), dtype=np.float64)
    for t in range(nt_i):
        p_out[t, :] = h[0, :]
        h = ((h + (h @ B)) > 0).astype(np.float64)
    return p_out


def run_dem_atariiii(entry_stop: int = 5) -> dict[str, Any]:
    """
    Run DEM_AtariIII driver entries up to `entry_stop` (implemented through Entry 12).

    Entry 12 calls ``spm_MDP_VB_XXX(RDP)`` with ``_rgms_partial_ok`` until the full MATLAB time loop
    is ported. MATLAB-only artifact capture: ``tests/oracle/toolbox/DEM/test_DEM_AtariIII_entry12.py``.

    **Wall time limit (optional):** set ``RGMS_ATARI_RUN_DEADLINE_MINUTES`` (minutes as a string) to
    enable a ``time.perf_counter()`` ceiling from the first deadline check; the same value appears
    in the timeout ``RuntimeError``. Optionally set ``RGMS_ATARI_RUN_DEADLINE_MONO`` instead for an
    explicit absolute cutoff (see module comment block and ``Atari_example.md`` § **ENTRY 1-11**).

    **Per-entry wall timing:** each completed Entry ``n`` prints one stderr line
    ``[DEM_AtariIII entry timing] ENTRYn total_s=...``; Entries **8** and **9** use summed inner-loop
    times (merge vs basin slices) as documented in the implementation.
    """
    if entry_stop < 1:
        raise ValueError("entry_stop must be >= 1")
    if entry_stop > 12:
        raise NotImplementedError("entry_stop > 12 is not implemented in DEM_AtariIII.py")

    _rgms_deadline_reset_for_run()

    ctx: dict[str, Any] = {}

    if _env_flag("RGMS_ATARI_RUN_SEGMENT_TIMING"):
        _rgms_run_reset_segment_timer()

    _rgms_run_set_last_label("run_dem_atariiii: start")
    _rgms_run_deadline_check()

    # %%% ENTRY 1
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(1):
        ctx = _load_context(1, "pre")
    else:
        if _capture_enabled(1, "pre"):
            _save_context(1, "pre", ctx)
        # MATLAB snippet constants
        ctx["Nr"] = 12
        ctx["Nc"] = 9
        ctx["Sc"] = 9
        ctx["Nd"] = 4
        ctx["C"] = 32
    if _capture_enabled(1, "post"):
        _save_context(1, "post", ctx)
    _rgms_entry_timing_print(1, time.perf_counter() - _t_entry_wall)
    if entry_stop == 1:
        _rgms_run_set_last_label("ENTRY1: return entry_stop=1")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 2
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(2):
        ctx = _load_context(2, "pre")
    elif _capture_enabled(2, "pre"):
        _save_context(2, "pre", ctx)
    _rgms_run_set_last_label("ENTRY2: spm_MDP_pong")
    _rgms_run_deadline_check()
    gdp, hid, cid, con, rgb, _ = spm_MDP_pong(ctx["Nr"], ctx["Nc"], ctx["Nd"], 1, 0)
    s = np.ones((4, 3), dtype=np.float64)
    s[0, :] = [ctx["Nr"], ctx["Nc"], 1]
    ctx["GDP"] = gdp
    ctx["hid"] = hid
    ctx["cid"] = cid
    ctx["con"] = con
    ctx["RGB"] = rgb
    ctx["S"] = s
    if _capture_enabled(2, "post"):
        _save_context(2, "post", ctx)
    _rgms_entry_timing_print(2, time.perf_counter() - _t_entry_wall)
    if entry_stop == 2:
        _rgms_run_set_last_label("ENTRY2: return entry_stop=2")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 3
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(3):
        ctx = _load_context(3, "pre")
    elif _capture_enabled(3, "pre"):
        _save_context(3, "pre", ctx)
    gdp = copy.deepcopy(ctx["GDP"])
    gdp["tau"] = 1.0
    gdp["T"] = float(_training_horizon())
    _rgms_run_set_last_label("ENTRY3: spm_MDP_generate")
    _rgms_run_deadline_check()
    pdp = spm_MDP_generate(gdp)
    ctx["GDP"] = gdp
    ctx["PDP"] = pdp
    if _capture_enabled(3, "post"):
        _save_context(3, "post", ctx)
    _rgms_entry_timing_print(3, time.perf_counter() - _t_entry_wall)
    if entry_stop == 3:
        _rgms_run_set_last_label("ENTRY3: return entry_stop=3")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 4
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(4):
        ctx = _load_context(4, "pre")
    elif _capture_enabled(4, "pre"):
        _save_context(4, "pre", ctx)
    o_sl = [[ctx["PDP"]["O"][g][t] for t in range(1000)] for g in range(len(ctx["PDP"]["O"]))]
    _rgms_run_set_last_label("ENTRY4: spm_faster_structure_learning")
    _rgms_run_deadline_check()
    mdp = spm_faster_structure_learning(o_sl, ctx["S"], ctx["Sc"])
    ctx["MDP"] = mdp
    if _capture_enabled(4, "post"):
        _save_context(4, "post", ctx)
    _rgms_entry_timing_print(4, time.perf_counter() - _t_entry_wall)
    if entry_stop == 4:
        _rgms_run_set_last_label("ENTRY4: return entry_stop=4")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 5
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(5):
        ctx = _load_context(5, "pre")
    elif _capture_enabled(5, "pre"):
        _save_context(5, "pre", ctx)
    _rgms_run_set_last_label("ENTRY5: _entry5_forget_parameters")
    _rgms_run_deadline_check()
    nm, ne, mdp = _entry5_forget_parameters(ctx["MDP"])
    ctx["Nm"] = nm
    ctx["Ne"] = ne
    ctx["MDP"] = mdp
    if _capture_enabled(5, "post"):
        _save_context(5, "post", ctx)
    _rgms_entry_timing_print(5, time.perf_counter() - _t_entry_wall)
    if entry_stop == 5:
        _rgms_run_set_last_label("ENTRY5: return entry_stop=5")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 6
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(6):
        ctx = _load_context(6, "pre")
    elif _capture_enabled(6, "pre"):
        _save_context(6, "pre", ctx)
    _rgms_run_set_last_label("ENTRY6: _entry6_find_events_and_windows")
    _rgms_run_deadline_check()
    r, c, windows = _entry6_find_events_and_windows(ctx["PDP"]["o"], ctx["GDP"]["id"], int(ctx["Ne"]))
    ctx["r"] = r
    ctx["c"] = c
    ctx["entry6_windows"] = windows
    if _capture_enabled(6, "post"):
        _save_context(6, "post", ctx)
    _rgms_entry_timing_print(6, time.perf_counter() - _t_entry_wall)
    if entry_stop == 6:
        _rgms_run_set_last_label("ENTRY6: return entry_stop=6")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 7
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(7):
        ctx = _load_context(7, "pre")
    elif _capture_enabled(7, "pre"):
        _save_context(7, "pre", ctx)
    _rgms_run_set_last_label("ENTRY7: _entry7_assimilate_sequences")
    _rgms_run_deadline_check()
    ctx["MDP"] = _entry7_assimilate_sequences(
        ctx["PDP"]["O"], ctx["MDP"], ctx["entry6_windows"], int(ctx["Ne"])
    )
    if _capture_enabled(7, "post"):
        _save_context(7, "post", ctx)
    _rgms_entry_timing_print(7, time.perf_counter() - _t_entry_wall)
    if entry_stop == 7:
        _rgms_run_set_last_label("ENTRY7: return entry_stop=7")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 8
    _t8_setup = time.perf_counter()
    if _use_checkpoint(8):
        ctx = _load_context(8, "pre")
    elif _capture_enabled(8, "pre"):
        _save_context(8, "pre", ctx)
    ctx["entry8_NT"] = 100
    n_outer = _entry8_outer_loop_count()
    ctx["entry8_outer"] = n_outer
    total_entry8_time_sum = time.perf_counter() - _t8_setup

    if entry_stop == 8:
        _rgms_run_set_last_label("ENTRY8: _entry8_training_assimilations")
        _rgms_run_deadline_check()
        mdp8, merge_loop_s = _entry8_training_assimilations(
            ctx["PDP"]["O"], ctx["MDP"], int(ctx["Ne"]), nt=int(ctx["entry8_NT"]), n_outer=n_outer
        )
        ctx["MDP"] = mdp8
        total_entry8_time_sum += merge_loop_s
        if _capture_enabled(8, "post"):
            _save_context(8, "post", ctx)
        _rgms_entry_timing_print(8, total_entry8_time_sum)
        _rgms_run_set_last_label("ENTRY8: return entry_stop=8")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 9 (inside Entry 8 outer loop in the MATLAB snippet)
    if _use_checkpoint(9):
        ctx = _load_context(9, "pre")
    elif _capture_enabled(9, "pre"):
        _save_context(9, "pre", ctx)
    _rgms_run_set_last_label("ENTRY9: _entry9_basin_training_loop")
    _rgms_run_deadline_check()
    out9 = _entry9_basin_training_loop(
        ctx["PDP"]["O"],
        ctx["MDP"],
        int(ctx["Ne"]),
        float(ctx["C"]),
        nt=int(ctx["entry8_NT"]),
        n_outer=n_outer,
    )
    ctx["MDP"] = out9["MDP"]
    ctx["NS"] = out9["NS"]
    ctx["NU"] = out9["NU"]
    ctx["NA"] = out9["NA"]
    ctx["NO"] = out9["NO"]
    ctx["NH"] = out9["NH"]
    total_entry8_time_sum += float(out9["entry8_loop_s"])
    total_entry9_time_sum = float(out9["entry9_loop_s"])
    _rgms_entry_timing_print(8, total_entry8_time_sum)
    _rgms_entry_timing_print(9, total_entry9_time_sum)
    if _capture_enabled(9, "post"):
        _save_context(9, "post", ctx)
    if entry_stop == 9:
        _rgms_run_set_last_label("ENTRY9: return entry_stop=9")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 10 (NESS sort, goals refresh, paths-to-hits P)
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(10):
        ctx = _load_context(10, "pre")
    elif _capture_enabled(10, "pre"):
        _save_context(10, "pre", ctx)
    _rgms_run_set_last_label("ENTRY10: spm_RDP_sort")
    _rgms_run_deadline_check()
    mdp10, j10 = spm_RDP_sort(copy.deepcopy(ctx["MDP"]))
    ctx["entry10_j"] = j10
    c_val = float(ctx["C"])
    _rgms_run_set_last_label("ENTRY10: spm_set_goals")
    _rgms_run_deadline_check()
    mdp10 = spm_set_goals(
        mdp10,
        np.array([2, 3], dtype=np.int64),
        np.array([c_val, -c_val], dtype=np.float64),
    )
    ctx["MDP"] = mdp10
    nm = len(mdp10)
    b1 = np.asarray(mdp10[nm - 1]["b"][0][0], dtype=np.float64)
    bp = (np.sum(b1, axis=2) > 0).astype(np.float64)
    hid_list = mdp10[nm - 1]["id"].get("hid", [])
    hid_arr = np.asarray(hid_list, dtype=np.int64).ravel() if hid_list else np.zeros(0, dtype=np.int64)
    nt_p = 32
    ctx["P"] = dem_atariiii_paths_to_hits_P(bp, hid_arr, nt_p)
    ctx["hid"] = hid_arr
    ctx["entry10_Nt"] = nt_p
    if _capture_enabled(10, "post"):
        _save_context(10, "post", ctx)
    _rgms_entry_timing_print(10, time.perf_counter() - _t_entry_wall)
    if entry_stop == 10:
        _rgms_run_set_last_label("ENTRY10: return entry_stop=10")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 11 (costs, nested RDP, ledger horizon T = 64)
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(11):
        ctx = _load_context(11, "pre")
    elif _capture_enabled(11, "pre"):
        _save_context(11, "pre", ctx)

    mdp_e11 = ctx["MDP"]
    c_val = float(ctx["C"])
    _rgms_run_set_last_label("ENTRY11: spm_set_goals")
    _rgms_run_deadline_check()
    mdp_e11 = spm_set_goals(
        mdp_e11,
        np.array([2, 3], dtype=np.int64),
        np.array([c_val, -c_val], dtype=np.float64),
    )
    ctx["MDP"] = mdp_e11
    _rgms_run_set_last_label("ENTRY11: spm_set_costs")
    _rgms_run_deadline_check()
    mdp_e11 = spm_set_costs(
        mdp_e11,
        np.array([2.0, 3.0], dtype=np.float64),
        np.array([c_val, -c_val], dtype=np.float64),
    )
    ctx["MDP"] = mdp_e11
    _rgms_run_set_last_label("ENTRY11: spm_mdp2rdp")
    _rgms_run_deadline_check()
    rdp = spm_mdp2rdp(mdp_e11)
    rdp["T"] = 64.0
    ctx["RDP"] = rdp

    if _capture_enabled(11, "post"):
        _save_context(11, "post", ctx)
    _rgms_entry_timing_print(11, time.perf_counter() - _t_entry_wall)
    if entry_stop == 11:
        _rgms_run_set_last_label("ENTRY11: return entry_stop=11")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 12 (variational Bayes on nested RDP → PDP)
    _t_entry_wall = time.perf_counter()
    if _use_checkpoint(12):
        ctx = _load_context(12, "pre")
    elif _capture_enabled(12, "pre"):
        _save_context(12, "pre", ctx)

    _rgms_run_set_last_label("ENTRY12: spm_MDP_VB_XXX")
    _rgms_run_deadline_check()
    ctx["PDP"] = spm_MDP_VB_XXX(ctx["RDP"])
    ctx["_entry12_use_partial_vb"] = False

    if _capture_enabled(12, "post"):
        _save_context(12, "post", ctx)
    _rgms_entry_timing_print(12, time.perf_counter() - _t_entry_wall)
    _rgms_run_set_last_label("run_dem_atariiii: complete")
    _rgms_run_deadline_check()
    return ctx

__all__ = [
    "run_dem_atariiii",
    "get_dem_atariiii_run_last_label",
    "dem_atariiii_paths_to_hits_P",
    "_entry8_training_assimilations",
    "_entry9_basin_training_loop",
]

