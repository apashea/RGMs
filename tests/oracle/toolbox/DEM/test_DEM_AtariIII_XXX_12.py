"""**XXX 12** — FSL-input Entry 12: ``spm_MDP_VB_XXX(ctx["RDP"])`` at full FSL ``RDP``.

Loads nested ``RDP`` from ``DEMAtariIII_fsl_1_11_rdp.mat`` by default (Phase **1** oracle; same as
``vb_12_monitor_spm_MDP_VB_XXX_from_fsl_rdp.m`` / ``RGMS_ATARI_FSL_1_11_MAT_PATH``). Set
``RGMS_XXX_12_RDP_FROM_CTX=1`` to use FSL context PKL (``fixtures/DEMAtariIII_fsl_1_11_ctx.pkl``) instead.
Explicit ``RGMS_XXX_12_RDP_FROM_MAT=1`` still forces the ``.mat`` lane.
Writes ``fixtures/DEMAtariIII_XXX_12_pdp.pkl`` (dict with top-level key ``PDP`` only;
override ``RGMS_XXX_12_PDP_PKL_PATH``).

**Opt-in:** ``RGMS_ATARI_RUN_XXX_12=1`` (VB on full Atari ``RDP`` can be long).

**Long runs — wall limit + where you died (applies here):** The test calls
``spm_MDP_VB_XXX`` with the **same** env toggles documented in ``DEM_AtariIII.py`` and
``Atari_example.md`` § **ENTRY 1-11**: ``RGMS_ATARI_RUN_DEADLINE_MINUTES`` (seeds
``perf_counter`` ceiling and error text) or optional explicit ``RGMS_ATARI_RUN_DEADLINE_MONO``;
``RGMS_ATARI_RUN_SEGMENT_TIMING=1`` for stderr segment timings. **Tracing** is
``get_dem_atariiii_run_last_label()``. On **any** exception from ``spm_MDP_VB_XXX`` inside
``_run_xxx12_spm_mdp_vb_xxx``, the harness prints ``[XXX 12] last traced segment = …``, the
traceback, and—only when the exception is the deadline ``RuntimeError``—``[XXX 12] exit reason:
time limit reached``, then re-raises. **If neither deadline env is set,**
``_run_xxx12_spm_mdp_vb_xxx`` sets ``RGMS_ATARI_RUN_DEADLINE_MINUTES=40`` for that run only,
then restores prior env.

**Run log:** overwrites ``matlab_custom/test_DEM_AtariIII_XXX_12_output.txt`` (module
docstring + teed stdout/stderr).

**Segment timing:** when ``RGMS_ATARI_RUN_SEGMENT_TIMING=1`` (same env as ``DEM_AtariIII`` /
FSL 1-11), stderr includes harness ``[XXX 12 run trace]`` at load/save and VB bands
``[spm_MDP_VB_XXX 12X] total_s=…`` per band inside ``spm_MDP_VB_XXX.py`` (12E/12F summed). Total VB wall time:
``[XXX 12] spm_MDP_VB_XXX wall_s=...``.

**Validation:** after **1a → 1b → 3**, run
``python tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py`` (script **4**).
See ``Atari_example.md`` § **Entry 12 workflow — four scripts**.

RNG imperative: script **3** output is meaningful for compute parity only under the
paired replay contract (same tag, coherent ``K``/``vb_rand_buf`` from **1a/1b**).
If replay coherence is broken, repair RNG alignment before debugging causal reds.
"""

from __future__ import annotations

import copy
import os
import pickle
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import pytest

from python_src.toolbox.DEM.DEM_AtariIII import (
    _rgms_deadline_reset_for_run,
    _rgms_run_deadline_check,
    _rgms_run_set_last_label,
    get_dem_atariiii_run_last_label,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

_XXX12_REPO_ROOT = Path(__file__).resolve().parents[4]


def _xxx12_run_output_txt_path() -> Path:
    return _XXX12_REPO_ROOT / "matlab_custom" / "test_DEM_AtariIII_XXX_12_output.txt"


class _Xxx12TeeIO:
    """Duplicate text writes to multiple streams (console + report file)."""

    __slots__ = ("_streams",)

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            s = str(s)
        for st in self._streams:
            st.write(s)
        return len(s)

    def flush(self) -> None:
        for st in self._streams:
            st.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._streams[0], "isatty", lambda: False)())


_XXX12_ENABLED = str(os.getenv("RGMS_ATARI_RUN_XXX_12", "")).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_XXX12_SEGMENT_T0 = 0.0


def _xxx12_segment_timing_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_RUN_SEGMENT_TIMING", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _xxx12_reset_segment_timer() -> None:
    global _XXX12_SEGMENT_T0
    _XXX12_SEGMENT_T0 = 0.0


def _xxx12_run_trace(label: str) -> None:
    """Mirror ``[DEM_AtariIII run trace]`` lines when ``RGMS_ATARI_RUN_SEGMENT_TIMING`` is on."""
    if not _xxx12_segment_timing_enabled():
        return
    global _XXX12_SEGMENT_T0
    now = time.perf_counter()
    dt = now - _XXX12_SEGMENT_T0 if _XXX12_SEGMENT_T0 > 0.0 else 0.0
    _XXX12_SEGMENT_T0 = now
    print(
        f"[XXX 12 run trace] {label}  (+{dt:.6f}s since previous segment)",
        file=sys.stderr,
        flush=True,
    )


