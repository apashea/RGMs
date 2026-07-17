#!/usr/bin/env python3
"""OPTIM1FULL Product B — compare live Entries **1–11** ``MDP_pre`` vs authority (pairing audit).

Gate: ``optim1full_parity_gate.py --pairing-audit``. Integration sign-off after **4a**:
``optim1full_compare_post_nr_pkl_to_mat.py``. See ``optim1full_parity_contract.py``.

**Report:** ``matlab_custom/optim1full_compare_mdp_pre_output.txt``
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
    return _REPO / "matlab_custom" / "optim1full_compare_mdp_pre_output.txt"


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
            print(f"[OPTIM1FULL MDP_pre compare] missing {label}: {path}", file=sys.stderr)
            return 2

    with pkl_path.open("rb") as f:
        payload = pickle.load(f)
    mdp_py = payload["mdp"]
    nm = int(payload.get("nm", len(mdp_py)))

    mdp_mat = load_mdp_from_mat(mat_path, "MDP_pre_active_inference")
    nm_mat = len(mdp_mat)
    if nm != nm_mat:
        raise AssertionError(f"Nm mismatch: python={nm} matlab={nm_mat}")

    print(f"[OPTIM1FULL MDP_pre compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL MDP_pre compare] MAT={mat_path}", file=sys.stderr)
    assert_optim1full_mdp_pre_pairing_equal(mdp_py, mdp_mat, nm)
    print("[OPTIM1FULL MDP_pre compare] PASS", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mdp_pre_active_inference_mat,
        optim1full_mdp_pre_pkl,
    )

    p = argparse.ArgumentParser(description="OPTIM1FULL Product B MDP_pre compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = optim1full_mdp_pre_pkl()
    if args.mat is None:
        args.mat = optim1full_mdp_pre_active_inference_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "OPTIM1FULL — compare live Entries 1–11 ``MDP_pre`` vs authority.\n\n"
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
