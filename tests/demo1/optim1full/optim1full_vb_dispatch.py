"""OPTIM1FULL W2 — VB module dispatch (fidelity vs optim).

Single policy surface for ``spm_MDP_VB_XXX`` vs ``spm_MDP_VB_XXX_optim``.

**Lanes:**
- ``fidelity`` — historical Product B parity oracle. Since 2026-07-13 this is a
  **diagnostic-only** lane, reached on the dispatch surface *only* by an explicit
  ``--vb-fidelity`` / ``RGMS_OPTIM1FULL_VB_DEV_OPTIM=0``. The fidelity Entry-12 tier
  gates (``--tier3a/3e/3f`` without the ``vb-optim`` prefix) call ``spm_MDP_VB_XXX``
  directly and do **not** go through this dispatch surface.
- ``optim`` — W2 sign-off via ``optim1full_vb_optim_matlab_equivalence`` (frozen
  MATLAB ``pdp_mat``); also the go-forward compute lane for the integrated driver.
- ``dispatch`` — full driver default. **Resolves to ``optim`` by default** (OPTIM1FULL
  go-forward compute); resolves to ``fidelity`` only when explicitly disabled via
  ``--vb-fidelity`` / ``RGMS_OPTIM1FULL_VB_DEV_OPTIM`` ∈ {``0``,``false``,``no``,``off``}.

See ``OPTIM1FULL.md`` § **W2 reference — spm_MDP_VB_XXX_optim** and
§ **Current status — optim adoption**.
"""
from __future__ import annotations

import argparse
import os
from typing import Any, Callable, Literal

VbLane = Literal["dispatch", "fidelity", "optim"]

OPTIM1FULL_VB_DEV_OPTIM_ENV = "RGMS_OPTIM1FULL_VB_DEV_OPTIM"

_vb_dev_optim_override: bool | None = None


def configure_vb_dev_optim(enabled: bool | None) -> None:
    """Programmatic dev-lane switch (``None`` clears override → env only)."""
    global _vb_dev_optim_override
    _vb_dev_optim_override = enabled
    if enabled is True:
        os.environ[OPTIM1FULL_VB_DEV_OPTIM_ENV] = "1"
    elif enabled is False:
        os.environ[OPTIM1FULL_VB_DEV_OPTIM_ENV] = "0"


def add_vb_dev_optim_cli_argument(parser: argparse.ArgumentParser) -> None:
    """Register the optim/fidelity lane switches on an OPTIM1FULL driver CLI.

    ``--vb-dev-optim`` is retained for back-compat but is now a **no-op** (optim is the
    default). ``--vb-fidelity`` is the diagnostic escape hatch that forces the historical
    fidelity ``spm_MDP_VB_XXX`` on the dispatch surface.
    """
    parser.add_argument(
        "--vb-dev-optim",
        action="store_true",
        help="(back-compat no-op — optim is now the dispatch default)",
    )
    parser.add_argument(
        "--vb-fidelity",
        action="store_true",
        help=(
            "Diagnostic: force fidelity spm_MDP_VB_XXX on the dispatch surface "
            "(default is optim). Use only for fidelity-vs-optim investigation."
        ),
    )


def apply_vb_dev_optim_cli(ns: Any) -> bool:
    """Apply lane switches from a parsed namespace; return resolved dev-optim state.

    ``--vb-fidelity`` wins over ``--vb-dev-optim`` if both are somehow present.
    """
    if bool(getattr(ns, "vb_fidelity", False)):
        configure_vb_dev_optim(False)
    elif bool(getattr(ns, "vb_dev_optim", False)):
        configure_vb_dev_optim(True)
    return optim1full_vb_dev_optim_enabled()


def optim1full_vb_dev_optim_enabled() -> bool:
    """Return True when the dispatch lane should resolve to ``optim`` (the default).

    OPTIM1FULL go-forward compute is the optim lane (2026-07-13). Fidelity is a
    diagnostic escape hatch only: return False **iff** an explicit override is set to
    False, or ``RGMS_OPTIM1FULL_VB_DEV_OPTIM`` is one of {``0``,``false``,``no``,``off``}.
    """
    if _vb_dev_optim_override is not None:
        return bool(_vb_dev_optim_override)
    env = str(os.getenv(OPTIM1FULL_VB_DEV_OPTIM_ENV, "")).strip().lower()
    if env in ("0", "false", "no", "off"):
        return False
    return True


def resolve_vb_lane(lane: VbLane) -> Literal["fidelity", "optim"]:
    if lane == "fidelity":
        return "fidelity"
    if lane == "optim":
        return "optim"
    return "optim" if optim1full_vb_dev_optim_enabled() else "fidelity"


def optim1full_vb_dispatch_status() -> dict[str, Any]:
    """Resolved dispatch state for logs / export manifests."""
    return {
        "vb_lane_dispatch_resolves_to": resolve_vb_lane("dispatch"),
        "vb_dev_optim_env": os.getenv(OPTIM1FULL_VB_DEV_OPTIM_ENV, ""),
        "vb_dev_optim_override": _vb_dev_optim_override,
    }


def spm_mdp_vb_xxx_callable(lane: VbLane = "dispatch") -> Callable[..., Any]:
    """Return ``spm_MDP_VB_XXX`` or ``spm_MDP_VB_XXX_optim`` for ``lane``."""
    resolved = resolve_vb_lane(lane)
    if resolved == "optim":
        from python_src.optimized.toolbox.DEM.spm_MDP_VB_XXX_optim import spm_MDP_VB_XXX_optim

        return spm_MDP_VB_XXX_optim
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    return spm_MDP_VB_XXX


def spm_mdp_vb_xxx_rand_buf_patch_target(lane: VbLane = "dispatch") -> str:
    """Full dotted path for ledger/tag ``vb_rand_buf`` injection patch.

    Fidelity lane patches ``spm_MDP_VB_XXX._vb_load_matlab_rand_buf``.

    Optim lane must patch ``vb_rng_optim.vb_load_matlab_rand_buf`` — the reference the
    standalone optim VB actually calls (``VbRandContext.__enter__`` →
    ``VbMatlabRandReplay(vb_load_matlab_rand_buf())``). ``vb_rng_optim`` imports that name
    **by value** from ``vb_rng_replay_optim``, so patching the *definition* module
    (``vb_rng_replay_optim.vb_load_matlab_rand_buf``) does NOT intercept the call and the
    optim VB silently replays the default tag buffer instead of the injected ledger
    segment (draws start ``0.8147…`` instead of the segment). See OPTIM1FULL.md
    § "CURRENT RED FLAG" (2026-07-13) — this was the root of the integrated 4a ``a`` red.
    """
    if resolve_vb_lane(lane) == "optim":
        return "python_src.optimized.toolbox.DEM.vb_rng_optim.vb_load_matlab_rand_buf"
    return "python_src.toolbox.DEM.spm_MDP_VB_XXX._vb_load_matlab_rand_buf"


def spm_mdp_vb_xxx_patch_module_name(lane: VbLane = "dispatch") -> str:
    """Deprecated — use :func:`spm_mdp_vb_xxx_rand_buf_patch_target`."""
    target = spm_mdp_vb_xxx_rand_buf_patch_target(lane)
    return target.rsplit(".", 1)[0]


def spm_mdp_vb_xxx_timing_module(lane: VbLane = "dispatch") -> Any:
    """Import module for ``_VB_TIMING_DEPTH`` reset before each gate lane run."""
    if resolve_vb_lane(lane) == "optim":
        from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as mod

        return mod
    import python_src.toolbox.DEM.spm_MDP_VB_XXX as mod

    return mod
