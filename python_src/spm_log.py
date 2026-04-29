"""Log of numeric array with MATLAB `spm_log` semantics.

MATLAB (`spm_log.m`, Pass 1 target):

- `islogical(A)` → `A = -32*(~A);`
- else → `A = max(log(A), -32);`

Python mirrors that structure after `as_matlab_array` (including raw 1-D
numeric → row vector). For float inputs, `np.log` follows IEEE-754; the
nearest representable to MATLAB's `log` can differ by a few ULPs depending on
platform libm. Oracle tests compare against the MATLAB Engine reference; see
`notes/andrew Python Matlab Translation Issues.md` (`spm_log` section).

For non-logical arrays, MATLAB `max` with `log(NaN)` still yields `-32`
(e.g. `max(log(NaN), -32) == -32`); Python uses `np.fmax` (not `np.maximum`) so
`spm_log` matches that behavior.
"""
import os

import numpy as np

from matlab_compat import as_matlab_array


def spm_log(A):
    A = as_matlab_array(A)
    mode = str(os.getenv("RGMS_SPM_LOG_EXPERIMENT_KERNEL", "")).strip().lower()

    if np.issubdtype(A.dtype, np.bool_):
        A = -32.0 * (~A)
    else:
        # MATLAB `max(u, v)` follows IEEE-like `fmax` for NaNs: e.g. `max(NaN, -32) == -32`.
        # NumPy `maximum` propagates NaNs from `log(NaN)`; `fmax` matches MATLAB here.
        if mode in ("", "default", "natural", "ln", "off", "0", "false", "no"):
            A = np.fmax(np.log(A), -32.0)
        elif mode in ("log2_ln2", "log2"):
            # Experimental kernel for Bottleneck #1 sweeps only (not MATLAB-faithful).
            A = np.fmax(np.log2(A) * np.log(2.0), -32.0)
        else:
            raise ValueError(f"unknown RGMS_SPM_LOG_EXPERIMENT_KERNEL mode: {mode!r}")

    return A
