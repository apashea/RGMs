#!/usr/bin/env python3
"""FSL backward — run Entry 5 only on MATLAB-fed boundary (no ``entry_stop=5``).

Loads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry5.pkl``.
Writes ``fixtures/DEMAtariIII_fsl_backward_entry5_post.pkl``.

Compare with ``fsl_backward_compare_entry5_pkl_to_mat.py``.
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


def _pre5_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_MDP_PRE5_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry5.pkl"


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY5_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry5_post.pkl"


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry5 import run_entry5_from_boundary

    pre = _pre5_pkl()
    if not pre.is_file():
        print(
            f"[FSL backward Entry 5 isolated] missing {pre}\n"
            "Run: patch_mdp_pre_entry5_to_pre_entry10_mat.m, then "
            "python fsl_backward_materialize_mdp_pre_entry5_pkl.py",
            file=sys.stderr,
        )
        return 2

    with pre.open("rb") as f:
        boundary = pickle.load(f)
    print(f"[FSL backward Entry 5 isolated] input {pre}", file=sys.stderr)
    print(
        f"[FSL backward Entry 5 isolated] Nm={boundary.get('Nm')} Ne={boundary.get('Ne')}",
        file=sys.stderr,
    )
    out_payload = run_entry5_from_boundary(boundary)
    print(
        f"[FSL backward Entry 5 isolated] Nm={out_payload.get('Nm')} Ne={out_payload.get('Ne')}",
        file=sys.stderr,
    )
    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "C": float(boundary.get("C", 32.0)),
                "source_pre5_pkl": str(pre),
                "validation": {
                    "lane": "fsl_backward_entry5",
                    "authority_var": "MDP_pre_entry7",
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 5 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
