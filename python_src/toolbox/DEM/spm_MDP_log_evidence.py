"""
Bayesian model reduction log-evidence for Dirichlet hyperparameters.

Pass 1 transliteration of ``spm_MDP_log_evidence.m`` (SPM toolbox).
"""

from __future__ import annotations

import numpy as np

from python_src.spm_betaln import spm_betaln


def spm_MDP_log_evidence(qA, pA, rA):
    """
    FORMAT F, sA = spm_MDP_log_evidence(qA, pA, rA)

    Returns free energy ``F`` and reduced sufficient statistics ``sA`` (nargout < 3).
    """
    p = 1.0 / 32.0
    rA = np.asarray(rA, dtype=np.float64) + p
    pA = np.asarray(pA, dtype=np.float64) + p
    qA = np.asarray(qA, dtype=np.float64) + p
    sA = qA + rA - pA
    F = np.asarray(spm_betaln(qA) + spm_betaln(rA) - spm_betaln(pA) - spm_betaln(sA), dtype=np.float64)
    sA = np.maximum(sA - p, 0.0)
    return F, sA


__all__ = ["spm_MDP_log_evidence"]
