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

from python_src.toolbox.DEM.dem_atariiii_entry5 import forget_parameters as _entry5_forget_parameters
from python_src.toolbox.DEM.dem_atariiii_entry6 import find_events_and_windows as _entry6_find_events_and_windows
from python_src.toolbox.DEM.dem_atariiii_entry7 import assimilate_hit_miss_sequences as _entry7_assimilate_sequences
from python_src.toolbox.DEM.dem_atariiii_entry8 import (
    entry8_outer_loop_count as _entry8_outer_loop_count,
    training_window_assimilations as _entry8_training_assimilations_impl,
)
from python_src.toolbox.DEM.dem_atariiii_entry9 import basin_training_loop as _entry9_basin_training_loop_impl
from python_src.toolbox.DEM.dem_atariiii_ledger_hooks import DemAtariLedgerHooks
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.toolbox.DEM.dem_atariiii_paths import dem_atariiii_paths_to_hits_P
from python_src.toolbox.DEM.fsl_backward_entry10 import run_entry10_from_mdp
from python_src.toolbox.DEM.fsl_backward_entry11 import run_entry11_assembly_from_mdp
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs


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
_RGMS_SCRIPT_T0: float | None = None


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


def _rgms_script_t0_reset() -> None:
    global _RGMS_SCRIPT_T0
    _RGMS_SCRIPT_T0 = time.perf_counter()


def _rgms_section_timing_print(section: str, section_start: float) -> None:
    now = time.perf_counter()
    script_t0 = _RGMS_SCRIPT_T0 if _RGMS_SCRIPT_T0 is not None else section_start
    print(
        f"[DEM_AtariIII timing] {section}: section_s={now - section_start:.6f} "
        f"total_elapsed_s={now - script_t0:.6f}",
        file=sys.stderr,
        flush=True,
    )


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


def _dem_atari_ledger_hooks() -> DemAtariLedgerHooks:
    return DemAtariLedgerHooks(
        set_label=_rgms_run_set_last_label,
        deadline_check=_rgms_run_deadline_check,
    )


def _entry8_training_assimilations(
    pdp_o_cells: list[list[Any]], mdp: list[dict[str, Any]], ne: int, nt: int = 100, n_outer: int = 128
) -> tuple[list[dict[str, Any]], float]:
    return _entry8_training_assimilations_impl(
        pdp_o_cells, mdp, ne, nt=nt, n_outer=n_outer, hooks=_dem_atari_ledger_hooks()
    )


