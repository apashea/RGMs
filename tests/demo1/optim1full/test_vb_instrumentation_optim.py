"""Contracts for optimized VB diagnostics versus native execution."""
from __future__ import annotations

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as inst


def test_capture_probe_defaults_off_and_dump_enables(monkeypatch) -> None:
    monkeypatch.delenv("RGMS_ENTRY12_CAPTURE_Y_PROBE", raising=False)
    monkeypatch.setattr(inst, "_VB_DUMP_SPEC", None)
    assert inst._vb_capture_y_probe_active() is False

    monkeypatch.setattr(inst, "_VB_DUMP_SPEC", {"enabled": True})
    assert inst._vb_capture_y_probe_active() is True


def test_capture_probe_env_override_wins_over_dump(monkeypatch) -> None:
    monkeypatch.setattr(inst, "_VB_DUMP_SPEC", {"enabled": True})
    monkeypatch.setenv("RGMS_ENTRY12_CAPTURE_Y_PROBE", "0")
    assert inst._vb_capture_y_probe_active() is False

    monkeypatch.setenv("RGMS_ENTRY12_CAPTURE_Y_PROBE", "1")
    assert inst._vb_capture_y_probe_active() is True


def test_inactive_probe_does_not_attach_stale_vbx_record(monkeypatch) -> None:
    monkeypatch.delenv("RGMS_ENTRY12_CAPTURE_Y_PROBE", raising=False)
    monkeypatch.setattr(inst, "_VB_DUMP_SPEC", None)
    monkeypatch.setattr(inst, "_ENTRY12_VBX_ACC", {"m1t1": {"F_vbx": 1.0}})
    models = [{}]

    inst._entry12_attach_vbx_to_model(models, 0, 1)

    assert "entry12_VBX" not in models[0]
