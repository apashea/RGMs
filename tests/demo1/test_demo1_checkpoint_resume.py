"""DEMO1 checkpoint resume — unit tests (no long parity runs)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.demo1.demo1_checkpoint_resume import (
    checkpoint_present,
    entry_gate_checkpoint_present,
    phase_b_scripts_in_order,
    phase_b_units,
    phase_c_skip_script3,
    phase_c_skip_script4,
    phase_d_skip,
    plan_phase_b,
)
from tests.demo1.demo1_parity_phases import _PHASE_B_SCRIPTS


def test_phase_b_script_list_matches_orchestrator() -> None:
    assert phase_b_scripts_in_order() == _PHASE_B_SCRIPTS


def test_phase_b_entry89_unit_uses_combined_loop_only() -> None:
    units = phase_b_units()
    labels = [u.label for u in units]
    assert "entry 8+9" in labels
    assert "entry 8" not in labels
    assert "entry 9" not in labels
    e89 = next(u for u in units if u.label == "entry 8+9")
    assert e89.artifact_id == "B89_post"
    joined = "\n".join(e89.scripts)
    assert "fsl_backward_run_entry8_isolated.py" not in joined
    assert "fsl_backward_compare_entry8_pkl_to_mat.py" not in joined
    assert "fsl_backward_run_entry9_isolated.py" in joined
    assert "fsl_backward_compare_entry9_pkl_to_mat.py" in joined


def test_registry_has_48_blocking_artifacts() -> None:
    from tests.demo1.fixture_registry import all_artifacts

    assert len(all_artifacts()) == 48


def test_plan_phase_b_skips_entry_when_post_pkl_exists(tmp_path: Path) -> None:
    fix = tmp_path / "fixtures"
    fix.mkdir()
    (fix / "DEMAtariIII_fsl_backward_entry1_post.pkl").write_bytes(b"pkl")
    plan = plan_phase_b(fix)
    assert plan[0][0].label == "entry 1"
    assert plan[0][1] is True
    assert plan[1][1] is False


def test_gate_checkpoint_requires_gate_pdp_not_empty_dir(tmp_path: Path) -> None:
    fix = tmp_path / "fixtures"
    gate = fix / "fsl_backward_entry11_entry12_vb"
    gate.mkdir(parents=True)
    assert entry_gate_checkpoint_present(fix) is False
    assert checkpoint_present("B11_gate", fix) is False
    (gate / "DEMAtariIII_fsl_backward_entry11_entry12_pdp.pkl").write_bytes(b"pkl")
    assert entry_gate_checkpoint_present(fix) is True
    assert checkpoint_present("B11_gate", fix) is True


def test_phase_c_skip_flags(tmp_path: Path) -> None:
    fix = tmp_path / "fixtures"
    fix.mkdir()
    assert phase_c_skip_script3(fix) is False
    (fix / "DEMAtariIII_XXX_12_pdp.pkl").write_bytes(b"pkl")
    assert phase_c_skip_script3(fix) is True


def test_phase_c_skip_script4_uses_repo_output_txt(tmp_path: Path) -> None:
    from tests.demo1.demo1_paths import demo1_repo_root

    out = demo1_repo_root() / "matlab_custom" / "XXX_12_compare_pdp_pkl_to_mat_output.txt"
    if not out.is_file():
        pytest.skip("Validation 12 output tee not present in this clone")
    assert phase_c_skip_script4(tmp_path / "fixtures") is True


def test_phase_d_skip_when_shipped_png_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.demo1 import demo1_paths

    png = tmp_path / "DEMO1_matlab_python_parity_12plot.png"
    png.write_bytes(b"png")
    monkeypatch.setattr(demo1_paths, "demo1_shipped_parity_png", lambda: png)
    assert phase_d_skip(tmp_path) is True
