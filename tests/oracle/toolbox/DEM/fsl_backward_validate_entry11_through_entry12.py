#!/usr/bin/env python3
"""FSL backward — Entry 11 ``RDP`` through frozen Entry 12 VB + Validation 12.

**North star:** MATLAB Entry 12 fixtures and ``XXX_12_compare_pdp_pkl_to_mat.py`` authority.
**Does not edit** frozen Entry 12 code, compare fixtures, or overwrite canonical script **3** PKLs.

Steps:
1. Load ``DEMAtariIII_fsl_backward_entry11_rdp.pkl`` (must already match ``XXX_12_rdp.mat``).
2. Run ``spm_MDP_VB_XXX`` with ``vb_rand_buf`` replay (``rgms_canonical`` tag).
3. Write Python dumps under ``fixtures/fsl_backward_entry11_entry12_vb/`` only.
4. Run full Validation **12** (script **4** logic) vs read-only MATLAB ``rgms_canonical`` mats.

Report: ``matlab_custom/fsl_backward_entry11_entry12_validation12_output.txt``

See ``Atari_example.md`` § FSL backward validation — Entry 11 → Entry 12 VB gate.
"""
from __future__ import annotations

import argparse
import copy
import os
import pickle
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir

_TAG = "rgms_canonical"
_VB_OUT_DIR = demo1_fixtures_dir() / "fsl_backward_entry11_entry12_vb"
_ENTRY11_RDP_PKL = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry11_rdp.pkl"
_PDP_OUT_PKL = _VB_OUT_DIR / "DEMAtariIII_fsl_backward_entry11_entry12_pdp.pkl"
_RDP_SNAPSHOT_PKL = _VB_OUT_DIR / "DEMAtariIII_fsl_backward_entry11_entry12_rdp.pkl"
_REPORT = _REPO / "matlab_custom" / "fsl_backward_entry11_entry12_validation12_output.txt"


def _report_path() -> Path:
    return _REPORT


def _default_entry11_rdp_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY11_RDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _ENTRY11_RDP_PKL


def _canonical_signoff_paths(tag: str) -> dict[str, Path]:
    """Sign-off paths under default ``fixtures/`` (ignore ``RGMS_ENTRY12_CAPTURE_OUT_DIR``)."""
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

    old_out = os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
    try:
        return entry12_signoff_artifact_paths(tag)
    finally:
        if old_out is not None:
            os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = old_out


def _mirror_canonical_rng_to_out_dir(*, tag: str, out_dir: Path) -> None:
    """
    ``spm_MDP_VB_XXX`` resolves ``vb_rand_buf`` via ``entry12_signoff_artifact_paths``,
    which follows ``RGMS_ENTRY12_CAPTURE_OUT_DIR``. Mirror read-only canonical RNG mats
    into the FSL-only dump dir so frozen Entry 12 code stays unchanged.
    """
    canon = _canonical_signoff_paths(tag)
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in ("rand_buf", "rand_k"):
        src = canon[key]
        dst = out_dir / src.name
        if not src.is_file():
            raise FileNotFoundError(f"missing canonical {key}: {src}")
        if not dst.is_file() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)
        print(f"[FSL Entry11→12 VB] mirrored {key} → {dst}", file=sys.stderr, flush=True)


def _rdp_for_vb_from_entry11_pkl(pkl_path: Path, *, tag: str) -> dict[str, Any]:
    """Entry 11 assembly + script **3** container alignment (``H``, ``MDP.A`` shapes)."""
    from python_src.toolbox.DEM.fsl_backward_entry11 import entry11_rdp_for_entry12_vb

    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "RDP" not in blob:
        raise KeyError(f"expected dict with RDP in {pkl_path}")
    return entry11_rdp_for_entry12_vb(copy.deepcopy(blob["RDP"]), tag=tag)


def _preflight_entry11_vb_input_vs_entry12(*, tag: str, pkl_path: Path) -> None:
    """Fail fast if Entry 11 ``RDP`` cannot match script **3** VB input after alignment."""
    from python_src.toolbox.DEM.entry12_atari_calls import load_entry12_rdp_for_tag
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    py = _rdp_for_vb_from_entry11_pkl(pkl_path, tag=tag)
    ref = load_entry12_rdp_for_tag(tag)
    _assert_nested_rdp_equal(py, ref, "Entry 11 VB-input preflight vs Entry 12 script 3")


