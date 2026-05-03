"""
Driver-lane transliteration scaffold for DEM_AtariIII.m (non-visual path).

This module is intentionally entry-aligned with `Atari_example.md`. It orchestrates
already-translated `spm_*` functions and keeps per-entry checkpoint/capture hooks so
later entries can be isolated against MATLAB boundary states. `entry_stop` is implemented for
**1..11** (Entry 11: `spm_set_costs`, `spm_mdp2rdp`, `RDP.T = 64`); **12+** is not wired.
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
) -> list[dict[str, Any]]:
    """ENTRY 8: merge additional training windows under random play (no basin step)."""
    mdp_out = copy.deepcopy(mdp)
    ng = len(pdp_o_cells)
    ne_i = int(ne)
    nt_i = int(nt)
    timing = _entry8_timing_enabled()
    for i in range(1, int(n_outer) + 1):
        t_outer = time.perf_counter()
        offset = int(np.remainder(i, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        for s in range(1, ne_i + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)
        if timing:
            print(
                f"[DEM_AtariIII entry8] outer {i}/{int(n_outer)} wall_s={time.perf_counter() - t_outer:.6f}",
                file=sys.stderr,
                flush=True,
            )
    return mdp_out


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

    for i in range(1, int(n_outer) + 1):
        offset = int(np.remainder(i, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        for s in range(1, ne_i + 1):
            cols = (t + int(s)).astype(np.int64)
            o_seg = [[pdp_o_cells[g][int(c) - 1] for c in cols.tolist()] for g in range(ng)]
            mdp_out = spm_merge_structure_learning(o_seg, mdp_out)

        mdp_out, d, o, h, _ = spm_RDP_basin(mdp_out, [2, 3], [float(c_value), -float(c_value)])
        b1 = np.asarray(mdp_out[len(mdp_out) - 1]["b"][0][0], dtype=np.float64)
        ns_hist.append(int(b1.shape[1]) if b1.ndim >= 2 else 1)
        nu_hist.append(int(b1.shape[2]) if b1.ndim >= 3 else 1)
        na_hist.append(int(np.sum(~np.asarray(d, dtype=bool).ravel(order="F"))))
        no_hist.append(int(np.sum(~np.asarray(o, dtype=bool).ravel(order="F"))))
        nh_hist.append(int(np.asarray(h, dtype=np.int64).ravel(order="F").size))
        if np.all(np.asarray(d, dtype=bool).ravel(order="F")):
            break

    return {
        "MDP": mdp_out,
        "NS": ns_hist,
        "NU": nu_hist,
        "NA": na_hist,
        "NO": no_hist,
        "NH": nh_hist,
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
    Run DEM_AtariIII driver entries up to `entry_stop` (implemented through Entry 11).
    """
    if entry_stop < 1:
        raise ValueError("entry_stop must be >= 1")
    if entry_stop > 11:
        raise NotImplementedError("Entries 12+ are not translated in DEM_AtariIII.py yet")

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
    if entry_stop == 6:
        return ctx

    # %%% ENTRY 7
    if _use_checkpoint(7):
        ctx = _load_context(7, "pre")
    elif _capture_enabled(7, "pre"):
        _save_context(7, "pre", ctx)
    ctx["MDP"] = _entry7_assimilate_sequences(
        ctx["PDP"]["O"], ctx["MDP"], ctx["entry6_windows"], int(ctx["Ne"])
    )
    if _capture_enabled(7, "post"):
        _save_context(7, "post", ctx)
    if entry_stop == 7:
        return ctx

    # %%% ENTRY 8
    if _use_checkpoint(8):
        ctx = _load_context(8, "pre")
    elif _capture_enabled(8, "pre"):
        _save_context(8, "pre", ctx)
    ctx["entry8_NT"] = 100
    n_outer = _entry8_outer_loop_count()
    ctx["entry8_outer"] = n_outer
    if entry_stop == 8:
        ctx["MDP"] = _entry8_training_assimilations(
            ctx["PDP"]["O"], ctx["MDP"], int(ctx["Ne"]), nt=int(ctx["entry8_NT"]), n_outer=n_outer
        )
        if _capture_enabled(8, "post"):
            _save_context(8, "post", ctx)
        return ctx

    # %%% ENTRY 9 (inside Entry 8 outer loop in the MATLAB snippet)
    if _use_checkpoint(9):
        ctx = _load_context(9, "pre")
    elif _capture_enabled(9, "pre"):
        _save_context(9, "pre", ctx)
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
    if _capture_enabled(9, "post"):
        _save_context(9, "post", ctx)
    if entry_stop == 9:
        return ctx

    # %%% ENTRY 10 (NESS sort, goals refresh, paths-to-hits P)
    if _use_checkpoint(10):
        ctx = _load_context(10, "pre")
    elif _capture_enabled(10, "pre"):
        _save_context(10, "pre", ctx)
    mdp10, j10 = spm_RDP_sort(copy.deepcopy(ctx["MDP"]))
    ctx["entry10_j"] = j10
    c_val = float(ctx["C"])
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
    if entry_stop == 10:
        return ctx

    # %%% ENTRY 11 (costs, nested RDP, ledger horizon T = 64)
    if _use_checkpoint(11):
        ctx = _load_context(11, "pre")
    elif _capture_enabled(11, "pre"):
        _save_context(11, "pre", ctx)

    mdp_e11 = ctx["MDP"]
    c_val = float(ctx["C"])
    mdp_e11 = spm_set_costs(
        mdp_e11,
        np.array([2.0, 3.0], dtype=np.float64),
        np.array([c_val, -c_val], dtype=np.float64),
    )
    ctx["MDP"] = mdp_e11
    rdp = spm_mdp2rdp(mdp_e11)
    rdp["T"] = 64.0
    ctx["RDP"] = rdp

    if _capture_enabled(11, "post"):
        _save_context(11, "post", ctx)
    if entry_stop == 11:
        return ctx

    return ctx

__all__ = [
    "run_dem_atariiii",
    "dem_atariiii_paths_to_hits_P",
    "_entry8_training_assimilations",
    "_entry9_basin_training_loop",
]

