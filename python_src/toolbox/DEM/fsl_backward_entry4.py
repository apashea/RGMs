"""FSL backward — Entry 4 only (``spm_faster_structure_learning`` on ``PDP.O(:,1:1000)``).

**Split validation (project-critical):** FSL sign-off injects MATLAB ``eig`` / ``MI`` / ``spm_dir_MI``
via keyword hooks (defaults in ``fsl_backward_run_entry4_isolated.py``) so grouping matches the
``rng(2)`` ledger (**485**-wide state, not native **511**). Native Python alone is diagnostic only —
see ``Atari_example.md`` § **511 vs 485** and Entry **4** bottlenecks.

Input: ``PDP.O`` first **1000** columns + ``S``, ``Sc``.
Authority: ``MDP_pre_entry5`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_entry4 import (
    ENTRY4_O_COLS,
    atari_S_and_Sc,
    faster_structure_learning,
    slice_pdp_o_for_entry4,
)

# FSL sign-off: Engine runs MATLAB ``spm_faster_structure_learning`` on the paired ``PDP_O``
# fixture until native Python ``MDP`` tensors match ``MDP_pre_entry5`` (485-wide ledger).
# Hook-only Python remains diagnostic (``RGMS_FSL_ENTRY4_MATLAB_STRUCTURE_LEARNING=0``).


def entry4_boundary_from_driver_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build boundary dict from ``run_dem_atariiii`` context (post–Entry 3, pre–Entry 5)."""
    s, sc = atari_S_and_Sc()
    return {
        "pdp_o_sl": slice_pdp_o_for_entry4(ctx["PDP"]["O"]),
        "S": s,
        "Sc": sc,
        "entry4_o_cols": ENTRY4_O_COLS,
    }


def run_entry4_from_boundary(
    boundary: dict[str, Any],
    *,
    rgm_eig_pair: Optional[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
    rgm_mi_override_fn: Optional[Callable[[list[Any], int], np.ndarray]] = None,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
) -> dict[str, Any]:
    """
    Run Entry **4** ledger from a materialized boundary.

    Required keys: ``pdp_o_sl``, ``S``, ``Sc``. Pass MATLAB hooks for FSL sign-off.
    """
    mdp_out = faster_structure_learning(
        boundary["pdp_o_sl"],
        np.asarray(boundary["S"], dtype=np.float64),
        int(boundary["Sc"]),
        rgm_eig_pair=rgm_eig_pair,
        rgm_mi_override_fn=rgm_mi_override_fn,
        link_dir_mi_fn=link_dir_mi_fn,
    )
    return {
        "mdp": mdp_out,
        "Nm": len(mdp_out),
        "entry4_o_cols": int(boundary.get("entry4_o_cols", ENTRY4_O_COLS)),
    }


def run_entry4_matlab_structure_learning(
    eng: Any,
    *,
    authority_mat_path: str | Path,
) -> dict[str, Any]:
    """
    FSL split-validation: MATLAB ``spm_faster_structure_learning`` on ``PDP_O(:,1:1000)``.

    Uses ``PDP_O`` from the ``rng(2)`` authority ``.mat`` (same ledger as ``MDP_pre_entry5``).
    """
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    mat_p = Path(authority_mat_path).resolve()
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing authority mat: {mat_p}")

    import matlab  # Engine-only (FSL lane)

    s, sc = atari_S_and_Sc()
    mat_s = str(mat_p).replace("\\", "/")
    eng.eval(f"load('{mat_s}');", nargout=0)
    s_list = s.tolist()
    eng.workspace["rgms_S_entry4"] = matlab.double(s_list, size=(4, 3))
    eng.eval(
        "S = rgms_S_entry4; "
        f"Sc = {int(sc)}; "
        f"MDP = spm_faster_structure_learning(PDP_O(:,1:{ENTRY4_O_COLS}), S, Sc);",
        nargout=0,
    )
    mdp_out = _pull_mdp_from_matlab(eng, "MDP")
    eng.eval("clear rgms_S_entry4 MDP", nargout=0)
    return {
        "mdp": mdp_out,
        "Nm": len(mdp_out),
        "entry4_o_cols": ENTRY4_O_COLS,
        "validation_lane": "matlab_structure_learning",
    }
