"""Oracle: sign-off manifest schema 2 (subentry mat/pkl checksums)."""

from __future__ import annotations

import pytest

from python_src.toolbox.DEM.entry12_atari_calls import (
    ENTRY12_ATARI_CALL4_TAG,
    entry12_assert_manifest_coherent,
    entry12_refresh_manifest_script3_checksums,
    entry12_signoff_artifact_paths,
    entry12_upgrade_manifest_schema2_mat_only,
)


def test_call4_manifest_schema2_coherent_if_fixtures_present() -> None:
    """When call-4 fixtures exist, upgrade mat checksums + refresh pkls → manifest passes."""
    tag = ENTRY12_ATARI_CALL4_TAG
    paths = entry12_signoff_artifact_paths(tag)
    if not paths["rdp_mat"].is_file():
        pytest.skip("call4 fixtures not on disk")
    entry12_upgrade_manifest_schema2_mat_only(tag)
    if paths["pdp_pkl"].is_file():
        entry12_refresh_manifest_script3_checksums(tag)
        entry12_assert_manifest_coherent(tag, require_script3_pkls=True)
    else:
        entry12_assert_manifest_coherent(tag, require_script3_pkls=False)
