"""FSL backward — Entry 2 only (``spm_MDP_pong``; not Entry 12).

Ledger: ``run_entry2_pong`` / ``build_s_matrix``.

**Split validation (default sign-off):** Engine ``rng(2)`` ``spm_MDP_pong(12,9,4,true,0)`` vs
``GDP_post_entry2``, ``RGB_post_entry2``, ``S_post_entry2`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

**Native ledger:** ``run_entry2_driver_ledger_replay`` — ``run_dem_atariiii(entry_stop=2)`` with
``dem_atari_rand_buf[0:K_2]``.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_entry2 import run_entry2_from_constants


def entry2_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build boundary dict from ``run_dem_atariiii`` context (post–Entry 1, pre–Entry 3)."""
    return {
        "nr": int(ctx["Nr"]),
        "nc": int(ctx["Nc"]),
        "nd": int(ctx["Nd"]),
        "na": True,
        "np_dist": 0,
    }


def run_entry2_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **2** ledger from materialized boundary.

    Required keys: ``nr``, ``nc``, ``nd``. Optional: ``na`` (default true), ``np_dist`` (default 0).
    """
    out = run_entry2_from_constants(
        nr=int(boundary["nr"]),
        nc=int(boundary["nc"]),
        nd=int(boundary["nd"]),
        na=bool(boundary.get("na", True)),
        np_dist=int(boundary.get("np_dist", 0)),
    )
    return {
        **out,
        "nr": int(boundary["nr"]),
        "nc": int(boundary["nc"]),
        "nd": int(boundary["nd"]),
    }


def pull_gdp_from_matlab_engine(eng: Any, *, expr: str = "GDP") -> dict[str, Any]:
    """Pull scalar ``GDP`` struct from Engine (pong output — not ``MDP{n}`` cell)."""
    eng.eval(f"rgms_gdp_pull = {expr};", nargout=0)
    ex = "rgms_gdp_pull"
    gdp: dict[str, Any] = {}
    gdp["T"] = float(np.asarray(eng.eval(f"{ex}.T"), dtype=np.float64).reshape(-1)[0])
    gdp["N"] = np.asarray(eng.eval(f"{ex}.N"), dtype=np.float64)
    gdp["U"] = np.asarray(eng.eval(f"{ex}.U"), dtype=np.float64)
    n_a = int(np.asarray(eng.eval(f"numel({ex}.A)"), dtype=np.int64).reshape(-1)[0])
    gdp["A"] = [
        np.asarray(eng.eval(f"full({ex}.A{{{g + 1}}})"), dtype=np.float64) for g in range(n_a)
    ]
    n_b = int(np.asarray(eng.eval(f"numel({ex}.B)"), dtype=np.int64).reshape(-1)[0])
    gdp["B"] = [
        np.asarray(eng.eval(f"full({ex}.B{{{f + 1}}})"), dtype=np.float64) for f in range(n_b)
    ]
    n_c = int(np.asarray(eng.eval(f"numel({ex}.C)"), dtype=np.int64).reshape(-1)[0])
    gdp["C"] = [np.asarray(eng.eval(f"{ex}.C{{{g + 1}}}"), dtype=np.float64) for g in range(n_c)]
    n_d = int(np.asarray(eng.eval(f"numel({ex}.D)"), dtype=np.int64).reshape(-1)[0])
    gdp["D"] = []
    for f in range(n_d):
        eng.eval(f"rgms_d = full({ex}.D{{{f + 1}}});", nargout=0)
        gdp["D"].append(np.asarray(eng.eval("rgms_d"), dtype=np.float64))
    n_e = int(np.asarray(eng.eval(f"numel({ex}.E)"), dtype=np.int64).reshape(-1)[0])
    gdp["E"] = []
    for f in range(n_e):
        eng.eval(f"rgms_e = full({ex}.E{{{f + 1}}});", nargout=0)
        gdp["E"].append(np.asarray(eng.eval("rgms_e"), dtype=np.float64))
    n_h = int(np.asarray(eng.eval(f"numel({ex}.H)"), dtype=np.int64).reshape(-1)[0])
    gdp["H"] = [np.asarray(eng.eval(f"{ex}.H{{{f + 1}}}"), dtype=np.float64) for f in range(n_h)]
    id_a_num = int(np.asarray(eng.eval(f"numel({ex}.id.A)"), dtype=np.int64).reshape(-1)[0])
    gdp["id"] = {
        "A": [
            np.atleast_2d(np.asarray(eng.eval(f"{ex}.id.A{{{g + 1}}}"), dtype=np.float64))
            for g in range(id_a_num)
        ],
    }
    for fname in ("reward", "contraint", "control"):
        flg = np.asarray(eng.eval(f"isfield({ex}.id,'{fname}')"), dtype=float).ravel()
        if flg.size and float(flg.flat[0]) != 0:
            gdp["id"][fname] = int(
                np.asarray(eng.eval(f"{ex}.id.{fname}"), dtype=np.int64).reshape(-1)[0]
            )
    eng.eval("clear rgms_gdp_pull rgms_d rgms_e", nargout=0)
    return gdp


def pull_gdp_bundle_from_matlab_engine(eng: Any, *, expr: str = "GDP") -> dict[str, Any]:
    """Pull ``GDP``, ``hid``, ``cid``, ``con``, ``RGB`` after Engine ``spm_MDP_pong``."""
    gdp = pull_gdp_from_matlab_engine(eng, expr=expr)
    hid = np.asarray(eng.eval("hid"), dtype=np.float64)
    cid = np.asarray(eng.eval("cid"), dtype=np.float64)
    con = np.asarray(eng.eval("con"), dtype=np.float64)
    rgb_n = np.asarray(eng.eval("RGB.N"), dtype=np.float64).ravel()
    nr = int(np.asarray(eng.eval("size(RGB.G,1)"), dtype=np.int64).reshape(-1)[0])
    nc = int(np.asarray(eng.eval("size(RGB.G,2)"), dtype=np.int64).reshape(-1)[0])
    g_cells: list[list[np.ndarray]] = []
    for i in range(nr):
        row: list[np.ndarray] = []
        for j in range(nc):
            eng.eval(f"rgms_gij = double(RGB.G{{{i + 1},{j + 1}}});", nargout=0)
            row.append(np.asarray(eng.eval("rgms_gij"), dtype=np.float64))
        g_cells.append(row)
    rgb = {"N": rgb_n, "G": g_cells, "V": []}
    return {"gdp": gdp, "hid": hid, "cid": cid, "con": con, "rgb": rgb}


def run_entry2_matlab_pong(
    eng: Any,
    *,
    nr: int = 12,
    nc: int = 9,
    nd: int = 4,
    authority_mat_path: str | Path | None = None,
) -> dict[str, Any]:
    """FSL split-validation: MATLAB ``rng(2)`` ``spm_MDP_pong`` (snippet branch)."""
    eng.eval(
        "rng(2); "
        f"[GDP, hid, cid, con, RGB] = spm_MDP_pong({nr}, {nc}, {nd}, true, 0);",
        nargout=0,
    )
    bundle = pull_gdp_bundle_from_matlab_engine(eng, expr="GDP")
    s = np.ones((4, 3), dtype=np.float64)
    s[0, :] = [float(nr), float(nc), 1.0]
    eng.eval("clear GDP hid cid con RGB rgms_gij", nargout=0)
    return {
        **bundle,
        "S": s,
        "nr": nr,
        "nc": nc,
        "nd": nd,
        "validation_lane": "matlab_pong",
        "authority_mat": str(authority_mat_path) if authority_mat_path else None,
    }


def run_entry2_driver_ledger_replay(
    *,
    k_use: int | None = None,
) -> dict[str, Any]:
    """Native FSL lane: driver Entries 1–2 with ``dem_atari_rand_buf`` replay."""
    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        fsl_backward_replay_matlab_draws,
        fsl_entry2_driver_env,
        load_dem_atari_rand_buf,
        load_entry2_k_py,
    )

    k_2 = int(k_use) if k_use is not None else load_entry2_k_py()
    buf, _k_11 = load_dem_atari_rand_buf()
    with fsl_entry2_driver_env(deadline_minutes="15"):
        with fsl_backward_replay_matlab_draws(k_2, buf) as ctr:
            ctx = run_dem_atariiii(entry_stop=2)
        used = int(ctr[0])
    if used != k_2:
        raise RuntimeError(
            f"Entry 2 driver replay: used {used} draws, expected K_2={k_2}"
        )
    return {
        "gdp": ctx["GDP"],
        "hid": ctx["hid"],
        "cid": ctx["cid"],
        "con": ctx["con"],
        "rgb": ctx["RGB"],
        "S": ctx["S"],
        "nr": int(ctx["Nr"]),
        "nc": int(ctx["Nc"]),
        "nd": int(ctx["Nd"]),
        "validation_lane": "driver_ledger_replay",
        "k_2": k_2,
        "draws_used": used,
    }