def _entry9_basin_training_loop(
    pdp_o_cells: list[list[Any]],
    mdp: list[dict[str, Any]],
    ne: int,
    c_value: float,
    nt: int = 100,
    n_outer: int = 128,
) -> dict[str, Any]:
    return _entry9_basin_training_loop_impl(
        pdp_o_cells, mdp, ne, c_value, nt=nt, n_outer=n_outer, hooks=_dem_atari_ledger_hooks()
    )


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
    _rgms_script_t0_reset()

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
        from python_src.toolbox.DEM.fsl_backward_entry1 import apply_entry1_constants

        apply_entry1_constants(ctx)
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
    _rgms_run_set_last_label("ENTRY2: run_entry2_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry2 import (
        entry2_boundary_from_driver_ctx,
        run_entry2_from_boundary,
    )

    out2 = run_entry2_from_boundary(entry2_boundary_from_driver_ctx(ctx))
    ctx["GDP"] = out2["gdp"]
    ctx["hid"] = out2["hid"]
    ctx["cid"] = out2["cid"]
    ctx["con"] = out2["con"]
    ctx["RGB"] = out2["rgb"]
    ctx["S"] = out2["S"]
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
    _rgms_run_set_last_label("ENTRY3: run_entry3_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry3 import (
        entry3_boundary_from_driver_ctx,
        run_entry3_from_boundary,
    )

    out3 = run_entry3_from_boundary(entry3_boundary_from_driver_ctx(ctx))
    ctx["GDP"] = out3["gdp"]
    ctx["PDP"] = out3["pdp"]
    if _capture_enabled(3, "post"):
        _save_context(3, "post", ctx)
    _rgms_entry_timing_print(3, time.perf_counter() - _t_entry_wall)
    _rgms_section_timing_print("Data Generation", _t_entry_wall)
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
    _rgms_run_set_last_label("ENTRY4: run_entry4_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry4 import (
        entry4_boundary_from_driver_ctx,
        run_entry4_from_boundary,
    )

    out4 = run_entry4_from_boundary(entry4_boundary_from_driver_ctx(ctx))
    ctx["MDP"] = out4["mdp"]
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
    _rgms_run_set_last_label("ENTRY5: run_entry5_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry5 import (
        entry5_boundary_from_driver_ctx,
        run_entry5_from_boundary,
    )

    out5 = run_entry5_from_boundary(entry5_boundary_from_driver_ctx(ctx))
    ctx["Nm"] = out5["Nm"]
    ctx["Ne"] = out5["Ne"]
    ctx["MDP"] = out5["mdp"]
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
    _rgms_run_set_last_label("ENTRY6: run_entry6_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry6 import (
        entry6_boundary_from_driver_ctx,
        run_entry6_from_boundary,
    )

    out6 = run_entry6_from_boundary(entry6_boundary_from_driver_ctx(ctx))
    ctx["r"] = out6["r"]
    ctx["c"] = out6["c"]
    ctx["entry6_windows"] = out6["entry6_windows"]
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
    _rgms_run_set_last_label("ENTRY7: run_entry7_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry7 import (
        entry7_boundary_from_driver_ctx,
        run_entry7_from_boundary,
    )

    out7 = run_entry7_from_boundary(entry7_boundary_from_driver_ctx(ctx))
    ctx["MDP"] = out7["mdp"]
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
        _rgms_run_set_last_label("ENTRY8: run_entry8_from_boundary")
        _rgms_run_deadline_check()
        from python_src.toolbox.DEM.fsl_backward_entry8 import (
            entry8_boundary_from_driver_ctx,
            run_entry8_from_boundary,
        )

        out8 = run_entry8_from_boundary(entry8_boundary_from_driver_ctx(ctx, n_outer=n_outer))
        ctx["MDP"] = out8["mdp"]
        total_entry8_time_sum += float(out8["entry8_merge_loop_s"])
        if _capture_enabled(8, "post"):
            _save_context(8, "post", ctx)
        _rgms_entry_timing_print(8, total_entry8_time_sum)
        _rgms_run_set_last_label("ENTRY8: return entry_stop=8")
        _rgms_run_deadline_check()
        return ctx

    # %%% ENTRY 9 (inside Entry 8 outer loop in the MATLAB snippet)
    _t_merge_structure_learning = time.perf_counter()
    if _use_checkpoint(9):
        ctx = _load_context(9, "pre")
    elif _capture_enabled(9, "pre"):
        _save_context(9, "pre", ctx)
    _rgms_run_set_last_label("ENTRY9: run_entry9_from_boundary")
    _rgms_run_deadline_check()
    from python_src.toolbox.DEM.fsl_backward_entry9 import (
        entry9_boundary_from_driver_ctx,
        run_entry9_from_boundary,
    )

    out9 = run_entry9_from_boundary(entry9_boundary_from_driver_ctx(ctx, n_outer=n_outer))
    ctx["MDP"] = out9["mdp"]
    ctx["NS"] = out9["NS"]
    ctx["NU"] = out9["NU"]
    ctx["NA"] = out9["NA"]
    ctx["NO"] = out9["NO"]
    ctx["NH"] = out9["NH"]
    total_entry8_time_sum += float(out9["entry8_loop_s"])
    total_entry9_time_sum = float(out9["entry9_loop_s"])
    _rgms_entry_timing_print(8, total_entry8_time_sum)
    _rgms_entry_timing_print(9, total_entry9_time_sum)
    _rgms_section_timing_print("Merge Structure Learning", _t_merge_structure_learning)
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
    _rgms_run_set_last_label("ENTRY10: run_entry10_from_mdp")
    _rgms_run_deadline_check()
    out10 = run_entry10_from_mdp(ctx["MDP"], c_val=float(ctx["C"]))
    ctx["MDP"] = out10["mdp"]
    ctx["entry10_j"] = out10["entry10_j"]
    ctx["P"] = out10["P"]
    ctx["hid"] = out10["hid"]
    ctx["entry10_Nt"] = out10["entry10_Nt"]
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

    _rgms_run_set_last_label("ENTRY11: assemble RDP")
    _rgms_run_deadline_check()
    ctx["RDP"] = run_entry11_assembly_from_mdp(ctx["MDP"], c_val=float(ctx["C"]))

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

