#!/usr/bin/env python3
"""OPTIM1FULL Product B — compare post–NR ``MDP`` vs ``DEMAtariIII_optim1full_MDP_post_nr.mat``.

**Report:** ``matlab_custom/optim1full_compare_post_nr_output.txt``
"""
from __future__ import annotations

import argparse
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "optim1full_compare_post_nr_output.txt"


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
        assert_optim1full_mdp_pre_pairing_equal,
        load_mdp_from_mat,
    )

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    for label, path in (("PKL", pkl_path), ("MAT", mat_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL post-NR compare] missing {label}: {path}", file=sys.stderr)
            return 2

    with pkl_path.open("rb") as f:
        payload = pickle.load(f)
    mdp_py = payload["mdp"]
    nm = int(payload.get("nm", len(mdp_py)))

    mdp_mat = load_mdp_from_mat(mat_path, "MDP_post_nr")
    nm_mat = len(mdp_mat)
    if nm != nm_mat:
        raise AssertionError(f"Nm mismatch: python={nm} matlab={nm_mat}")

    print(f"[OPTIM1FULL post-NR compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL post-NR compare] MAT={mat_path}", file=sys.stderr)
    assert_optim1full_mdp_pre_pairing_equal(mdp_py, mdp_mat, nm)
    print("[OPTIM1FULL post-NR compare] PASS", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat, optim1full_post_nr_pkl

    p = argparse.ArgumentParser(description="OPTIM1FULL Product B post-NR MDP compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = optim1full_post_nr_pkl()
    if args.mat is None:
        args.mat = optim1full_mdp_post_nr_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8") as rf:
        tee = _TeeIO(sys.stdout, rf)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = tee  # type: ignore[assignment]
        sys.stderr = tee  # type: ignore[assignment]
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = old_out, old_err


if __name__ == "__main__":
    raise SystemExit(main())
