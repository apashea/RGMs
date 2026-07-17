#!/usr/bin/env python3
"""FSL backward — run Entry 6 only on MATLAB-fed boundary (no ``entry_stop=6``).

Loads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry6.pkl``.
Writes ``fixtures/DEMAtariIII_fsl_backward_entry6_post.pkl``.

Compare with ``fsl_backward_compare_entry6_pkl_to_mat.py``.
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


def _pre6_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_MDP_PRE6_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry6.pkl"


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY6_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry6_post.pkl"


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry6 import run_entry6_from_boundary

    pre = _pre6_pkl()
    if not pre.is_file():
        print(
            f"[FSL backward Entry 6 isolated] missing {pre}\n"
            "Run: matlab dump_MDP_pre_entry10.m (or patch_entry6_authority), then "
            "python fsl_backward_materialize_mdp_pre_entry6_pkl.py",
            file=sys.stderr,
        )
        return 2

    with pre.open("rb") as f:
        boundary = pickle.load(f)
    print(f"[FSL backward Entry 6 isolated] input {pre}", file=sys.stderr)
    print(
        f"[FSL backward Entry 6 isolated] Ne={boundary.get('Ne')} "
        f"pdp_o_obs shape={getattr(boundary.get('pdp_o_obs'), 'shape', None)}",
        file=sys.stderr,
    )
    out_payload = run_entry6_from_boundary(boundary)
    print(
        f"[FSL backward Entry 6 isolated] n_windows={out_payload.get('n_windows')} "
        f"numel(r)={out_payload['r'].size} numel(c)={out_payload['c'].size}",
        file=sys.stderr,
    )
    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "C": float(boundary.get("C", 32.0)),
                "source_pre6_pkl": str(pre),
                "validation": {
                    "lane": "fsl_backward_entry6",
                    "authority_var": "entry6_r, entry6_c, entry6_t_windows",
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 6 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
