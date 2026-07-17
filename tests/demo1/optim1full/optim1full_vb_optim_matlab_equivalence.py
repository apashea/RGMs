#!/usr/bin/env python3
"""OPTIM1FULL W2 — optim vs frozen MATLAB PDP on Entry 12 VB fixtures.

Sign-off authority for ``--vb-optim-tier3*`` / ``--vb-optim-nr-g01`` gates.
Runs only ``spm_MDP_VB_XXX_optim``; compares against frozen MATLAB ``pdp_mat``
from ``optim1full_entry12_signoff_artifact_paths(tag)`` with MATLAB-layout
alignment (``entry12_align_mdp_to_mat_workspace``,
``entry12_mat_pdp_for_value_assert``).

Does **not** compare optim to fidelity Python. Fidelity-vs-optim is a
historical diagnostic only (``optim1full_vb_optim_equivalence.py``).

Default tag: ``rgms_atari_optim1full_call4`` (tier 3f).
"""
from __future__ import annotations

import argparse
import copy
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

OUT_DIR = _REPO / "logs"


def _optim_pkl_path(tag: str) -> Path:
    return OUT_DIR / f"optim1full_w2_{tag}_optim_pdp.pkl"


def run_vb_optim_matlab_equivalence(
    tag: str,
    *,
    deadline_minutes: str = "120",
) -> dict[str, Any]:
    """Run optim VB once; assert PDP matches frozen MATLAB authority."""
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        optim1full_entry12_signoff_artifact_paths,
    )
    from tests.demo1.optim1full.optim1full_vb_tag_lane import (
        configure_entry12_fixture_env,
        load_tag_rdp_and_buf,
        run_vb_tag_lane,
    )
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _densify_sparse_leaves,
        _load_matlab_pdp,
    )

    os.environ.setdefault("RGMS_ATARI_RUN_DEADLINE_MINUTES", str(deadline_minutes))
    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")

    configure_entry12_fixture_env(tag)
    assert_entry12_vb_tag_ready(tag)
    paths = optim1full_entry12_signoff_artifact_paths(tag)
    mat_path = paths["pdp_mat"]
    if not mat_path.is_file():
        raise FileNotFoundError(f"MATLAB PDP authority missing for tag {tag!r}: {mat_path}")

    rdp, _buf, k = load_tag_rdp_and_buf(tag)
    print(
        f"[optim1full_vb_optim_matlab_equivalence] tag={tag!r} vb_rand_buf.k={k} "
        f"matlab={mat_path.name}",
        file=sys.stderr,
        flush=True,
    )

    t0 = time.perf_counter()
    pdp_optim = run_vb_tag_lane(rdp, lane="optim")
    optim_vb_s = time.perf_counter() - t0

    pdp_matlab = _load_matlab_pdp(mat_path)
    label = f"W2 optim vs MATLAB ({tag})"

    if isinstance(pdp_optim, dict) and isinstance(pdp_matlab, dict):
        py_cmp = entry12_align_mdp_to_mat_workspace(copy.deepcopy(pdp_optim), pdp_matlab)
        mat_cmp = entry12_mat_pdp_for_value_assert(pdp_matlab)
    else:
        py_cmp, mat_cmp = pdp_optim, pdp_matlab

    _compare_pair(
        label,
        _densify_sparse_leaves(copy.deepcopy(py_cmp)),
        _densify_sparse_leaves(copy.deepcopy(mat_cmp)),
        "PDP",
        report_only=False,
        coerce_sparse=False,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pkl_out = _optim_pkl_path(tag)
    payload = {
        "tag": tag,
        "k": k,
        "optim_vb_s": optim_vb_s,
        "matlab_pdp_mat": str(mat_path),
        "PDP": pdp_optim,
    }
    with open(pkl_out, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    wall = time.perf_counter() - t0
    out = {
        "tag": tag,
        "k": k,
        "optim_vb_s": optim_vb_s,
        "wall_s": wall,
        "pkl": str(pkl_out),
    }
    print(
        f"[optim1full_vb_optim_matlab_equivalence] PASS tag={tag!r} "
        f"optim_vb_s={optim_vb_s:.3f} wall_s={wall:.3f} pkl={pkl_out.name}",
        file=sys.stderr,
        flush=True,
    )
    return out


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL4_TAG,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--tag",
        default=ENTRY12_OPTIM1FULL_CALL4_TAG,
        help="Entry 12 VB tag (default: tier 3f call4)",
    )
    p.add_argument("--deadline-minutes", default="120")
    args = p.parse_args(argv)

    try:
        run_vb_optim_matlab_equivalence(
            str(args.tag).strip(),
            deadline_minutes=str(args.deadline_minutes),
        )
    except Exception as exc:
        print(
            f"[optim1full_vb_optim_matlab_equivalence] FAIL: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
