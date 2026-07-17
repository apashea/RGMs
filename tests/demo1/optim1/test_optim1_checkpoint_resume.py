"""OPTIM1 checkpoint resume — unit tests (no long scale runs)."""

from __future__ import annotations

from tests.demo1.demo1_checkpoint_resume import phase_b_units as demo1_phase_b_units
from tests.demo1.optim1.optim1_checkpoint_resume import optim1_phase_b_units


def test_optim1_phase_b_entry89_uses_combined_scale_only() -> None:
    units = optim1_phase_b_units()
    labels = [u.label for u in units]
    assert "entry 8+9 (optim)" in labels
    assert "entry 8 (optim)" not in labels
    assert "entry 9 (optim)" not in labels
    e89 = next(u for u in units if u.label == "entry 8+9 (optim)")
    assert e89.artifact_id == "B89_optim"
    assert e89.optim_lane is True
    joined = "\n".join(e89.scripts)
    assert "optim1_run_entry89_scale.py" in joined
    assert "optim1_run_entry8_scale.py" not in joined


def test_optim1_fidelity_entry89_matches_demo1_combined_unit() -> None:
    demo = demo1_phase_b_units()
    optim = optim1_phase_b_units()
    demo89 = next(u for u in demo if u.label == "entry 8+9")
    optim89 = next(u for u in optim if u.label == "entry 8+9 (optim)")
    assert "fsl_backward_run_entry9_isolated.py" in demo89.scripts
    assert "fsl_backward_run_entry8_isolated.py" not in demo89.scripts
    assert optim89.scripts == ("optim1_run_entry89_scale.py",)


def test_optim1_phase_b_optim_entries_are_3_7_89_10() -> None:
    optim_entries = [u for u in optim1_phase_b_units() if u.optim_lane]
    assert [u.label for u in optim_entries] == [
        "entry 3 (optim)",
        "entry 7 (optim)",
        "entry 8+9 (optim)",
        "entry 10 (optim)",
    ]
