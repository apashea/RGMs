"""DEM_AtariIII Entry 4 — ``spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc)``."""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

import numpy as np

from python_src.toolbox.DEM.spm_faster_structure_learning import spm_faster_structure_learning

ENTRY4_O_COLS = 1000


def atari_S_and_Sc() -> tuple[np.ndarray, int]:
    """MATLAB snippet constants for ``S`` and ``Sc`` (``Nr=12``, ``Nc=9``)."""
    s = np.ones((4, 3), dtype=np.float64)
    s[0, :] = [12.0, 9.0, 1.0]
    return s, 9


def slice_pdp_o_for_entry4(pdp_o_cells: list[list[Any]]) -> list[list[Any]]:
    """``PDP.O(:,1:1000)`` as nested Python lists (1-based column count)."""
    ncol = ENTRY4_O_COLS
    return [[row[t] for t in range(ncol)] for row in pdp_o_cells]


def faster_structure_learning(
    pdp_o_sl: list[list[Any]],
    s: np.ndarray,
    sc: int,
    *,
    rgm_eig_pair: Optional[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
    rgm_mi_override_fn: Optional[Callable[[list[Any], int], np.ndarray]] = None,
    link_dir_mi_fn: Optional[Callable[[np.ndarray], float]] = None,
) -> list[dict[str, Any]]:
    """Run Entry **4** ledger; optional hooks are FSL / oracle-only (see ``fsl_backward_entry4``)."""
    return spm_faster_structure_learning(
        pdp_o_sl,
        s,
        sc,
        rgm_eig_pair=rgm_eig_pair,
        rgm_mi_override_fn=rgm_mi_override_fn,
        link_dir_mi_fn=link_dir_mi_fn,
    )
