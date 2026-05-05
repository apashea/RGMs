"""
Bayesian model reduction likelihood over reduced Dirichlet models.

Pass 1 transliteration of ``spm_MDP_BMR.m`` (SPM toolbox).
"""

from __future__ import annotations

from typing import Any, List, Sequence

import numpy as np

from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_MDP_log_evidence import spm_MDP_log_evidence


def spm_MDP_BMR(qp: np.ndarray, rp: Sequence[Any]) -> np.ndarray:
    """
    FORMAT L = spm_MDP_BMR(qp, rp)

    ``rp`` — sequence of reduced priors (MATLAB cell ``rp{m}``).
    """
    rp_list: List[Any] = list(rp)
    np_ = len(rp_list)
    pp = np.zeros_like(np.asarray(qp, dtype=np.float64), dtype=np.float64)
    for i in range(np_):
        pp = pp + np.asarray(rp_list[i], dtype=np.float64)
    pp = pp / float(np.sum(pp))
    F = np.zeros((np_, 1), dtype=np.float64)
    for i in range(np_):
        Fi, _ = spm_MDP_log_evidence(qp, pp, rp_list[i])
        F[i, 0] = float(np.sum(np.asarray(Fi, dtype=np.float64)))
    return np.asarray(spm_softmax(-F), dtype=np.float64)


__all__ = ["spm_MDP_BMR"]
