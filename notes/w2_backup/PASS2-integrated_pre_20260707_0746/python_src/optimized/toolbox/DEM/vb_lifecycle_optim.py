"""W2 — optim partial nested return (**0b** — **PASS** 2026-07-03).

Fidelity ``_vb_build_partial_output`` begins with ``copy.deepcopy(models[0])`` (~128 nested
returns per call4). Optim version updates ``models[0]`` in place and copies only ``X``/``P``
columns — **3f PASS**, 0 PDP mismatches.

**Experiment 0a** (nested in-place ``checkX`` via ``run_spm_MDP_VB_XXX_optim_entry``): **FAIL**
``PDP.MDP.Q.E[0]`` max abs **~1.04** — root cause: partial return **replaced shared hierarchical
``Q`` dict** with belief ``Q_cells``, not ``checkX`` (``.m`` never touches ``Q``). **Fixed 5-C-arena.**

See ``XXX_optim.md`` + ``OPTIM1FULL.md`` § W2 ledger **3-T1-0b**.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _vb_build_partial_output_optim(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> Any:
    """
    Partial nested return — update ``models[0]`` in place (``.m`` ``mdp`` lifetime).

    Same field layout as fidelity ``_vb_build_partial_output``; array copies only where
    fidelity copied for ``X``/``P`` columns, not whole-tree ``deepcopy``.
    """
    if len(models) != 1:
        return models
    out = models[0]
    out["id"] = bundle["id"][0]
    out["X"] = [np.asarray(x, dtype=np.float64).copy() for x in models[0]["X"]]
    out["P"] = [np.asarray(x, dtype=np.float64).copy() for x in models[0]["P"]]

    # Hierarchical child: ``mdp.Q = MDP(m).Q`` (~1163) — **shared qrec dict**. Replacing with
    # bundle belief ``Q_cells`` breaks parent ``Q.F`` accumulation (was misread as **0e** need).
    if not isinstance(out.get("Q"), dict):
        Q_cells: list[np.ndarray] = []
        for f in range(len(bundle["Q"][0])):
            cols = [
                np.asarray(bundle["Q"][0][f][t], dtype=np.float64).reshape(-1, 1)
                for t in range(int(bundle["T"]))
            ]
            Q_cells.append(np.hstack(cols))
        out["Q"] = Q_cells
    for _k in ("Y", "j", "i", "xn", "wn", "dn", "un", "sn"):
        if _k in models[0]:
            out[_k] = models[0][_k]
    out["_rgms_partial_v"] = 1
    return out
