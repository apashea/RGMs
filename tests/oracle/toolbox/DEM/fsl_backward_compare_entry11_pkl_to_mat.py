#!/usr/bin/env python3
"""FSL backward 4 — Entry 11: compare Python ``ctx['RDP']`` vs Entry 12 Call 1 input ``.mat``.

**Authority (read-only Entry 12 fixture):** ``fixtures/DEMAtariIII_XXX_12_rdp.mat``
(``rgms_canonical`` / VB Call **1** input from script **1b**).

**Default:** VB-input lane — ``entry11_rdp_for_entry12_vb`` vs ``load_entry12_rdp_for_tag`` (script **3**).

**Legacy:** ``--raw-assembly-oracle-lane`` — raw assembly vs ``.mat`` with oracle coercion.

**Strict:** no ``[accepted ledger dim 511 vs 485 …]`` on the legacy lane.

**Report:** ``matlab_custom/fsl_backward_compare_entry11_output.txt``

See ``Atari_example.md`` § **FSL backward validation (Entry 11 → 1)**.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry11_output.txt"


def _default_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY11_RDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    legacy = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY11_CONTEXT_PKL_PATH", "")).strip()
    if legacy:
        return Path(legacy).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry11_rdp.pkl"


def _default_mat() -> Path:
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call_rdp_mat_path

    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY11_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return entry12_atari_call_rdp_mat_path("rgms_canonical")


class _TeeIO:
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


def _load_pkl_assembly_rdp(pkl_path: Path) -> Any:
    with open(pkl_path, "rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "RDP" not in blob:
        raise KeyError(f"expected dict with RDP in {pkl_path}")
    return blob["RDP"]


def _load_pkl_vb_rdp(pkl_path: Path) -> Any:
    """Prefer ``RDP_vb`` when isolated runner wrote VB prep; else assembly."""
    with open(pkl_path, "rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "RDP" not in blob:
        raise KeyError(f"expected dict with RDP in {pkl_path}")
    if "RDP_vb" in blob:
        return blob["RDP_vb"]
    from python_src.toolbox.DEM.fsl_backward_entry11 import entry11_rdp_for_entry12_vb

    return entry11_rdp_for_entry12_vb(blob["RDP"])


def _load_mat_rdp(mat_path: Path) -> Any:
    from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import _load_matlab_nested_rdp_for_fsl_oracle

    return _load_matlab_nested_rdp_for_fsl_oracle(mat_path)


def _execute(args: argparse.Namespace) -> int:
    from python_src.toolbox.DEM.entry12_atari_calls import load_entry12_rdp_for_tag
    from python_src.toolbox.DEM.fsl_backward_entry11 import entry11_rdp_for_entry12_vb
    from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import compare_nested_rdp_oracle_lane
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(
            f"missing Entry 12 Call 1 RDP mat: {mat_path}\n"
            "Refresh via Entry 12 script 1b (DEMAtariIII_entry12_dump_all_subentries.m)."
        )

    assembly = _load_pkl_assembly_rdp(pkl_path)
    print(
        f"[FSL backward Entry 11] PKL={pkl_path}",
        file=sys.stderr,
    )
    print(
        f"[FSL backward Entry 11] MAT (Entry 12 Call 1 spec)={mat_path}",
        file=sys.stderr,
    )

    if args.raw_assembly_oracle_lane:
        mat_rdp = _load_mat_rdp(mat_path)
        return compare_nested_rdp_oracle_lane(
            assembly,
            mat_rdp,
            lane="FSL backward Entry 11 (raw assembly)",
            strict=args.check_rdp_checkx_strict,
            report_only=args.report_type_mismatches_only,
            coerce_sparse=args.coerce_sparse_to_dense_for_compare,
            schema_only=args.check_rdp_checkx_schema_only,
            accept_ledger_dim_511_vs_485=False,
        )

    tag = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "rgms_canonical")).strip() or "rgms_canonical"
    py_vb = _load_pkl_vb_rdp(pkl_path)
    ref_vb = load_entry12_rdp_for_tag(tag)
    print(
        "[FSL backward Entry 11] compare lane: VB-input prep vs script 3 ``load_entry12_rdp_for_tag``",
        file=sys.stderr,
    )
    try:
        _assert_nested_rdp_equal(py_vb, ref_vb, "RDP")
    except AssertionError:
        traceback.print_exc()
        return 1
    print("OK: nested RDP parity (FSL backward Entry 11 VB-input lane)", file=sys.stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        ).print_help()
        return 0

    p = argparse.ArgumentParser(description="FSL backward 4 — Entry 11 strict RDP compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    p.add_argument("--coerce-sparse-to-dense-for-compare", action="store_true")
    p.add_argument("--report-type-mismatches-only", action="store_true")
    p.add_argument("--check-rdp-checkx-schema-only", action="store_true")
    p.add_argument("--check-rdp-checkx-strict", action="store_true")
    p.add_argument(
        "--raw-assembly-oracle-lane",
        action="store_true",
        help="Legacy: compare raw assembly vs .mat with oracle coercion (not sign-off).",
    )
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = _default_pkl()
    if args.mat is None:
        args.mat = _default_mat()

    out_path = _report_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as report_f:
        report_f.write(__doc__ or "")
        report_f.write(f"\n--- RUN OUTPUT — {out_path} ---\n")
        report_f.flush()
        old_err, old_out = sys.stderr, sys.stdout
        sys.stderr = _TeeIO(old_err, report_f)
        sys.stdout = _TeeIO(old_out, report_f)
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stderr, sys.stdout = old_err, old_out


if __name__ == "__main__":
    raise SystemExit(main())
