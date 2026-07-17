#!/usr/bin/env python3
"""
OPTIM1FULL Phase A — classify tier **3g** failure before live VB or driver edits.

Normative queue: ``OPTIM1.md`` § **11.7.4** (steps **A1–A4**). Classification only — not sign-off.

Usage:
  python optim1full_phase_a_evidence.py           # full A1–A4 (A3 is slow)
  python optim1full_phase_a_evidence.py --from a4 # A1–A2 preflight + A4 only

Forbidden: edits to ``spm_MDP_VB_XXX.py``; ledger re-capture; ad-hoc ``python -c`` outside this script.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_CAPTURE_CALL2 = "capture_call2_game1"
_CAPTURE_LEDGER = "capture_optim1full_rand_ledger"
_TAG_CALL2 = "rgms_atari_optim1full_call2"
_NR_SEG = "nr_game_01"


def _scalar_t(rdp: object) -> None:
    models = rdp if isinstance(rdp, list) else [rdp]
    for m in models:
        if isinstance(m, dict) and "T" in m:
            m["T"] = float(np.asarray(m["T"]).reshape(-1)[0])


def _assemble_nr_game1_raw(mdp: list[dict[str, Any]], ne: int, c_val: float, ns: float = 256.0) -> dict[str, Any]:
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
    from python_src.toolbox.DEM.spm_set_goals import spm_set_goals

    rdp = spm_set_goals(mdp, [2, 3], [c_val, -c_val])
    rdp = spm_set_costs(rdp, [2, 3], [c_val, -c_val])
    rdp = spm_mdp2rdp(rdp, 0, 1.0 / ns)
    rdp["T"] = float(int(256 / ne))
    _scalar_t(rdp)
    return rdp


def _prepped(rdp_raw: dict[str, Any]) -> dict[str, Any]:
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested

    out = entry12_rdp_for_vb_from_mat_nested(copy.deepcopy(rdp_raw))
    _scalar_t(out)
    return out


def _count_draws_simple(rdp: object) -> int | str:
    """Scalar ``numpy.random.rand`` count only (no ``reuse_matlab_draws``)."""
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    ctr = [0]

    def shim(*_a: object, **_k: object) -> float:
        ctr[0] += 1
        return 0.5

    try:
        with patch("numpy.random.rand", side_effect=shim):
            spm_MDP_VB_XXX(copy.deepcopy(rdp), {})
        return int(ctr[0])
    except Exception as exc:
        return f"fail@{ctr[0]}: {exc}"


def _count_draws_entry12_flags(rdp: object) -> int | str:
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_vb_oracle_flags
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    ctr = [0]

    def shim(*_a: object, **_k: object) -> float:
        ctr[0] += 1
        return 0.5

    flags = entry12_vb_oracle_flags(reuse_matlab_draws=False)
    flags["dump_subentries"] = False
    try:
        with patch("numpy.random.rand", side_effect=shim):
            spm_MDP_VB_XXX(copy.deepcopy(rdp), {}, **flags)
        return int(ctr[0])
    except Exception as exc:
        return f"fail: {exc}"


def _vb_ledger_replay(rdp: object, buf: np.ndarray, start: int, k_allow: int) -> int | str:
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
    from tests.demo1.optim1full.optim1full_rand_ledger import optim1full_replay_matlab_draws

    try:
        with optim1full_replay_matlab_draws(buf, start_index=start, k_use=k_allow) as ctr:
            spm_MDP_VB_XXX(copy.deepcopy(rdp), {})
        return int(ctr[0])
    except Exception as exc:
        return f"fail: {exc}"


def _vb_reuse_custom_buf(rdp: object, vb_buf: np.ndarray, k_expected: int) -> int | str:
    """Replay explicit buffer via patched ``_vb_load_matlab_rand_buf`` (ledger segment lane)."""
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_vb_oracle_flags
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    buf = np.asarray(vb_buf, dtype=np.float64).ravel()
    flags = entry12_vb_oracle_flags(reuse_matlab_draws=True)
    flags["dump_subentries"] = False
    try:
        with patch(
            "python_src.toolbox.DEM.spm_MDP_VB_XXX._vb_load_matlab_rand_buf",
            return_value=buf.copy(),
        ):
            spm_MDP_VB_XXX(copy.deepcopy(rdp), {}, **flags)
        return k_expected
    except Exception as exc:
        return f"fail: {exc}"


def _vb_reuse_tag_oracle(rdp: object, tag: str) -> int | str:
    """Entry 12 tag-oracle lane (script 3 style): ``reuse_matlab_draws`` + tag ``vb_rand_buf``."""
    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_load_k_from_mat,
        entry12_vb_oracle_flags,
    )
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
    from tests.demo1.optim1full.optim1full_replay import entry12_vb_tag_env

    flags = entry12_vb_oracle_flags(reuse_matlab_draws=True)
    flags["dump_subentries"] = False
    try:
        with entry12_vb_tag_env(tag):
            k = int(entry12_load_k_from_mat(tag))
            spm_MDP_VB_XXX(copy.deepcopy(rdp), {}, **flags)
        return k
    except Exception as exc:
        return f"fail: {exc}"


def _try_assert_equal(a: object, b: object, label: str) -> str:
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    try:
        _assert_nested_rdp_equal(a, b, label)
        return "MATCH"
    except AssertionError as exc:
        return f"MISMATCH: {str(exc)[:1200]}"


def _preflight_artifacts() -> list[str]:
    """Return missing required paths (empty = OK)."""
    from python_src.toolbox.DEM.entry12_atari_calls import (
        ENTRY12_ATARI_CALL2_TAG,
        entry12_signoff_artifact_paths,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        ledger_artifacts_present,
        optim1full_rand_ledger_mat,
        optim1full_rand_manifest_json,
    )

    missing: list[str] = []
    pre = optim1full_mdp_pre_active_inference_mat()
    if not pre.is_file():
        missing.append(str(pre))
    if not ledger_artifacts_present():
        missing.append(str(optim1full_rand_ledger_mat()))
        missing.append(str(optim1full_rand_manifest_json()))
    from tests.demo1.optim1full.optim1full_replay import optim1full_entry12_fixture_env

    missing: list[str] = []
    pre = optim1full_mdp_pre_active_inference_mat()
    if not pre.is_file():
        missing.append(str(pre))
    if not ledger_artifacts_present():
        missing.append(str(optim1full_rand_ledger_mat()))
        missing.append(str(optim1full_rand_manifest_json()))
    with optim1full_entry12_fixture_env():
        paths = entry12_signoff_artifact_paths(ENTRY12_ATARI_CALL2_TAG)
        for key in ("rdp_mat", "rand_buf", "rand_k"):
            p = paths[key]
            if not p.is_file():
                missing.append(f"{key}:{p}")
    return missing


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OPTIM1FULL Phase A classification (not sign-off)")
    p.add_argument(
        "--from",
        dest="from_step",
        choices=("a1", "a3", "a4"),
        default="a1",
        help="Start at step (a4 skips expensive A3 draw counts)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    from scipy.io import loadmat

    from python_src.toolbox.DEM.entry12_atari_calls import (
        ENTRY12_ATARI_CALL2_TAG,
        entry12_load_vb_rand_buf_for_tag,
        entry12_signoff_artifact_paths,
        load_entry12_rdp_for_tag,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_authority import _LEDGER_CAPTURE_MODE, _mat_capture_meta
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_replay import atari_c_value, optim1full_entry12_fixture_env
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env

    skip_a3 = args.from_step in ("a4",)
    a2_branch = "not run"
    a3_branch = "skipped (--from a4)" if skip_a3 else "not run"
    a4_branch = "not run"

    pre = optim1full_mdp_pre_active_inference_mat()
    print("=" * 72)
    print("OPTIM1FULL Phase A evidence (classification only)")
    print("=" * 72)

    missing = _preflight_artifacts()
    if missing:
        print("\n[preflight] BLOCKED — missing artifacts (capture may be incomplete):")
        for m in missing:
            print(f"  - {m}")
        return 2
    print("\n[preflight] required artifacts present")

    # --- A1 ---
    print("\n[A1] MDP context: ledger MDP_pre vs call-2 tag capture")
    if not pre.is_file():
        print(f"  BLOCKED: missing {pre}")
        return 2
    raw_pre = loadmat(str(pre), squeeze_me=True, struct_as_record=False)
    meta_field = "metaPre" if "metaPre" in raw_pre else "meta"
    cap = _mat_capture_meta(pre, meta_field)
    ts = getattr(raw_pre[meta_field], "timestamp", "?")
    print(f"  on-disk MDP_pre: {pre.name}")
    print(f"  {meta_field}.capture = {cap!r}  timestamp = {ts}")
    print(f"  capture_call2_game1: entries_1_11 + GDP attach only (no vb_call1)")
    print(f"  capture_optim1full_rand_ledger: entries_1_11 + vb_call1 + GDP attach -> MDP_pre")
    a1_branch = (
        "CONFIRMED lane split (3a tag oracle != 3g ledger MDP context)"
        if cap == _LEDGER_CAPTURE_MODE
        else f"UNEXPECTED capture {cap!r} (expected {_LEDGER_CAPTURE_MODE!r})"
    )
    print(f"  branch: {a1_branch}")

    buf, manifest = load_validated_optim1full_ledger()
    seg = manifest.segment(_NR_SEG)
    print(f"  manifest {_NR_SEG}: start={seg.start} k={seg.k}")

    with optim1full_signoff_env(deadline_minutes="30"):
        mdp = load_mdp_from_mat(pre, "MDP_pre_active_inference")
        ne = load_ne_from_mat(pre, "Ne")
        c_val = atari_c_value()
        rdp_raw = _assemble_nr_game1_raw(mdp, ne, c_val)
        rdp_prepped = _prepped(rdp_raw)

        # --- A2 ---
        print("\n[A2] RDP identity: ledger game-1 vs frozen rgms_atari_call2")
        print(f"  live raw T={rdp_raw.get('T')}  prepped T={rdp_prepped.get('T')}")
        tag_rdp: dict[str, Any] | None = None
        raw_vs_tag = "not run"
        prep_vs_tag = "not run"
        with optim1full_entry12_fixture_env():
            from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call_rdp_mat_path

            tag_mat = entry12_atari_call_rdp_mat_path(ENTRY12_ATARI_CALL2_TAG)
            print(f"  tag RDP mat: {tag_mat} exists={tag_mat.is_file()}")
            if tag_mat.is_file():
                tag_rdp = load_entry12_rdp_for_tag(ENTRY12_ATARI_CALL2_TAG)
                raw_vs_tag = _try_assert_equal(rdp_raw, tag_rdp, "ledger raw vs tag VB-input")
                prep_vs_tag = _try_assert_equal(rdp_prepped, tag_rdp, "ledger prepped vs tag VB-input")
                print(f"  raw vs tag: {raw_vs_tag}")
                print(f"  prepped vs tag: {prep_vs_tag}")
            else:
                print("  tag RDP missing — A2 partial (live assembly only)")
        if prep_vs_tag == "MATCH":
            a2_branch = "prepped ledger RDP MATCHES tag oracle (3a fixture)"
        elif raw_vs_tag == "MATCH":
            a2_branch = "raw only matches tag — prep still required on NR path"
        else:
            a2_branch = "EXPECTED lane split — ledger MDP context != call-2 tag capture"
        print(f"  branch: {a2_branch}")

        # --- A3 ---
        if skip_a3:
            print("\n[A3] skipped (--from a4); prior run: raw/prepped native count = 32256 vs manifest k=4096")
        else:
            print("\n[A3] RDP prep draw-count gap (same ledger MDP_pre assembly)")
            print(f"  manifest k reference: {seg.k} (MATLAB NR game 1)")
            raw_simple = _count_draws_simple(rdp_raw)
            prep_simple = _count_draws_simple(rdp_prepped)
            raw_e12 = _count_draws_entry12_flags(rdp_raw)
            prep_e12 = _count_draws_entry12_flags(rdp_prepped)
            print(f"  raw assembly  (simple rand patch):     {raw_simple}")
            print(f"  prepped RDP   (simple rand patch):     {prep_simple}")
            print(f"  raw assembly  (entry12 oracle flags):  {raw_e12}")
            print(f"  prepped RDP   (entry12 oracle flags):  {prep_e12}")
            if isinstance(prep_simple, int) and prep_simple == seg.k:
                a3_branch = "PREP CLOSES GAP -> Phase B driver (wire script-3 RDP prep on NR path)"
            elif isinstance(raw_simple, int) and raw_simple == seg.k:
                a3_branch = "RAW already matches k - prep not the gap; proceed A4"
            else:
                a3_branch = "GAP REMAINS ON PREPPED RDP -> proceed A4"
            print(f"  branch: {a3_branch}")

        # --- A4 ---
        print("\n[A4] RNG harness: reuse_matlab_draws vs ledger segment replay (prepped RDP)")
        seg_buf = buf[seg.start : seg.start + seg.k]
        arm_a_ledger = _vb_reuse_custom_buf(rdp_prepped, seg_buf, seg.k)
        arm_a_tag_on_ledger = "not run"
        arm_a_tag_on_tag = "not run"
        with optim1full_entry12_fixture_env():
            buf_path = entry12_signoff_artifact_paths(ENTRY12_ATARI_CALL2_TAG)["rand_buf"]
            print(f"  tag vb_rand_buf: {buf_path.name} exists={buf_path.is_file()}")
            tag_buf = entry12_load_vb_rand_buf_for_tag(ENTRY12_ATARI_CALL2_TAG)
            arm_a_tag_on_ledger = _vb_reuse_custom_buf(rdp_prepped, tag_buf, int(tag_buf.size))
            if tag_rdp is not None:
                arm_a_tag_on_tag = _vb_reuse_tag_oracle(tag_rdp, ENTRY12_ATARI_CALL2_TAG)
        arm_b = _vb_ledger_replay(rdp_prepped, buf, seg.start, seg.k)
        print(f"  (A1) reuse + ledger nr_game_01 buf ({seg.k}):              {arm_a_ledger}")
        print(f"  (A2) reuse + tag buf on ledger prepped RDP:               {arm_a_tag_on_ledger}")
        print(f"  (A3) reuse + tag buf on tag RDP (3a control):             {arm_a_tag_on_tag}")
        print(f"  (B)  optim1full_replay_matlab_draws segment only:         {arm_b}")

        def _ok(x: object, k: int = seg.k) -> bool:
            return isinstance(x, int) and x == k

        if _ok(arm_a_tag_on_tag) and not _ok(arm_b):
            if _ok(arm_a_tag_on_ledger):
                a4_branch = "3a control OK; ledger prepped OK with tag buf; external replay fail -> Phase B ledger harness"
            else:
                a4_branch = (
                    "3a control OK on tag RDP but ledger prepped fails all reuse -> "
                    "structural MATCH insufficient; NR-context Entry 12 tag needed"
                )
        elif _ok(arm_a_tag_on_ledger) and not _ok(arm_b):
            a4_branch = "reuse path OK on ledger prepped; external replay fail -> Phase B ledger harness wiring"
        elif _ok(arm_a_ledger) and not _ok(arm_b):
            a4_branch = "Ledger segment reuse OK; external replay fail -> Phase B ledger harness wiring"
        elif not _ok(arm_a_tag_on_tag):
            a4_branch = "3a control FAIL — tag fixtures incomplete/corrupt; refresh capture_call2_game1 before Phase C"
        elif _ok(arm_a_tag_on_tag) and _ok(arm_b):
            a4_branch = "BOTH PASS on prepped RDP -> NR loop uses raw RDP without prep (Phase B prep fix)"
        else:
            a4_branch = "ALL replay arms fail on ledger prepped RDP -> Phase C Entry 12 on NR-context RDP"
        print(f"  branch: {a4_branch}")

    print("\n" + "=" * 72)
    print("Phase A summary")
    print(f"  A1: {a1_branch}")
    print(f"  A2: {a2_branch}")
    print(f"  A3: {a3_branch}")
    print(f"  A4: {a4_branch}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
