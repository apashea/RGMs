"""Entry 12 handoff-capture artifact (subentries 12A–12I).

**Authoritative:** ``matlab_subentries[<code>]`` — MATLAB Engine outputs at each subentry
boundary (same DEM lane / ``rgms_rdp11`` preamble as ``spm_MDP_VB_XXX`` capture). Built once;
reload the pickle for tests — compare **Python translation vs these MATLAB blobs**, never
Python vs earlier Python.

**12A** stores MATLAB ``spm_MDP_checkX(rgms_rdp11)`` after the same ``E`` repair used before
the first VB call in ``test_DEM_AtariIII_entry12.py``. **12B–12I:** MATLAB checkpoints are
``None`` until extended in this builder (same pattern as 12A).

**Non-authoritative:** ``legacy_python_handoffs`` — optional Python-run snapshots for debugging
only; **do not** use as parity truth.

Training/outer: :mod:`python_src.toolbox.DEM.DEM_AtariIII` via :func:`entry12_handoff_capture_driver_params`.
"""

from __future__ import annotations

import copy
import os
import pickle
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vbxxx
from python_src.toolbox.DEM.DEM_AtariIII import _entry8_outer_loop_count, _training_horizon
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM import test_DEM_AtariIII_entry10 as _matlab_dem_lane_oracle
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    _capture_entry10_sort_artifact,
    _pull_nested_rdp_from_matlab,
)
ENTRY12_HANDOFF_CAPTURE_V = 6

_MATLAB_E_REPAIR_BEFORE_VB = (
    "rgms_entry12_e_repaired = 0; "
    "for rgms_m = 1:numel(rgms_rdp11), "
    "if ~isfield(rgms_rdp11(rgms_m),'E') || isempty(rgms_rdp11(rgms_m).E), "
    "rgms_rdp11(rgms_m).E = cell(1,numel(rgms_rdp11(rgms_m).B)); "
    "end; "
    "for rgms_f = 1:numel(rgms_rdp11(rgms_m).B), "
    "rgms_nu = size(rgms_rdp11(rgms_m).B{rgms_f},3); "
    "if rgms_nu < 1, rgms_nu = 1; end; "
    "if numel(rgms_rdp11(rgms_m).E) < rgms_f || isempty(rgms_rdp11(rgms_m).E{rgms_f}), "
    "rgms_rdp11(rgms_m).E{rgms_f} = ones(rgms_nu,1)/rgms_nu; "
    "rgms_entry12_e_repaired = rgms_entry12_e_repaired + 1; "
    "end; "
    "end; "
    "end; "
)


def entry12_handoff_capture_refresh_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_ENTRY12_HANDOFF_CAPTURE_REFRESH", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def entry12_handoff_capture_tag() -> str:
    raw = str(os.getenv("RGMS_ATARI_ENTRY12_HANDOFF_CAPTURE_TAG", "default")).strip()
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw)
    return safe or "default"


def entry12_handoff_capture_driver_params() -> tuple[int, int]:
    """``(training_t, n_outer)`` aligned with ``DEM_AtariIII`` env-driven defaults."""
    return _training_horizon(), _entry8_outer_loop_count()


