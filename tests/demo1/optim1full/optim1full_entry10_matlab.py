"""OPTIM1FULL Product B — Entry **10** MATLAB spectral lane (Entries **1–11** segment).

Uses Engine ``eig(B,'nobalance')`` inject into ``spm_RDP_sort_optim`` (same class as OPTIM1
Product B Entry **10** scale). Full Engine ``spm_RDP_sort`` on a template overlay is not
used here — overlay without full MDP push broke VB call **1** dimensions.

OPTIM1FULL-only env: ``RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG=1``.
"""
from __future__ import annotations

import os
from typing import Any


def optim1full_entry10_matlab_eig_enabled() -> bool:
    """``RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG`` — default **on** for Product B parity."""
    raw = str(os.getenv("RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def run_entry10_optim1full_parity(
    ctx: dict[str, Any],
    eng: Any,
) -> dict[str, Any]:
    """Entry **10**: MATLAB ``eig`` inject → ``spm_RDP_sort_optim`` → goals → ``P``."""
    from python_src.optimized.toolbox.DEM.fsl_backward_entry10_optim import run_entry10_optim_from_mdp
    from tests.demo1.optim1full.optim1full_replay import matlab_eig_callable

    if not optim1full_entry10_matlab_eig_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG=1"
        )
    eig_fn = matlab_eig_callable(eng)
    out10 = run_entry10_optim_from_mdp(ctx["MDP"], c_val=float(ctx["C"]), eig=eig_fn)
    ctx["MDP"] = out10["mdp"]
    ctx["entry10_j"] = out10["entry10_j"]
    ctx["P"] = out10["P"]
    ctx["hid"] = out10["hid"]
    ctx["entry10_Nt"] = out10["entry10_Nt"]
    return ctx


def validation_entry10_metadata() -> dict[str, Any]:
    return {
        "entry10_eig_source": "matlab_engine" if optim1full_entry10_matlab_eig_enabled() else "native",
        "RGMS_OPTIM1FULL_ENTRY10_MATLAB_EIG": optim1full_entry10_matlab_eig_enabled(),
    }
