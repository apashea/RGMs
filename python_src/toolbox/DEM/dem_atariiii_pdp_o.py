"""PDP.O column bounds for DEM_AtariIII / FSL backward (Entries 7–9 merges)."""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_pdp_o_max_col(
    *,
    ne: int,
    nt: int = 100,
    n_outer: int = 128,
    entry6_windows: list[dict[str, Any]] | None = None,
    min_col: int = 1000,
    pdp_width_cap: int | None = None,
) -> int:
    """
    Maximum 1-based column index required for ``PDP.O(:, cols)`` merges.

    Matches ``dump_MDP_pre_entry10.m``: Entry **7** hit/miss windows, then Entry **8/9**
    outer-loop offsets (``rem(i, 99)*NT`` schedule).
    """
    ne_i = int(ne)
    nt_i = int(nt)
    max_col = int(min_col)

    if entry6_windows:
        for rec in entry6_windows:
            t = np.asarray(rec["t"], dtype=np.int64).ravel(order="F")
            if t.size > 0:
                max_col = max(max_col, int(np.max(t + ne_i)))

    for ii in range(1, int(n_outer) + 1):
        offset = int(np.remainder(ii, 100 - 1)) * nt_i
        t = np.arange(0, nt_i + ne_i + 1, dtype=np.int64) + int(offset)
        max_col = max(max_col, int(np.max(t + ne_i)))

    if pdp_width_cap is not None:
        max_col = min(max_col, int(pdp_width_cap))
    return max_col


def assert_pdp_o_columns_sufficient(
    pdp_o_cells: list[list[Any]],
    *,
    ne: int,
    nt: int = 100,
    n_outer: int = 128,
    entry6_windows: list[dict[str, Any]] | None = None,
    min_col: int = 1000,
) -> int:
    """Raise ``ValueError`` if any merge column is out of range; return required ``max_col``."""
    if not pdp_o_cells or not pdp_o_cells[0]:
        raise ValueError("PDP_O must have at least one row and column")
    n_cols = len(pdp_o_cells[0])
    need = compute_pdp_o_max_col(
        ne=ne,
        nt=nt,
        n_outer=n_outer,
        entry6_windows=entry6_windows,
        min_col=min_col,
        pdp_width_cap=n_cols,
    )
    if need > n_cols:
        raise ValueError(
            f"PDP_O has {n_cols} columns but ledger requires {need} "
            f"(re-run dump_MDP_pre_entry10.m or extend PDP_O slice)"
        )
    return need
