"""Policy unit tests for OPTIM1FULL plot-parity dump-once + fingerprints (no VB/Engine)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.demo1.optim1full.optim1full_plot_parity import decide_plot_parity_heavy_steps
from tests.demo1.optim1full.optim1full_plot_parity_fingerprints import (
    SCHEMA_ORACLE,
    SCHEMA_SPINE_PKL,
    file_stamp,
    oracle_mat_meta_ok,
    spine_pkl_meta_ok,
    write_oracle_mat_meta,
    write_spine_pkl_meta,
)


@pytest.mark.parametrize(
    "pkl_exists,oracle_exists,force_export,force_refresh,pkl_meta_ok,oracle_meta_ok,"
    "expect_export,expect_refresh",
    [
        (True, True, False, False, True, True, False, False),
        (False, True, False, False, True, True, True, False),
        (True, False, False, False, True, True, False, True),
        (True, True, False, False, False, True, True, False),
        (True, True, False, False, True, False, False, True),
        (True, True, True, False, True, True, True, False),
        (True, True, False, True, True, True, False, True),
        (False, False, False, False, False, False, True, True),
    ],
)
def test_decide_plot_parity_heavy_steps(
    pkl_exists: bool,
    oracle_exists: bool,
    force_export: bool,
    force_refresh: bool,
    pkl_meta_ok: bool,
    oracle_meta_ok: bool,
    expect_export: bool,
    expect_refresh: bool,
) -> None:
    do_export, do_refresh = decide_plot_parity_heavy_steps(
        pkl_exists=pkl_exists,
        oracle_exists=oracle_exists,
        force_export=force_export,
        force_refresh_oracle=force_refresh,
        pkl_meta_ok=pkl_meta_ok,
        oracle_meta_ok=oracle_meta_ok,
    )
    assert do_export is expect_export
    assert do_refresh is expect_refresh


def test_spine_and_oracle_meta_roundtrip(tmp_path: Path) -> None:
    # Fake "VB modules" as empty stubs under a mini repo tree.
    repo = tmp_path / "repo"
    fidelity = repo / "python_src/toolbox/DEM/spm_MDP_VB_XXX.py"
    fidelity.parent.mkdir(parents=True)
    fidelity.write_text("# stub\n", encoding="utf-8")

    auth = tmp_path / "matlab_pdp.mat"
    auth.write_bytes(b"AUTH")
    pkl = tmp_path / "site_input.pkl"
    pkl.write_bytes(b"PKL")
    oracle = tmp_path / "site_oracle.mat"
    oracle.write_bytes(b"ORCL")

    write_spine_pkl_meta(
        pkl,
        site_id="dem_with_compression_rgb",
        boundary="vb_call4",
        matlab_pdp_mat=auth,
        ledger_protocol="test",
        vb_dev_optim=False,
        repo=repo,
    )
    write_oracle_mat_meta(
        oracle,
        site_id="dem_with_compression_rgb",
        matlab_pdp_mat=auth,
        oracle_source="capture_optim1full_plot_fence",
        repo=repo,
    )

    assert spine_pkl_meta_ok(pkl, auth, vb_dev_optim=False, repo=repo)
    assert oracle_mat_meta_ok(oracle, auth, repo=repo)

    # Missing sidecar ⇒ invalid.
    pkl2 = tmp_path / "other.pkl"
    pkl2.write_bytes(b"X")
    assert not spine_pkl_meta_ok(pkl2, auth, vb_dev_optim=False, repo=repo)

    # Authority mtime/size change ⇒ invalid.
    auth.write_bytes(b"AUTH!")
    assert not spine_pkl_meta_ok(pkl, auth, vb_dev_optim=False, repo=repo)
    assert not oracle_mat_meta_ok(oracle, auth, repo=repo)


def test_file_stamp_and_schema_constants() -> None:
    assert SCHEMA_SPINE_PKL.startswith("optim1full_spine_pkl_")
    assert SCHEMA_ORACLE.startswith("optim1full_oracle_")
    # Touch ensure helper is importable / callable with real tempfile via fixture site above.
    assert callable(file_stamp)
