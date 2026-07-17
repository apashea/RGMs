"""FSL backward — Entry 3 only (``spm_MDP_generate``; not Entry 12).

Ledger: ``prepare_gdp_for_generate`` → ``generate_mdp_rollout``.

**Split validation (default sign-off):** MATLAB ``spm_MDP_generate`` on the ``rng(2)``
ledger vs ``PDP_o`` / ``PDP_O`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

**Native ledger lane:** ``run_entry3_driver_ledger_replay`` — ``run_dem_atariiii(entry_stop=3)``
with ``dem_atari_rand_buf`` replay through ``K_3`` (preflight
``fsl_backward_preflight_rand_k_entry3.py``). Compare uses the same authority vars.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_entry3 import (
    ATARI_TRAINING_T_LEDGER,
    generate_mdp_rollout,
    prepare_gdp_for_generate,
)
from python_src.toolbox.DEM.dem_atariiii_entry4 import ENTRY4_O_COLS


def entry3_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build boundary dict from ``run_dem_atariiii`` context (post–Entry 2, pre–Entry 4)."""
    from python_src.toolbox.DEM.DEM_AtariIII import _training_horizon

    # MATLAB sets ``GDP.T = 10000`` after pong; do not use pong's small default ``GDP.T``.
    return {
        "gdp": ctx["GDP"],
        "training_t": int(_training_horizon()),
    }


def run_entry3_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **3** ledger from materialized boundary.

    Required keys: ``gdp``. Optional: ``training_t`` (default ``10000``).
    """
    tt = int(boundary.get("training_t", ATARI_TRAINING_T_LEDGER))
    gdp = prepare_gdp_for_generate(boundary["gdp"], training_t=tt)
    pdp = generate_mdp_rollout(gdp)
    return {
        "gdp": gdp,
        "pdp": pdp,
        "training_t": tt,
    }


def pull_pdp_from_matlab_engine(
    eng: Any,
    *,
    expr: str = "PDP",
    o_cols: int | None = ENTRY4_O_COLS,
) -> dict[str, Any]:
    """Pull ``PDP`` from Engine; default ``O`` slice is ``(:,1:1000)`` (Entry **4** input)."""
    pdp: dict[str, Any] = {}
    pdp["o"] = np.asarray(eng.eval(f"{expr}.o"), dtype=np.float64)
    pdp["s"] = np.asarray(eng.eval(f"{expr}.s"), dtype=np.float64)
    pdp["u"] = np.asarray(eng.eval(f"{expr}.u"), dtype=np.float64)
    pdp["T"] = float(np.asarray(eng.eval(f"{expr}.T"), dtype=np.float64).reshape(-1)[0])
    ng = int(np.asarray(eng.eval(f"numel({expr}.A)"), dtype=np.int64).reshape(-1)[0])
    ncol = int(o_cols) if o_cols is not None else int(pdp["T"])
    o_cells: list[list[np.ndarray]] = []
    for g in range(1, ng + 1):
        row: list[np.ndarray] = []
        for tt in range(1, ncol + 1):
            eng.eval(f"rgms_oc = full({expr}.O{{{g},{tt}}});", nargout=0)
            col = np.asarray(eng.eval("rgms_oc"), dtype=np.float64)
            if col.ndim == 1:
                col = col.reshape((-1, 1), order="F")
            row.append(col)
        o_cells.append(row)
    pdp["O"] = o_cells
    pdp["O_cols_pulled"] = ncol
    return pdp


def run_entry3_driver_ledger_replay(
    *,
    k_use: int | None = None,
) -> dict[str, Any]:
    """
    Native FSL lane: full driver Entries 1–3 with ``dem_atari_rand_buf`` replay.

    Requires ``fsl_backward_preflight_rand_k_entry3.py`` (writes ``K_py``) and FSL backward **1b**
    fixture ``dem_atari_rand_buf_through_entry11.mat``.
    """
    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        fsl_backward_replay_matlab_draws,
        fsl_entry3_driver_env,
        load_dem_atari_rand_buf,
        load_entry3_k_py,
    )

    k_3 = int(k_use) if k_use is not None else load_entry3_k_py()
    buf, _k_11 = load_dem_atari_rand_buf()
    with fsl_entry3_driver_env(deadline_minutes="45"):
        with fsl_backward_replay_matlab_draws(k_3, buf) as ctr:
            ctx = run_dem_atariiii(entry_stop=3)
        used = int(ctr[0])
    if used != k_3:
        raise RuntimeError(
            f"Entry 3 driver replay: used {used} draws, expected K_3={k_3} (unused_draws={k_3 - used})"
        )
    pdp = dict(ctx["PDP"])
    pdp["O_cols_pulled"] = ENTRY4_O_COLS
    return {
        "gdp": ctx["GDP"],
        "pdp": pdp,
        "training_t": ATARI_TRAINING_T_LEDGER,
        "validation_lane": "driver_ledger_replay",
        "k_3": k_3,
        "draws_used": used,
    }


def run_entry3_matlab_generate(
    eng: Any,
    *,
    authority_mat_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    FSL split-validation: MATLAB ``rng(2)`` pong + ``spm_MDP_generate`` (``T=10000``, ``tau=1``).
    """
    nr, nc, nd = 12, 9, 4
    eng.eval(
        "rng(2); "
        f"[GDP, hid, cid, con, RGB] = spm_MDP_pong({nr}, {nc}, {nd}, true, 0); "
        "GDP.tau = 1; "
        f"GDP.T = {ATARI_TRAINING_T_LEDGER}; "
        "PDP = spm_MDP_generate(GDP);",
        nargout=0,
    )
    pdp = pull_pdp_from_matlab_engine(eng, expr="PDP")
    eng.eval("clear GDP PDP rgms_oc", nargout=0)
    return {
        "pdp": pdp,
        "training_t": ATARI_TRAINING_T_LEDGER,
        "validation_lane": "matlab_generate",
        "authority_mat": str(authority_mat_path) if authority_mat_path else None,
    }
