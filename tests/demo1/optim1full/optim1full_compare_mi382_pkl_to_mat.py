#!/usr/bin/env python3
"""OPTIM1FULL — MI-382: compare Python ``spm_RDP_MI`` post vs MATLAB authority.

**Authority:** ``DEMAtariIII_optim1full_MDP_post_mi382.mat`` variable ``MDP_post_mi382``.
**Python:** ``DEMAtariIII_optim1full_mi382_post.pkl`` field ``mdp``.
**Report:** ``matlab_custom/optim1full_compare_mi382_output.txt``

See ``OPTIM1.md`` § **11.6**.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "optim1full_compare_mi382_output.txt"


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


def _execute(args: argparse.Namespace) -> int:
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(
            f"missing authority mat: {mat_path}\n"
            "Run MATLAB capture_optim1full_mi_boundaries first."
        )

    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    py_mdp = blob["mdp"]
    if not isinstance(py_mdp, list):
        raise TypeError(f"mdp must be list in {pkl_path}")

    mat_mdp = load_mdp_from_mat(mat_path, "MDP_post_mi382")
    print(f"[OPTIM1FULL MI-382] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL MI-382] MAT={mat_path}", file=sys.stderr)
    print(
        f"[OPTIM1FULL MI-382] levels py={len(py_mdp)} mat={len(mat_mdp)}",
        file=sys.stderr,
    )
    _assert_mdp_full_equal(py_mdp, mat_mdp, k=10)
    print("OK: MDP parity (OPTIM1FULL MI-382)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mi382_post_pkl,
        optim1full_mdp_post_mi382_mat,
    )

    p = argparse.ArgumentParser(description="OPTIM1FULL MI-382 MDP compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        raw = str(os.getenv("RGMS_OPTIM1FULL_MI382_POST_PKL_PATH", "")).strip()
        args.pkl = (
            Path(raw).expanduser().resolve()
            if raw
            else optim1full_mi382_post_pkl()
        )
    if args.mat is None:
        raw = str(os.getenv("RGMS_OPTIM1FULL_MI382_AUTHORITY_MAT_PATH", "")).strip()
        args.mat = (
            Path(raw).expanduser().resolve()
            if raw
            else optim1full_mdp_post_mi382_mat()
        )

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "OPTIM1FULL — MI-382: compare Python ``spm_RDP_MI`` vs "
        "``MDP_post_mi382`` authority.\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out = sys.stdout
        tee_err = sys.stderr
        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout = tee_out
            sys.stderr = tee_err


if __name__ == "__main__":
    raise SystemExit(main())
