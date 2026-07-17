#!/usr/bin/env python3
"""OPTIM1 Iteration 1 — capture real Atari boundary slices for high-risk oracle tests.

Writes small pickles under ``tests/oracle/toolbox/DEM/_checkpoint_data/optim1_entry89/``
for merge/basin regression (not full ``n_outer=128`` dumps).

Usage (repo root)::

    python tests/demo1/optim1/optim1_capture_entry89_regression.py
"""
from __future__ import annotations

import argparse
import copy
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir
from tests.demo1.optim1.optim1_merge_unique_samples import collect_merge_unique_samples


def capture_dir() -> Path:
    return (
        _REPO
        / "tests"
        / "oracle"
        / "toolbox"
        / "DEM"
        / "_checkpoint_data"
        / "optim1_entry89"
    )


def _load_boundary(pre9: Path) -> dict[str, Any]:
    with pre9.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {pre9}")
    return blob


def _o_seg_for_outer_inner(
    pdp_o: list,
    ne: int,
    nt: int,
    outer_i: int,
    inner_s: int,
) -> list:
    ng = len(pdp_o)
    offset = int(np.remainder(outer_i, 100 - 1)) * nt
    t = np.arange(0, nt + ne + 1, dtype=np.int64) + int(offset)
    cols = (t + int(inner_s)).astype(np.int64).tolist()
    return [[pdp_o[g][int(c) - 1] for c in cols] for g in range(ng)]


def build_capture_payload(boundary: dict[str, Any]) -> dict[str, Any]:
    from python_src.toolbox.DEM.spm_merge_structure_learning import spm_merge_structure_learning
    from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin

    ne = int(boundary["Ne"])
    nt = int(boundary.get("NT", 100))
    c_val = float(boundary["C"])
    pdp_o = boundary["pdp_o"]

    o_seg_1_1 = _o_seg_for_outer_inner(pdp_o, ne, nt, outer_i=1, inner_s=1)
    mdp_pre_merge = copy.deepcopy(boundary["mdp"])
    mdp_post_one_merge = spm_merge_structure_learning(copy.deepcopy(o_seg_1_1), copy.deepcopy(mdp_pre_merge))

    o_seg_2_1 = _o_seg_for_outer_inner(pdp_o, ne, nt, outer_i=2, inner_s=1)
    mdp_pre_merge_o2 = copy.deepcopy(mdp_post_one_merge)
    mdp_post_merge_o2 = spm_merge_structure_learning(
        copy.deepcopy(o_seg_2_1), copy.deepcopy(mdp_pre_merge_o2)
    )

    mdp_pre_basin = copy.deepcopy(mdp_post_merge_o2)
    mdp_post_basin, d, o, h, c = spm_RDP_basin(
        copy.deepcopy(mdp_pre_basin), [2, 3], [c_val, -c_val]
    )

    return {
        "source_pre9_pkl": None,
        "Ne": ne,
        "NT": nt,
        "C": c_val,
        "unique_sample_count": 5,
        "cases": {
            "merge_outer1_inner1": {
                "O": o_seg_1_1,
                "MDP_in": mdp_pre_merge,
                "MDP_out_ref": mdp_post_one_merge,
                "unique_samples": collect_merge_unique_samples(
                    o_seg_1_1, mdp_pre_merge, max_samples=5
                ),
            },
            "merge_outer2_inner1": {
                "O": o_seg_2_1,
                "MDP_in": mdp_pre_merge_o2,
                "MDP_out_ref": mdp_post_merge_o2,
                "unique_samples": collect_merge_unique_samples(
                    o_seg_2_1, mdp_pre_merge_o2, max_samples=5
                ),
            },
            "basin_after_two_merges": {
                "MDP_in": mdp_pre_basin,
                "MDP_out_ref": mdp_post_basin,
                "d_ref": d,
                "o_ref": o,
                "h_ref": h,
                "c_ref": c,
                "S": [2, 3],
                "chi": [c_val, -c_val],
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Capture OPTIM1 Entry 8+9 regression slices")
    p.add_argument("--pre-entry9", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None, help="Override capture pickle path")
    args = p.parse_args(argv)

    pre9 = args.pre_entry9 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
    )
    if not pre9.is_file():
        print(f"[OPTIM1 capture] missing {pre9}", file=sys.stderr)
        return 2

    boundary = _load_boundary(pre9)
    payload = build_capture_payload(boundary)
    payload["source_pre9_pkl"] = str(pre9)

    out_dir = capture_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out or (out_dir / "optim1_entry89_atari_boundary_slices.pkl")
    with out.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    n_cases = len(payload["cases"])
    print(f"[OPTIM1 capture] wrote {out} ({n_cases} cases)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