def _fsl_context_pkl_in_path() -> Path:
    raw = str(os.getenv("RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "fixtures" / "DEMAtariIII_fsl_1_11_ctx.pkl"


def _xxx12_env_truthy(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in ("1", "true", "yes", "on")


def _xxx12_rdp_from_mat() -> bool:
    """Phase 1 default: MATLAB FSL ``rdp.mat`` oracle lane (not ctx PKL)."""
    if _xxx12_env_truthy("RGMS_XXX_12_RDP_FROM_CTX"):
        return False
    if _xxx12_env_truthy("RGMS_XXX_12_RDP_FROM_MAT"):
        return True
    return True


def _load_xxx12_rdp() -> dict[str, Any]:
    """Load ``RDP`` for VB: call ``tag`` → script **1b** ``rdp.mat``; else FSL ``.mat`` oracle."""
    tag = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "")).strip()
    if tag and _xxx12_rdp_from_mat():
        from python_src.toolbox.DEM.entry12_atari_calls import load_entry12_rdp_for_tag

        return load_entry12_rdp_for_tag(tag)
    if not _xxx12_rdp_from_mat():
        pkl_in = _fsl_context_pkl_in_path()
        if not pkl_in.is_file():
            raise FileNotFoundError(f"missing FSL context PKL: {pkl_in}")
        with pkl_in.open("rb") as f:
            ctx = pickle.load(f)
        if not isinstance(ctx, dict) or "RDP" not in ctx:
            raise AssertionError("FSL PKL must be a dict with key 'RDP'")
        return copy.deepcopy(ctx["RDP"])
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
    from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import (
        _fsl_1_11_mat_path,
        _load_matlab_nested_rdp_for_fsl_oracle,
    )

    mat_in = _fsl_1_11_mat_path()
    if not mat_in.is_file():
        raise FileNotFoundError(f"missing FSL RDP mat: {mat_in}")
    rdp_raw = _load_matlab_nested_rdp_for_fsl_oracle(mat_in)
    if not isinstance(rdp_raw, dict):
        raise AssertionError(f"FSL mat RDP must convert to dict, got {type(rdp_raw).__name__}")
    return copy.deepcopy(entry12_rdp_for_vb_from_mat_nested(rdp_raw))


def _xxx12_pdp_pkl_out_path() -> Path:
    raw = str(os.getenv("RGMS_XXX_12_PDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    tag = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "")).strip()
    if tag:
        from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

        return entry12_signoff_artifact_paths(tag)["pdp_pkl"]
    return Path(__file__).resolve().parent / "fixtures" / "DEMAtariIII_XXX_12_pdp.pkl"


def _xxx12_out_dir() -> Path:
    raw = str(os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "fixtures"


def _xxx12_rdp_pkl_out_path() -> Path:
    raw = str(os.getenv("RGMS_XXX_12_RDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    tag = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "")).strip()
    if tag:
        from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

        return entry12_signoff_artifact_paths(tag)["rdp_pkl"]
    return _xxx12_out_dir() / "DEMAtariIII_XXX_12_rdp.pkl"


def _dump_xxx12_rdp_pkl(rdp: Any) -> None:
    path = _xxx12_rdp_pkl_out_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump({"RDP": rdp}, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[XXX 12] wrote RDP pickle: {path}", file=sys.stderr, flush=True)


def _dump_xxx12_pdp_pkl(pdp: Any) -> None:
    path = _xxx12_pdp_pkl_out_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump({"PDP": pdp}, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[XXX 12] wrote PDP pickle: {path}", file=sys.stderr, flush=True)


_XXX12_DEFAULT_TIMEOUT_MINUTES = 40


def _xxx12_reuse_matlab_draws() -> bool:
    """Phase 1 oracle: replay MATLAB ``vb_rand_buf`` when not explicitly disabled."""
    if _xxx12_env_truthy("RGMS_XXX_12_NATIVE_RNG"):
        return False
    if _xxx12_env_truthy("RGMS_XXX_12_MATLAB_RAND_REPLAY"):
        return True
    return True


def _run_xxx12_spm_mdp_vb_xxx(rdp: dict[str, Any]) -> Any:
    """``spm_MDP_VB_XXX(rdp, {})`` with deadline env; restores prior env."""
    old_mins = os.environ.get("RGMS_ATARI_RUN_DEADLINE_MINUTES")
    installed_default_minutes = not (
        str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MINUTES", "")).strip()
        or str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MONO", "")).strip()
    )
    if installed_default_minutes:
        os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = str(_XXX12_DEFAULT_TIMEOUT_MINUTES)

    try:
        try:
            _rgms_deadline_reset_for_run()
            _rgms_run_set_last_label("ENTRY12: spm_MDP_VB_XXX")
            _rgms_run_deadline_check()
            from python_src.toolbox.DEM.entry12_atari_calls import (
                entry12_assert_buf_k_coherent,
                entry12_resolve_run_tag,
                entry12_signoff_artifact_paths,
                entry12_vb_oracle_flags,
            )

            reuse = _xxx12_reuse_matlab_draws()
            tag = entry12_resolve_run_tag()
            paths = entry12_signoff_artifact_paths(tag)
            if reuse and not paths["rand_buf"].is_file():
                raise FileNotFoundError(
                    "MATLAB vb_rand_buf missing for Phase 1 oracle "
                    f"({paths['rand_buf']}). "
                    "Run entry12_preflight_vb_rand_k.py then DEMAtariIII_entry12_dump_all_subentries."
                )
            if reuse:
                entry12_assert_buf_k_coherent(tag)
            return spm_MDP_VB_XXX(rdp, {}, **entry12_vb_oracle_flags(reuse_matlab_draws=reuse))
        except Exception as exc:
            print(
                f"[XXX 12] last traced segment = {get_dem_atariiii_run_last_label()!r}",
                file=sys.stderr,
                flush=True,
            )
            traceback.print_exc(file=sys.stderr)
            if isinstance(exc, RuntimeError) and "TIME LIMIT OF" in str(
                exc
            ) and "MINUTES EXCEEDED" in str(exc):
                print(
                    "[XXX 12] exit reason: time limit reached",
                    file=sys.stderr,
                    flush=True,
                )
            raise
    finally:
        if installed_default_minutes:
            if old_mins is None:
                os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MINUTES", None)
            else:
                os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = old_mins


@pytest.mark.slow
@pytest.mark.skipif(
    not _XXX12_ENABLED,
    reason=(
        "XXX 12 (FSL-input VB): set RGMS_ATARI_RUN_XXX_12=1. See Atari_example.md § Entry 12."
    ),
)
def test_xxx_12_fsl_rdp_to_pdp_pkl() -> None:
    """Load FSL ``RDP`` (``.mat`` oracle default), run ``spm_MDP_VB_XXX``, write ``PDP`` PKL."""
    try:
        rdp = _load_xxx12_rdp()
    except FileNotFoundError as e:
        pytest.skip(str(e))

    out_path = _xxx12_run_output_txt_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_f = out_path.open("w", encoding="utf-8")
    report_f.write(__doc__ or "")
    report_f.write(f"\n--- RUN OUTPUT (stdout + stderr) — {out_path} ---\n")
    report_f.flush()
    old_err, old_out = sys.stderr, sys.stdout
    try:
        sys.stderr = _Xxx12TeeIO(old_err, report_f)
        sys.stdout = _Xxx12TeeIO(old_out, report_f)

        _xxx12_reset_segment_timer()
        _xxx12_run_trace("start (tee active)")

        from python_src.toolbox.DEM.entry12_atari_calls import (
            entry12_assert_buf_k_coherent,
            entry12_assert_signoff_chain_ready,
            entry12_log_signoff_chain,
            entry12_refresh_manifest_script3_checksums,
            entry12_resolve_run_tag,
        )

        tag_env = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "")).strip()
        tag_use = tag_env or entry12_resolve_run_tag()
        if tag_env or _xxx12_reuse_matlab_draws():
            entry12_assert_signoff_chain_ready(
                tag_use,
                require_rand_buf=_xxx12_reuse_matlab_draws(),
                require_script3_pkls=False,
            )
        paths = entry12_log_signoff_chain(tag_use, stream=sys.stderr)

        src = "FSL RDP mat" if _xxx12_rdp_from_mat() else "FSL context PKL"
        if tag_env:
            src = f"tag {tag_env!r} rdp.mat (1b snapshot)"
        reuse = _xxx12_reuse_matlab_draws()
        print(f"[XXX 12] RDP source: {src}", file=sys.stderr, flush=True)
        print(
            f"[XXX 12] reuse_matlab_draws={reuse}",
            file=sys.stderr,
            flush=True,
        )
        if reuse:
            try:
                entry12_assert_buf_k_coherent(tag_use)
            except ValueError as exc:
                print(f"[XXX 12] warning: {exc}", file=sys.stderr, flush=True)
            print(
                f"[XXX 12] vb_rand_buf: {paths['rand_buf']}",
                file=sys.stderr,
                flush=True,
            )
        _xxx12_run_trace(f"loaded RDP from {src}")
        _xxx12_run_trace("after deepcopy(RDP)")
        _dump_xxx12_rdp_pkl(rdp)
        t0 = time.perf_counter()
        pdp = _run_xxx12_spm_mdp_vb_xxx(rdp)
        wall = time.perf_counter() - t0
        print(f"[XXX 12] spm_MDP_VB_XXX wall_s={wall:.6f}", file=sys.stderr, flush=True)
        _xxx12_run_trace("after spm_MDP_VB_XXX")

        assert isinstance(pdp, dict)
        _dump_xxx12_pdp_pkl(pdp)
        _xxx12_run_trace("after PDP pickle write")
        entry12_refresh_manifest_script3_checksums(tag_use)
    finally:
        sys.stderr = old_err
        sys.stdout = old_out
        report_f.close()
