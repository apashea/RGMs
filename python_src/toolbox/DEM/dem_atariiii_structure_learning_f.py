"""``DEM_AtariIII.m`` structure-learning ``F`` column (L288–293) — library helper.

Used by OPTIM1FULL native plots and parity spine export. No test-harness imports.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from python_src.toolbox.DEM.entry12_plot import spm_get_hits


def _unwrap_b1(b_field: Any) -> np.ndarray:
    """First factor of ``B``/``b`` as MATLAB 3-D Dirichlet (drop list + leading singleton)."""
    x = b_field[0] if isinstance(b_field, list) else b_field
    while isinstance(x, list):
        if not x:
            raise ValueError("empty B/b cell")
        x = x[0]
    arr = np.asarray(x, dtype=np.float64)
    # Python load of ``MDP{end}.b{1}`` may be ``(1, Ns, Ns, Np)``; MATLAB is 3-D.
    while arr.ndim > 3 and int(arr.shape[0]) == 1:
        arr = arr[0]
    return arr


def _pdp_b1(pdp: Any) -> np.ndarray:
    return _unwrap_b1(pdp["B"])


def _mdp_end_b1(mdp: Any) -> np.ndarray:
    if not isinstance(mdp, list) or not mdp:
        raise TypeError("MDP must be a non-empty list for structure F rows 5–6")
    end = mdp[-1]
    return _unwrap_b1(end["b"])


def _pdp_elbo(pdp: Any) -> float:
    q = pdp.get("Q", {})
    qf = float(np.asarray(q.get("F", 0.0), dtype=np.float64).ravel()[0])
    f_field = pdp.get("F", 0.0)
    return qf + float(np.sum(np.asarray(f_field, dtype=np.float64)))


def _pdp_hit_count(pdp: Any, gdp_id: dict[str, Any]) -> float:
    # DEM_AtariIII.m: h = spm_get_hits(PDP.Q.o{1}, GDP.id) — dense ``o``, not cell ``O``.
    q = pdp.get("Q", {})
    o_levels = q.get("o")
    if o_levels is None:
        o_levels = q.get("O")
    if not isinstance(o_levels, list) or not o_levels:
        raise KeyError("PDP.Q.o missing for structure F hit count")
    h = spm_get_hits(o_levels[0], gdp_id)
    return float(np.asarray(h).size)


def structure_learning_f_column(
    pdp: Any,
    mdp: Any,
    gdp_id: dict[str, Any],
) -> np.ndarray:
    """One column of ``F`` (DEM_AtariIII.m L288–293) before merge/basin."""
    b1 = _pdp_b1(pdp)
    mb1 = _mdp_end_b1(mdp)
    col = np.array(
        [
            float(b1.shape[1]),
            float(b1.shape[2]) if b1.ndim >= 3 else 1.0,
            _pdp_elbo(pdp),
            _pdp_hit_count(pdp, gdp_id),
            float(mb1.shape[1]),
            float(mb1.shape[2]) if mb1.ndim >= 3 else 1.0,
        ],
        dtype=np.float64,
    )
    return col


__all__ = ["structure_learning_f_column"]
