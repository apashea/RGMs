"""OPTIM1 — Entry 4 ``spm_faster_structure_learning_optim`` ledger."""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

import numpy as np

from python_src.optimized.toolbox.DEM.spm_faster_structure_learning_optim import (
    spm_faster_structure_learning_optim,
)
from python_src.toolbox.DEM.dem_atariiii_entry4 import (
    ENTRY4_O_COLS,
    atari_S_and_Sc,
    slice_pdp_o_for_entry4,
)


def faster_structure_learning_optim(
    pdp_o_sl: list[list[Any]],
    s: np.ndarray,
    sc: int,
    *,
    rgm_eig_pair: Optional[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
    rgm_mi_override_fn: Optional[Callable[[list[Any], int], np.ndarray]] = None,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
) -> list[dict[str, Any]]:
    """Same ledger as fidelity Entry **4**; structure kernel = optim."""
    return spm_faster_structure_learning_optim(
        pdp_o_sl,
        s,
        sc,
        rgm_eig_pair=rgm_eig_pair,
        rgm_mi_override_fn=rgm_mi_override_fn,
        link_dir_mi_fn=link_dir_mi_fn,
    )


__all__ = [
    "ENTRY4_O_COLS",
    "atari_S_and_Sc",
    "slice_pdp_o_for_entry4",
    "faster_structure_learning_optim",
]
