#!/usr/bin/env python3
"""FSL backward — run Entry 7 only on MATLAB-fed boundary (no ``entry_stop=7``).

Loads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl``.
Writes ``fixtures/DEMAtariIII_fsl_backward_entry7_post.pkl``.

Compare with ``fsl_backward_compare_entry7_pkl_to_mat.py``.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _pre7_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_MDP_PRE7_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl"


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY7_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry7_post.pkl"


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry7 import run_entry7_from_boundary

    pre = _pre7_pkl()
    if not pre.is_file():
        print(
            f"[FSL backward Entry 7 isolated] missing {pre}\n"
            "Run: matlab dump_MDP_pre_entry10.m, then "
            "python fsl_backward_materialize_mdp_pre_entry7_pkl.py",
            file=sys.stderr,
        )
        return 2

    with pre.open("rb") as f:
        boundary = pickle.load(f)
    print(f"[FSL backward Entry 7 isolated] input {pre}", file=sys.stderr)
    print(
        f"[FSL backward Entry 7 isolated] Ne={boundary.get('Ne')} "
        f"PDP_O_cols={boundary.get('PDP_O_cols')}",
        file=sys.stderr,
    )
    out_payload = run_entry7_from_boundary(boundary)
    print(
        f"[FSL backward Entry 7 isolated] n_windows={out_payload.get('n_windows')}",
        file=sys.stderr,
    )
    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "C": float(boundary.get("C", 32.0)),
                "source_pre7_pkl": str(pre),
                "validation": {
                    "lane": "fsl_backward_entry7",
                    "authority_var": "MDP_pre_entry9",
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 7 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
