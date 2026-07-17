#!/usr/bin/env python3
"""OPTIM1FULL — MI-429: compare Python ``spm_RDP_MI`` + ``np`` vs MATLAB authority.

**Authority:** ``DEMAtariIII_optim1full_MDP_post_mi429.mat`` + ``DEMAtariIII_optim1full_np_mi429.mat``.
**Python:** ``DEMAtariIII_optim1full_mi429_post.pkl``.
**Report:** ``matlab_custom/optim1full_compare_mi429_output.txt``

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
    return _REPO / "matlab_custom" / "optim1full_compare_mi429_output.txt"


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
    from tests.demo1.optim1full.optim1full_mi_boundary import (
        load_mdp_from_mat,
        load_np_mi429_from_mat,
    )
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pkl_path = args.pkl.resolve()
    mat_mdp_path = args.mat_mdp.resolve()
    mat_np_path = args.mat_np.resolve()
    for label, path in (
        ("PKL", pkl_path),
        ("MDP mat", mat_mdp_path),
        ("np mat", mat_np_path),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"missing {label}: {path}")

    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    py_mdp = blob["mdp"]
    py_np = int(blob["np"])
    if not isinstance(py_mdp, list):
        raise TypeError(f"mdp must be list in {pkl_path}")

    mat_mdp = load_mdp_from_mat(mat_mdp_path, "MDP_post_mi429")
    mat_np = load_np_mi429_from_mat(mat_np_path)

    print(f"[OPTIM1FULL MI-429] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL MI-429] MAT MDP={mat_mdp_path}", file=sys.stderr)
    print(f"[OPTIM1FULL MI-429] MAT np={mat_np_path}", file=sys.stderr)
    print(
        f"[OPTIM1FULL MI-429] levels py={len(py_mdp)} mat={len(mat_mdp)}",
        file=sys.stderr,
    )
    _assert_mdp_full_equal(py_mdp, mat_mdp, k=10)
    if py_np != mat_np:
        raise AssertionError(f"np mismatch: py={py_np} mat={mat_np}")
    print(f"OK: MDP + np parity (OPTIM1FULL MI-429, np={py_np})", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mi429_post_pkl,
        optim1full_mdp_post_mi429_mat,
        optim1full_np_mi429_mat,
    )

    p = argparse.ArgumentParser(description="OPTIM1FULL MI-429 MDP+np compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat-mdp", type=Path, default=None)
    p.add_argument("--mat-np", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        raw = str(os.getenv("RGMS_OPTIM1FULL_MI429_POST_PKL_PATH", "")).strip()
        args.pkl = (
            Path(raw).expanduser().resolve()
            if raw
            else optim1full_mi429_post_pkl()
        )
    if args.mat_mdp is None:
        raw = str(os.getenv("RGMS_OPTIM1FULL_MI429_AUTHORITY_MDP_MAT_PATH", "")).strip()
        args.mat_mdp = (
            Path(raw).expanduser().resolve()
            if raw
            else optim1full_mdp_post_mi429_mat()
        )
    if args.mat_np is None:
        raw = str(os.getenv("RGMS_OPTIM1FULL_MI429_AUTHORITY_NP_MAT_PATH", "")).strip()
        args.mat_np = (
            Path(raw).expanduser().resolve()
            if raw
            else optim1full_np_mi429_mat()
        )

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "OPTIM1FULL — MI-429: compare Python ``spm_RDP_MI`` + ``np`` vs MATLAB authority.\n\n"
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
