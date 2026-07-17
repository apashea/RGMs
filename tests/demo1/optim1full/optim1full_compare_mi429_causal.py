#!/usr/bin/env python3
"""OPTIM1FULL — MI-429 causal fix-queue gate (OPTIM1.md § 11.5.1)."""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "optim1full_compare_mi429_causal_output.txt"


def _execute(args: argparse.Namespace) -> int:
    from tests.demo1.optim1full.optim1full_mi_causal import run_causal_gate

    step, msg = run_causal_gate(
        pre_mat=args.pre.resolve(),
        pre_var="MDP_pre_mi429",
        causal_mat=args.causal.resolve(),
        causal_var="mi429_causal",
        site_label="MI-429",
    )
    print(msg, file=sys.stderr)
    if step is not None:
        print(f"FIRST_CAUSAL_RED={step}", file=sys.stderr)
        return 1
    print("OK: MI-429 causal gate", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mi429_causal_mat,
        optim1full_mdp_pre_mi429_mat,
    )

    p = argparse.ArgumentParser(description="OPTIM1FULL MI-429 causal gate")
    p.add_argument("--pre", type=Path, default=None)
    p.add_argument("--causal", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pre is None:
        args.pre = optim1full_mdp_pre_mi429_mat()
    if args.causal is None:
        args.causal = optim1full_mi429_causal_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    from tests.demo1.optim1full.optim1full_compare_mi382_pkl_to_mat import _TeeIO

    header = (
        "OPTIM1FULL — MI-429 causal gate (``spm_RDP_MI`` steps B_ambig..R).\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_err = sys.stderr
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stderr = tee_err


if __name__ == "__main__":
    raise SystemExit(main())