def load_matlab_rdp_at_entry12_input(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    """Nested MATLAB ``RDP`` passed into Entry 12 (``spm_MDP_VB_XXX``).

    Pulled from the MATLAB workspace after Engine-side DEM lane execution; Python only
    deep-copies the pulled dict.
    """
    artifact = _matlab_dem_lane_oracle.load_or_build_entry10_sort_artifact(
        dem_eng, training_t, n_outer
    )
    return copy.deepcopy(artifact["rdp11_nested_mat"])


def entry12_handoff_capture_path(training_t: int, n_outer: int) -> Path:
    repo = Path(__file__).resolve().parents[4]
    ckpt_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    tag = entry12_handoff_capture_tag()
    return ckpt_dir / f"dem_atari_entry12_handoff_capture_t{int(training_t)}_outer{int(n_outer)}_{tag}.pkl"


def _boundary_io(in_obj: dict[str, Any], out_obj: dict[str, Any]) -> dict[str, Any]:
    return {"in": copy.deepcopy(in_obj), "out": copy.deepcopy(out_obj)}


def _capture_python_handoffs_from_rdp_matlab(rdp11: dict[str, Any]) -> dict[str, Any]:
    handoffs: dict[str, Any] = {}

    mdp_checked = spm_MDP_checkX(copy.deepcopy(rdp11))
    handoffs["12A"] = _boundary_io(
        {"mdp_in": copy.deepcopy(rdp11)},
        {"mdp_checked": copy.deepcopy(mdp_checked)},
    )

    models = vbxxx._vb_models_after_checkx(mdp_checked)
    nm = len(models)
    hp = vbxxx._vb_hyperparameters_mdp1(models[0])
    t_h = float(models[0]["T"])
    in_12b = {
        "models": copy.deepcopy(models),
        "nm": int(nm),
        "t_h": float(t_h),
    }
    bundle = vbxxx._vb_tensors_through_H(models, nm, t_h)
    handoffs["12B"] = _boundary_io(in_12b, {"bundle": copy.deepcopy(bundle)})

    in_12c = {
        "models": copy.deepcopy(models),
        "bundle_pre_12c": copy.deepcopy(bundle),
        "hp": copy.deepcopy(hp),
    }
    post = vbxxx._vb_init_QXSP_outcomes_and_process(models, bundle, vbxxx._default_options_vb(), float(hp["chi"]))
    bundle.update(post)

    capture: dict[str, Any] = {"12D": None, "12E": None, "12F": None}
    call_trace: dict[str, int] = {
        "_vb_policy_depth_and_get_M": 0,
        "spm_forwards": 0,
        "spm_backwards": 0,
        "_spm_sample": 0,
        "_spm_action": 0,
    }
    orig_gen = vbxxx._vb_generation_paths_states_share
    orig_out = vbxxx._vb_generate_outcomes_if_options_o
    orig_bel = vbxxx._vb_belief_after_forwards
    orig_getm = vbxxx._vb_policy_depth_and_get_M
    orig_forwards = vbxxx.spm_forwards
    orig_backwards = vbxxx.spm_backwards
    orig_sample = vbxxx._spm_sample
    orig_action = vbxxx._spm_action

    def _getm_wrap(models_w: list[dict[str, Any]], bundle_w: dict[str, Any], hp_w: dict[str, Any]) -> dict[str, Any]:
        call_trace["_vb_policy_depth_and_get_M"] += 1
        return orig_getm(models_w, bundle_w, hp_w)

    def _forwards_wrap(*args: Any, **kwargs: Any) -> Any:
        call_trace["spm_forwards"] += 1
        return orig_forwards(*args, **kwargs)

    def _backwards_wrap(*args: Any, **kwargs: Any) -> Any:
        call_trace["spm_backwards"] += 1
        return orig_backwards(*args, **kwargs)

    def _sample_wrap(*args: Any, **kwargs: Any) -> Any:
        call_trace["_spm_sample"] += 1
        return orig_sample(*args, **kwargs)

    def _action_wrap(*args: Any, **kwargs: Any) -> Any:
        call_trace["_spm_action"] += 1
        return orig_action(*args, **kwargs)

    def _gen_wrap(models_w: list[dict[str, Any]], bundle_w: dict[str, Any], t_idx: int, M_row: np.ndarray) -> None:
        in_obj = {
            "models": copy.deepcopy(models_w),
            "bundle": copy.deepcopy(bundle_w),
            "t_idx": int(t_idx),
            "M_row": np.asarray(M_row, dtype=np.int64).copy(),
        }
        orig_gen(models_w, bundle_w, t_idx, M_row)
        if capture["12D"] is None:
            capture["12D"] = _boundary_io(in_obj, {"models": copy.deepcopy(models_w), "bundle": copy.deepcopy(bundle_w)})

    def _out_wrap(models_w: list[dict[str, Any]], bundle_w: dict[str, Any], t_idx: int, M_row: np.ndarray) -> None:
        in_obj = {
            "models": copy.deepcopy(models_w),
            "bundle": copy.deepcopy(bundle_w),
            "t_idx": int(t_idx),
            "M_row": np.asarray(M_row, dtype=np.int64).copy(),
        }
        orig_out(models_w, bundle_w, t_idx, M_row)
        if capture["12E"] is None:
            capture["12E"] = _boundary_io(in_obj, {"models": copy.deepcopy(models_w), "bundle": copy.deepcopy(bundle_w)})

    def _bel_wrap(mi: int, bundle_w: dict[str, Any], t_m: int, t_idx: int, G_m: Any, alpha: float) -> tuple[np.ndarray, float]:
        in_obj = {
            "models": copy.deepcopy(models),
            "bundle": copy.deepcopy(bundle_w),
            "mi": int(mi),
            "t_m": int(t_m),
            "t_idx": int(t_idx),
            "G_m": np.asarray(G_m, dtype=np.float64).copy(),
            "alpha": float(alpha),
        }
        out = orig_bel(mi, bundle_w, t_m, t_idx, G_m, alpha)
        if capture["12F"] is None:
            capture["12F"] = _boundary_io(in_obj, {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle_w)})
        return out

    with (
        patch.object(vbxxx, "_vb_policy_depth_and_get_M", side_effect=_getm_wrap),
        patch.object(vbxxx, "spm_forwards", side_effect=_forwards_wrap),
        patch.object(vbxxx, "spm_backwards", side_effect=_backwards_wrap),
        patch.object(vbxxx, "_spm_sample", side_effect=_sample_wrap),
        patch.object(vbxxx, "_spm_action", side_effect=_action_wrap),
        patch.object(vbxxx, "_vb_generation_paths_states_share", side_effect=_gen_wrap),
        patch.object(vbxxx, "_vb_generate_outcomes_if_options_o", side_effect=_out_wrap),
        patch.object(vbxxx, "_vb_belief_after_forwards", side_effect=_bel_wrap),
    ):
        bundle.update(vbxxx._vb_policy_depth_and_get_M(models, bundle, hp))
        bundle["options_vb"] = vbxxx._default_options_vb()
        handoffs["12C"] = _boundary_io(in_12c, {"bundle": copy.deepcopy(bundle)})
        vbxxx._vb_run_partial_t_loop(models, bundle, float(hp["alpha"]), recurse_partial=False)

    if capture["12D"] is None:
        capture["12D"] = _boundary_io(
            {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle), "t_idx": -1, "M_row": np.array([], dtype=np.int64)},
            {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle)},
        )
    if capture["12E"] is None:
        capture["12E"] = _boundary_io(
            {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle), "t_idx": -1, "M_row": np.array([], dtype=np.int64)},
            {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle)},
        )
    if capture["12F"] is None:
        capture["12F"] = _boundary_io(
            {
                "models": copy.deepcopy(models),
                "bundle": copy.deepcopy(bundle),
                "mi": -1,
                "t_m": -1,
                "t_idx": -1,
                "G_m": np.array([], dtype=np.float64),
                "alpha": float(hp["alpha"]),
            },
            {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle)},
        )

    handoffs["12D"] = capture["12D"]
    handoffs["12E"] = capture["12E"]
    handoffs["12F"] = capture["12F"]
    in_12g = {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle)}
    vbxxx._vb_optional_backwards_replay(models, bundle, bundle["options_vb"])
    vbxxx._vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
    vbxxx._vb_posterior_predictive_Y(models, bundle, bundle["options_vb"])
    vbxxx._vb_reorganize_X_S_from_QP(bundle)
    vbxxx._vb_options_N_neural_simulated_responses(models, bundle, bundle["options_vb"])
    handoffs["12G"] = _boundary_io(in_12g, {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle)})

    in_12h = {"models": copy.deepcopy(models), "bundle": copy.deepcopy(bundle)}
    vbxxx._vb_assemble_mdp_results_1691(models, bundle)
    out_12h: Any = copy.deepcopy(models[0] if len(models) == 1 else models)
    handoffs["12H"] = _boundary_io(in_12h, {"assembled": out_12h, "bundle": copy.deepcopy(bundle)})

    handoffs["12I"] = _boundary_io(
        {
            "spine_targets": [
                "spm_forwards",
                "spm_backwards",
                "_spm_sample",
                "_spm_action",
                "_vb_policy_depth_and_get_M",
                "_spm_MDP_update",
            ],
            "available_symbols": {
                "spm_forwards": bool(hasattr(vbxxx, "spm_forwards")),
                "spm_backwards": bool(hasattr(vbxxx, "spm_backwards")),
                "_spm_sample": bool(hasattr(vbxxx, "_spm_sample")),
                "_spm_action": bool(hasattr(vbxxx, "_spm_action")),
                "_vb_policy_depth_and_get_M": bool(hasattr(vbxxx, "_vb_policy_depth_and_get_M")),
                "_spm_MDP_update": bool(hasattr(vbxxx, "_spm_MDP_update")),
            },
        },
        {"call_counts": copy.deepcopy(call_trace)},
    )
    return handoffs


