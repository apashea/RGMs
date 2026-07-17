#!/usr/bin/env python3
"""W2 ledger-segment smoke — optim via Model B buffer slice vs frozen MATLAB PDP.

Validates that ``spm_mdp_vb_xxx_with_ledger_segment_reuse`` with
``--vb-dev-optim`` / ``RGMS_OPTIM1FULL_VB_DEV_OPTIM=1`` replays the correct
ledger segment through optim-owned RNG and matches frozen MATLAB authority
(aligned compare — not fidelity-vs-optim scaffolding).

Default tag: ``rgms_atari_optim1full_nr_g01`` (fast NR game-1 class).

Usage::

    python tests/demo1/optim1full/optim1full_vb_dev_adoption_smoke.py
    python tests/demo1/optim1full/optim1full_vb_dev_adoption_smoke.py --tag rgms_atari_optim1full_call4
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_NR_G01_TAG,
        optim1full_entry12_signoff_artifact_paths,
    )
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        configure_vb_dev_optim,
        optim1full_vb_dispatch_status,
    )
    from tests.demo1.optim1full.optim1full_vb_tag_lane import (
        configure_entry12_fixture_env,
        load_tag_rdp_and_buf,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        spm_mdp_vb_xxx_with_ledger_segment_reuse,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _densify_sparse_leaves,
        _load_matlab_pdp,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", default=ENTRY12_OPTIM1FULL_NR_G01_TAG)
    p.add_argument("--deadline-minutes", default="120")
    args = p.parse_args(argv)

    tag = str(args.tag).strip()
    configure_entry12_fixture_env(tag)
    rdp, buf, k = load_tag_rdp_and_buf(tag)
    paths = optim1full_entry12_signoff_artifact_paths(tag)
    mat_path = paths["pdp_mat"]
    if not mat_path.is_file():
        raise FileNotFoundError(f"MATLAB PDP authority missing for tag {tag!r}: {mat_path}")

    configure_vb_dev_optim(True)
    status = optim1full_vb_dispatch_status()
    if status["vb_lane_dispatch_resolves_to"] != "optim":
        raise RuntimeError(f"dispatch did not resolve to optim: {status}")

    t0 = time.perf_counter()
    pdp_optim = spm_mdp_vb_xxx_with_ledger_segment_reuse(
        copy.deepcopy(rdp),
        buf,
        start=0,
        k=k,
        vb_lane="dispatch",
    )
    optim_s = time.perf_counter() - t0

    pdp_matlab = _load_matlab_pdp(mat_path)
    label = f"W2 ledger-segment optim vs MATLAB ({tag})"
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

    print(
        f"[optim1full_vb_dev_adoption_smoke] PASS tag={tag!r} "
        f"optim_s={optim_s:.3f} dispatch={status} matlab={mat_path.name}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
