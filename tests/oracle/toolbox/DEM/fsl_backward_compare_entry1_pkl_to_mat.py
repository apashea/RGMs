#!/usr/bin/env python3
"""FSL backward — Entry 1: compare Python constants vs MATLAB authority.

**Authority:** ``entry1_*`` and legacy ``C`` in ``DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

**Report:** ``matlab_custom/fsl_backward_compare_entry1_output.txt``
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry1_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY1_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry1_post.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY1_AUTHORITY_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    )


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


def _scalar_int(raw: Any, name: str) -> int:
    return int(np.asarray(raw, dtype=np.int64).reshape(-1)[0])


def _execute(args: argparse.Namespace) -> int:
    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing authority mat: {mat_path}")

    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    raw = loadmat(str(mat_path), simplify_cells=True)

    for key in ("entry1_Nr", "entry1_Nc", "entry1_Sc", "entry1_Nd", "entry1_C"):
        if key not in raw:
            raise KeyError(
                f"{mat_path} missing {key} — run patch_entry1_authority_to_pre_entry10_mat.m"
            )

    pairs = (
        ("Nr", "entry1_Nr"),
        ("Nc", "entry1_Nc"),
        ("Sc", "entry1_Sc"),
        ("Nd", "entry1_Nd"),
        ("C", "entry1_C"),
    )
    print(f"[FSL backward Entry 1] PKL post={pkl_path}", file=sys.stderr)
    print(f"[FSL backward Entry 1] MAT authority={mat_path}", file=sys.stderr)
    print(f"[FSL backward Entry 1] lane={blob.get('validation_lane')}", file=sys.stderr)

    for py_key, mat_key in pairs:
        py_v = int(blob[py_key]) if py_key != "C" else float(blob[py_key])
        mat_v = _scalar_int(raw[mat_key], mat_key)
        if py_key == "C":
            mat_v = float(np.asarray(raw[mat_key], dtype=np.float64).reshape(-1)[0])
        if py_v != mat_v:
            raise AssertionError(f"{py_key}: py={py_v} mat={mat_v}")

    if "C" in raw:
        c_legacy = float(np.asarray(raw["C"], dtype=np.float64).reshape(-1)[0])
        if float(blob["C"]) != c_legacy:
            raise AssertionError(f"C legacy scalar: py={blob['C']} mat={c_legacy}")

    print("OK: entry1_Nr/Nc/Sc/Nd/C parity (FSL backward Entry 1)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 1 constants compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = _default_post_pkl()
    if args.mat is None:
        args.mat = _default_authority_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "FSL backward — Entry 1: compare Python snippet constants vs MATLAB authority.\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out, tee_err = sys.stdout, sys.stderr
        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = tee_out, tee_err


if __name__ == "__main__":
    raise SystemExit(main())