def replay_python_handoffs_from_matlab_rdp_for_entry12(rdp: dict[str, Any]) -> dict[str, Any]:
    """Rebuild ``12A``…``12I`` handoffs from a MATLAB-origin nested ``RDP`` (deterministic)."""
    return _capture_python_handoffs_from_rdp_matlab(copy.deepcopy(rdp))


def _capture_entry12_handoff_artifact(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    """Build workspace ``rgms_rdp11``, E-repair (VB capture parity), MATLAB subentry pulls, legacy Python scratch."""
    _capture_entry10_sort_artifact(dem_eng, training_t, n_outer)
    dem_eng.eval(_MATLAB_E_REPAIR_BEFORE_VB, nargout=0)
    rdp_matlab = copy.deepcopy(_pull_nested_rdp_from_matlab(dem_eng, "rgms_rdp11"))
    dem_eng.eval(
        "rgms_matlab_subentry_12a = spm_MDP_checkX(rgms_rdp11);",
        nargout=0,
    )
    matlab_12a_after_checkx = copy.deepcopy(
        _pull_nested_rdp_from_matlab(dem_eng, "rgms_matlab_subentry_12a")
    )
    matlab_subentries: dict[str, Any] = {
        "12A": {"after_spm_MDP_checkX": matlab_12a_after_checkx},
        "12B": None,
        "12C": None,
        "12D": None,
        "12E": None,
        "12F": None,
        "12G": None,
        "12H": None,
        "12I": None,
    }
    legacy_python_handoffs = _capture_python_handoffs_from_rdp_matlab(rdp_matlab)
    provenance = {
        "boundary": (
            "Nested MATLAB RDP after DEM lane + Entry-12 E repair (matches first ``spm_MDP_VB_XXX`` input)."
        ),
        "matlab_subentries": (
            "MATLAB truth per subentry; 12A = ``spm_MDP_checkX`` pull. 12B–12I reserved — extend builder."
        ),
        "legacy_python_handoffs": "Not used for MATLAB↔Python parity.",
        "training_t": int(training_t),
        "n_outer": int(n_outer),
    }
    return {
        "entry12_handoff_capture_v": ENTRY12_HANDOFF_CAPTURE_V,
        "training_t": int(training_t),
        "n_outer": int(n_outer),
        "tag": entry12_handoff_capture_tag(),
        "matlab_provenance": provenance,
        "matlab_rdp11_nested_mat": rdp_matlab,
        "rdp11_nested_mat": rdp_matlab,
        "matlab_subentries": matlab_subentries,
        "legacy_python_handoffs": legacy_python_handoffs,
        "handoffs": legacy_python_handoffs,
    }


def load_or_build_entry12_handoff_capture(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    capture_path = entry12_handoff_capture_path(training_t, n_outer)
    refresh = entry12_handoff_capture_refresh_enabled()
    if capture_path.exists() and not refresh:
        with capture_path.open("rb") as f:
            old = pickle.load(f)
        if (
            isinstance(old, dict)
            and int(old.get("entry12_handoff_capture_v", 0)) == ENTRY12_HANDOFF_CAPTURE_V
            and "rdp11_nested_mat" in old
            and "matlab_rdp11_nested_mat" in old
            and "matlab_subentries" in old
            and isinstance(old.get("matlab_subentries"), dict)
            and isinstance(old["matlab_subentries"].get("12A"), dict)
            and "after_spm_MDP_checkX" in old["matlab_subentries"]["12A"]
        ):
            return old
        refresh = True
    if capture_path.exists() and refresh:
        capture_path.unlink(missing_ok=True)
    artifact = _capture_entry12_handoff_artifact(dem_eng, training_t, n_outer)
    with capture_path.open("wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)
    return artifact


@pytest.mark.slow
def test_entry12_handoff_capture_build_or_reuse(dem_eng_entry12):
    training_t, n_outer = entry12_handoff_capture_driver_params()
    artifact = load_or_build_entry12_handoff_capture(dem_eng_entry12, training_t, n_outer)
    assert int(artifact["entry12_handoff_capture_v"]) == ENTRY12_HANDOFF_CAPTURE_V
    assert isinstance(artifact.get("matlab_rdp11_nested_mat"), dict)
    assert artifact["matlab_rdp11_nested_mat"] is artifact["rdp11_nested_mat"]
    assert isinstance(artifact.get("matlab_provenance"), dict)
    ms = artifact.get("matlab_subentries")
    assert isinstance(ms, dict) and "12A" in ms
    assert isinstance(ms["12A"], dict) and "after_spm_MDP_checkX" in ms["12A"]
    handoffs = artifact.get("handoffs")
    assert isinstance(handoffs, dict)
    for k in ("12A", "12B", "12C", "12D", "12E", "12F", "12G", "12H", "12I"):
        assert k in handoffs and isinstance(handoffs[k], dict)
        assert "in" in handoffs[k] and "out" in handoffs[k]
    assert entry12_handoff_capture_path(training_t, n_outer).is_file()
