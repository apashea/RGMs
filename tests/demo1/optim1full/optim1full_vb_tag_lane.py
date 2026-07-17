"""OPTIM1FULL W2 — shared Entry 12 tag VB lane helpers.

Used by W2 sign-off (``optim1full_vb_optim_matlab_equivalence``), profiling,
and historical diagnostic (``optim1full_vb_optim_equivalence``). Not historical
itself — neutral helper surface for frozen-tag VB runs.
"""
from __future__ import annotations

import copy
import os
from typing import Any

from tests.demo1.optim1full.optim1full_vb_dispatch import (
    spm_mdp_vb_xxx_callable,
    spm_mdp_vb_xxx_timing_module,
)


def configure_entry12_fixture_env(tag: str) -> None:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fix = str(optim1full_fixtures_dir().resolve())
    os.environ["RGMS_OPTIM1FULL_FIXTURES_DIR"] = fix
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = fix
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = str(tag).strip()


def load_tag_rdp_and_buf(tag: str) -> tuple[dict[str, Any], Any, int]:
    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_load_vb_rand_buf_for_tag,
        load_entry12_rdp_for_tag,
    )
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready

    assert_entry12_vb_tag_ready(tag)
    rdp = load_entry12_rdp_for_tag(tag)
    buf = entry12_load_vb_rand_buf_for_tag(tag)
    k = int(buf.size)
    if k < 1:
        raise RuntimeError(f"tag {tag!r}: empty vb_rand_buf")
    return rdp, buf, k


def run_vb_tag_lane(rdp: dict[str, Any], *, lane: str) -> Any:
    """Script **3**-style VB on frozen Entry **12** tag fixtures."""
    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_assert_buf_k_coherent,
        entry12_resolve_run_tag,
        entry12_vb_oracle_flags,
    )

    tag = entry12_resolve_run_tag()
    entry12_assert_buf_k_coherent(tag)
    vb_fn = spm_mdp_vb_xxx_callable(lane)  # type: ignore[arg-type]
    _spm_vb_mod = spm_mdp_vb_xxx_timing_module(lane)  # type: ignore[arg-type]
    _spm_vb_mod._VB_TIMING_DEPTH = 0
    flags = entry12_vb_oracle_flags(reuse_matlab_draws=True)
    flags["dump_subentries"] = False
    return vb_fn(rdp, {}, **flags)


def assert_pdp_equal(ref_pdp: Any, test_pdp: Any, *, label: str) -> None:
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _densify_sparse_leaves,
    )

    _compare_pair(
        label,
        _densify_sparse_leaves(copy.deepcopy(test_pdp)),
        _densify_sparse_leaves(copy.deepcopy(ref_pdp)),
        "PDP",
        report_only=False,
        coerce_sparse=False,
    )


# Back-compat private aliases for modules not yet migrated.
_configure_entry12_fixture_env = configure_entry12_fixture_env
_load_tag_rdp_and_buf = load_tag_rdp_and_buf
_run_vb_tag_lane = run_vb_tag_lane
_assert_pdp_equal = assert_pdp_equal
_load_tier3a_rdp_and_buf = load_tag_rdp_and_buf
