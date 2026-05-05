"""
Cumulative distribution function of the Gamma distribution.

Pass 1 transliteration of ``spm_Gcdf.m`` (SPM). MATLAB uses ``gammainc(l.*x, h, tail)``.
"""

from __future__ import annotations

import numpy as np
from scipy.special import gammainc, gammaincc

from matlab_compat import matlab_scalar


def spm_Gcdf(x, h, l, tail: str = "lower"):
    """
    FORMAT ``F = spm_Gcdf(x, h, l, tail)``

    ``tail``: ``'lower'`` (default) or ``'upper'``.
    """
    tail_l = str(tail).lower()
    if tail_l not in ("lower", "upper"):
        raise ValueError("tail must be 'lower' or 'upper'")

    x = np.asarray(x, dtype=np.float64)
    h = np.asarray(h, dtype=np.float64)
    l = np.asarray(l, dtype=np.float64)
    z = l * x

    if tail_l == "lower":
        out = gammainc(h, z)
    else:
        out = gammaincc(h, z)

    out = np.asarray(out, dtype=np.float64)
    return matlab_scalar(out) if out.ndim == 0 else out
