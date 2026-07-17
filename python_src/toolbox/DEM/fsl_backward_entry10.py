"""FSL backward — Entry 10 only (not Entry 12, not full ``run_dem_atariiii``).

Ledger: ``spm_RDP_sort`` → ``spm_set_goals`` → paths-to-hits ``P``.

**Split validation:** FSL sign-off injects MATLAB ``eig(B,'nobalance')`` (see
``fsl_backward_run_entry10_isolated.py``, default ``RGMS_FSL_RDP_SORT_MATLAB_EIG=1``) so sorting
uses MATLAB's eigen determination while prune / compress / goals / ``P`` stay in Python. Native eig
alone is not authority-aligned at full Atari scale — ``Atari_example.md`` § Entry 10 eigen limitation.
"""

from __future__ import annotations

import copy
import os
from typing import Any, Callable

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_paths import dem_atariiii_paths_to_hits_P
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals


def _env_matlab_eig_for_fsl_backward() -> bool:
    return str(os.getenv("RGMS_FSL_RDP_SORT_MATLAB_EIG", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def run_entry10_from_mdp(
    mdp: list[dict[str, Any]],
    *,
    c_val: float = 32.0,
    nt_p: int = 32,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> dict[str, Any]:
    """
    Ledger Entry 10 only: ``spm_RDP_sort`` → ``spm_set_goals`` → paths-to-hits ``P``.

    Output ``mdp`` matches MATLAB ``MDP_pre_entry11`` when ``eig`` is MATLAB-injected (FSL sign-off).

    Pass ``eig=`` from Engine (``_make_matlab_spm_RDP_sort_eig``) or rely on
    ``RGMS_FSL_RDP_SORT_MATLAB_EIG`` in the isolated runner. Omitting MATLAB ``eig`` exercises native
    ``spm_RDP_sort`` only (diagnostic; not FSL backward sign-off on full-scale ``B``).
    """
    mdp_in = copy.deepcopy(mdp)
    # Default: ``spm_RDP_sort`` → ``eig_matlab_nobalance`` (geevx if linked, else numpy) + ``min_tie`` principal.
    # MATLAB-paired FSL lane: pass ``eig=`` from Engine or set ``RGMS_FSL_RDP_SORT_MATLAB_EIG=1``
    # in ``fsl_backward_run_entry10_isolated.py``.
    mdp10, j10 = spm_RDP_sort(mdp_in, eig=eig)
    mdp10 = spm_set_goals(
        mdp10,
        np.array([2, 3], dtype=np.int64),
        np.array([c_val, -c_val], dtype=np.float64),
    )
    nm = len(mdp10)
    b1 = np.asarray(mdp10[nm - 1]["b"][0][0], dtype=np.float64)
    bp = (np.sum(b1, axis=2) > 0).astype(np.float64)
    hid_list = mdp10[nm - 1]["id"].get("hid", [])
    hid_arr = (
        np.asarray(hid_list, dtype=np.int64).ravel()
        if hid_list
        else np.zeros(0, dtype=np.int64)
    )
    p_mat = dem_atariiii_paths_to_hits_P(bp, hid_arr, nt_p)
    return {
        "mdp": mdp10,
        "P": p_mat,
        "hid": hid_arr,
        "entry10_j": j10,
        "entry10_Nt": nt_p,
    }
