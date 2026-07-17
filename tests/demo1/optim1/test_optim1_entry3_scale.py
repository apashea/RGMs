"""OPTIM1 Entry 3 scale gate — ``T=10000`` vs DEMO1 authority (slow)."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_src.optimized.toolbox.DEM.fsl_backward_entry3_optim import (
    compare_entry3_optim_pdp_to_demo1_authority,
    run_entry3_optim_from_entry2_post_pkl,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir


def _demo1_entry3_fixtures_present() -> bool:
    d = demo1_fixtures_dir()
    need = (
        "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat",
        "DEMAtariIII_fsl_backward_entry2_post.pkl",
        "dem_atari_rand_buf_through_entry11.mat",
        "fsl_backward_entry3_K_py.mat",
    )
    return all((d / name).is_file() for name in need)


@pytest.mark.slow
@pytest.mark.skipif(
    not _demo1_entry3_fixtures_present(),
    reason="DEMO1 Entry 3 fixtures missing — run DEM_AtariIII_demo1_parity.py first",
)
def test_optim1_entry3_scale_matches_demo1_authority():
    """``spm_MDP_generate_optim`` at ``T=10000`` ≡ DEMO1 ``PDP_o`` / ``PDP_O(:,1:1000)``."""
    out = run_entry3_optim_from_entry2_post_pkl(deadline_minutes="90")
    compare_entry3_optim_pdp_to_demo1_authority(
        out["pdp"],
        authority_mat=Path(
            demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
        ),
    )