def _run_vb_on_entry11_rdp(*, tag: str, out_dir: Path) -> Any:
    from python_src.toolbox.DEM.DEM_AtariIII import (
        _rgms_deadline_reset_for_run,
        _rgms_run_deadline_check,
        _rgms_run_set_last_label,
    )
    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_assert_buf_k_coherent,
        entry12_assert_signoff_chain_ready,
        entry12_log_signoff_chain,
        entry12_vb_oracle_flags,
    )
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    entry11_pkl = _default_entry11_rdp_pkl()
    if not entry11_pkl.is_file():
        raise FileNotFoundError(
            f"missing {entry11_pkl} — run fsl_backward_run_entry11_isolated.py first."
        )

    entry12_assert_signoff_chain_ready(tag, require_rand_buf=True, require_script3_pkls=False)
    canon = _canonical_signoff_paths(tag)
    entry12_log_signoff_chain(tag, stream=sys.stderr)

    print(
        f"[FSL Entry11→12 VB] RDP input={entry11_pkl}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[FSL Entry11→12 VB] vb_rand_buf (canonical)={canon['rand_buf']}",
        file=sys.stderr,
        flush=True,
    )
    # VB-input preflight uses canonical ``fixtures/`` (not ``OUT_DIR``).
    _preflight_entry11_vb_input_vs_entry12(tag=tag, pkl_path=entry11_pkl)
    rdp = _rdp_for_vb_from_entry11_pkl(entry11_pkl, tag=tag)

    old_out = os.environ.get("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = tag
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = str(out_dir.resolve())
    try:
        print(
            f"[FSL Entry11→12 VB] dump out_dir={out_dir}",
            file=sys.stderr,
            flush=True,
        )
        _mirror_canonical_rng_to_out_dir(tag=tag, out_dir=out_dir)
        entry12_assert_buf_k_coherent(tag)
        out_dir.mkdir(parents=True, exist_ok=True)
        with _RDP_SNAPSHOT_PKL.open("wb") as f:
            pickle.dump({"RDP": rdp}, f, protocol=pickle.HIGHEST_PROTOCOL)

        _rgms_deadline_reset_for_run()
        _rgms_run_set_last_label("FSL Entry11→12: spm_MDP_VB_XXX")
        _rgms_run_deadline_check()
        t0 = time.perf_counter()
        pdp = spm_MDP_VB_XXX(rdp, {}, **entry12_vb_oracle_flags(reuse_matlab_draws=True))
        print(
            f"[FSL Entry11→12 VB] spm_MDP_VB_XXX wall_s={time.perf_counter() - t0:.6f}",
            file=sys.stderr,
            flush=True,
        )
        if not isinstance(pdp, dict):
            raise TypeError(f"expected dict PDP, got {type(pdp).__name__}")
        with _PDP_OUT_PKL.open("wb") as f:
            pickle.dump({"PDP": pdp}, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"[FSL Entry11→12 VB] wrote {_PDP_OUT_PKL}", file=sys.stderr, flush=True)
        return pdp
    finally:
        if old_out is None:
            os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
        else:
            os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = old_out


def _run_validation12_compare(*, tag: str, vb_out_dir: Path, pdp_pkl: Path) -> int:
    """Full script **4** via existing module; patch only Python PKL paths (MATLAB ``.mat`` in fixtures/)."""
    import tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat as v12

    v12._default_pkl_path = lambda: pdp_pkl  # type: ignore[method-assign]
    # Input ``RDP`` lane: canonical script **3** pickle (Entry 11 object-compare already
    # proved ``fsl_backward_entry11_rdp`` == ``XXX_12_rdp.mat``; FSL snapshot is VB-only).

    def _subentry_pkl_path(code: str) -> Path:
        return vb_out_dir / f"DEMAtariIII_entry12_{tag}_{code}.pkl"

    v12._subentry_pkl_path = _subentry_pkl_path  # type: ignore[method-assign]
    # ``_entry12_out_dir`` unchanged → MATLAB subentry ``.mat`` authority stays in ``fixtures/``.

    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = tag
    os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
    os.environ["RGMS_FSL_ENTRY11_GATE_COMPARE"] = "1"
    argv = ["--coerce-sparse-to-dense-for-compare"]
    try:
        return int(v12.main(argv))
    finally:
        os.environ.pop("RGMS_FSL_ENTRY11_GATE_COMPARE", None)


def _execute(*, tag: str, vb_only: bool, compare_only: bool) -> int:
    vb_out = _VB_OUT_DIR
    if not compare_only:
        _run_vb_on_entry11_rdp(tag=tag, out_dir=vb_out)
    if vb_only:
        return 0
    return _run_validation12_compare(tag=tag, vb_out_dir=vb_out, pdp_pkl=_PDP_OUT_PKL)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 11 RDP through Entry 12 VB + Validation 12")
    p.add_argument("--tag", default=_TAG, help="Entry 12 capture tag (default rgms_canonical)")
    p.add_argument("--vb-only", action="store_true", help="Run VB only, skip script 4")
    p.add_argument("--compare-only", action="store_true", help="Run script 4 only (VB artifacts must exist)")
    args = p.parse_args(argv)

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "FSL backward — Entry 11 ``RDP`` through Entry 12 ``spm_MDP_VB_XXX`` + Validation 12.\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out, tee_err = sys.stdout, sys.stderr
        from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import _TeeIO

        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(tag=str(args.tag).strip(), vb_only=args.vb_only, compare_only=args.compare_only)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout = tee_out
            sys.stderr = tee_err


if __name__ == "__main__":
    raise SystemExit(main())
