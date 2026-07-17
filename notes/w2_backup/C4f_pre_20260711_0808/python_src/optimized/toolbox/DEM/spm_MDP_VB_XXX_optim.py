"""OPTIM1FULL W2 — fast ``spm_MDP_VB_XXX`` matching ``spm_MDP_VB_XXX.m`` structure.

**Authority:** ``XXX_optim.md`` + ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m``.

**Status (2026-07-04):** **4-X-1** — thin public wrapper → ``run_optim_vb`` only; no patch layer.

Prove equivalence: ``optim1full_vb_optim_equivalence.py`` / ``--vb-optim-tier3f``.
"""
from __future__ import annotations

from typing import Any

from python_src.optimized.toolbox.DEM.vb_entry_optim import run_optim_vb

__all__ = ["spm_MDP_VB_XXX_optim", "run_optim_vb"]


def spm_MDP_VB_XXX_optim(
    RDP: Any,
    OPTIONS: Any = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    W2 optim lane — delegates to ``run_optim_vb``.

    Nested hierarchical calls use ``run_child_vb`` (``vb_hierarchical_optim``) — **4-N-1**.
    """
    if OPTIONS is None:
        OPTIONS = {}
    return run_optim_vb(
        RDP,
        OPTIONS,
        monitoring=kwargs.get("monitoring", False),
        dump_subentries=kwargs.get("dump_subentries", False),
        reuse_matlab_draws=kwargs.get("reuse_matlab_draws", False),
    )
