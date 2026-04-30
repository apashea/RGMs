"""
Driver-lane transliteration scaffold for DEM_AtariIII.m (non-visual path).

This module is intentionally entry-aligned with `Atari_example.md`. It orchestrates
already-translated `spm_*` functions and keeps per-entry checkpoint/capture hooks so
later entries can be isolated against MATLAB boundary states.
"""

from __future__ import annotations

import copy
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_faster_structure_learning import spm_faster_structure_learning
from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong


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


def run_dem_atariiii(entry_stop: int = 5) -> dict[str, Any]:
    """
    Run DEM_AtariIII driver entries up to `entry_stop` (currently supports 1..6).
    """
    if entry_stop < 1:
        raise ValueError("entry_stop must be >= 1")
    if entry_stop > 6:
        raise NotImplementedError("Entries 7+ are not translated in DEM_AtariIII.py yet")

    ctx: dict[str, Any] = {}

    # %%% ENTRY 1
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
    if entry_stop == 1:
        return ctx

    # %%% ENTRY 2
    if _use_checkpoint(2):
        ctx = _load_context(2, "pre")
    elif _capture_enabled(2, "pre"):
        _save_context(2, "pre", ctx)
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
    if entry_stop == 2:
        return ctx

    # %%% ENTRY 3
    if _use_checkpoint(3):
        ctx = _load_context(3, "pre")
    elif _capture_enabled(3, "pre"):
        _save_context(3, "pre", ctx)
    gdp = copy.deepcopy(ctx["GDP"])
    gdp["tau"] = 1.0
    gdp["T"] = float(_training_horizon())
    pdp = spm_MDP_generate(gdp)
    ctx["GDP"] = gdp
    ctx["PDP"] = pdp
    if _capture_enabled(3, "post"):
        _save_context(3, "post", ctx)
    if entry_stop == 3:
        return ctx

    # %%% ENTRY 4
    if _use_checkpoint(4):
        ctx = _load_context(4, "pre")
    elif _capture_enabled(4, "pre"):
        _save_context(4, "pre", ctx)
    o_sl = [[ctx["PDP"]["O"][g][t] for t in range(1000)] for g in range(len(ctx["PDP"]["O"]))]
    mdp = spm_faster_structure_learning(o_sl, ctx["S"], ctx["Sc"])
    ctx["MDP"] = mdp
    if _capture_enabled(4, "post"):
        _save_context(4, "post", ctx)
    if entry_stop == 4:
        return ctx

    # %%% ENTRY 5
    if _use_checkpoint(5):
        ctx = _load_context(5, "pre")
    elif _capture_enabled(5, "pre"):
        _save_context(5, "pre", ctx)
    nm, ne, mdp = _entry5_forget_parameters(ctx["MDP"])
    ctx["Nm"] = nm
    ctx["Ne"] = ne
    ctx["MDP"] = mdp
    if _capture_enabled(5, "post"):
        _save_context(5, "post", ctx)
    if entry_stop == 5:
        return ctx

    # %%% ENTRY 6
    if _use_checkpoint(6):
        ctx = _load_context(6, "pre")
    elif _capture_enabled(6, "pre"):
        _save_context(6, "pre", ctx)
    r, c, windows = _entry6_find_events_and_windows(ctx["PDP"]["o"], ctx["GDP"]["id"], int(ctx["Ne"]))
    ctx["r"] = r
    ctx["c"] = c
    ctx["entry6_windows"] = windows
    if _capture_enabled(6, "post"):
        _save_context(6, "post", ctx)

    return ctx


__all__ = ["run_dem_atariiii"]

