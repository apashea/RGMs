"""FSL backward — Entry 1 only (snippet constants; no ``spm_*`` call).

Ledger: ``apply_entry1_constants``.

**Authority:** ``entry1_Nr``, ``entry1_Nc``, ``entry1_Sc``, ``entry1_Nd``, ``entry1_C`` in
``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (and legacy scalar ``C``).

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

from typing import Any

from python_src.toolbox.DEM.dem_atariiii_entry1 import apply_entry1_constants, entry1_constants_dict


def entry1_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Entry **1** has no upstream boundary — returns empty dict (constants are fixed)."""
    return {}


def run_entry1_from_boundary(_boundary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run Entry **1** ledger (snippet constants only)."""
    const = entry1_constants_dict()
    return {
        **const,
        "validation_lane": "native_constants",
    }


def run_entry1_driver_ledger_replay(
    *,
    k_use: int | None = None,
) -> dict[str, Any]:
    """Native FSL lane: ``run_dem_atariiii(entry_stop=1)`` with optional ``dem_atari_rand_buf`` replay."""
    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        fsl_backward_replay_matlab_draws,
        fsl_entry1_driver_env,
        load_dem_atari_rand_buf,
        load_entry1_k_py,
    )

    k_1 = int(k_use) if k_use is not None else load_entry1_k_py()
    buf, _k_11 = load_dem_atari_rand_buf()
    with fsl_entry1_driver_env(deadline_minutes="5"):
        if k_1 > 0:
            with fsl_backward_replay_matlab_draws(k_1, buf) as ctr:
                ctx = run_dem_atariiii(entry_stop=1)
            used = int(ctr[0])
        else:
            ctx = run_dem_atariiii(entry_stop=1)
            used = 0
    if used != k_1:
        raise RuntimeError(
            f"Entry 1 driver replay: used {used} draws, expected K_1={k_1}"
        )
    return {
        "Nr": int(ctx["Nr"]),
        "Nc": int(ctx["Nc"]),
        "Sc": int(ctx["Sc"]),
        "Nd": int(ctx["Nd"]),
        "C": float(ctx["C"]),
        "validation_lane": "driver_ledger_replay",
        "k_1": k_1,
        "draws_used": used,
    }
