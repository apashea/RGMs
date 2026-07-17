#!/usr/bin/env python3
"""Report BLAS/LAPACK toolchain visible to Python (``eig.md`` §29). Read-only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    out: dict = {"numpy_version": None, "scipy_version": None, "blas": {}, "lapack_routines": {}}
    try:
        import numpy as np_mod

        out["numpy_version"] = np_mod.__version__
        try:
            import yaml  # noqa: F401

            out["numpy_config"] = np_mod.show_config()
        except Exception:
            out["numpy_config"] = "unavailable (install pyyaml for full config)"
    except ImportError as e:
        out["numpy_error"] = str(e)

    try:
        import scipy

        out["scipy_version"] = scipy.__version__
        from scipy.linalg import lapack

        probe = np.zeros((2, 2), dtype=np.float64, order="F")
        for name in ("geev", "geevx", "gges"):
            try:
                lapack.get_lapack_funcs(name, (probe,))
                out["lapack_routines"][name] = True
            except (ValueError, TypeError, AttributeError):
                out["lapack_routines"][name] = False
    except ImportError as e:
        out["scipy_error"] = str(e)

    try:
        from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available

        out["vendored_dgeevx_built"] = lapack_nobalance_available()
    except ImportError:
        out["vendored_dgeevx_built"] = False

    text = json.dumps(out, indent=2, default=str)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
