#!/usr/bin/env python3
"""OPTIM1FULL preamble bisect — classify MDP_pre drift (not sign-off).

Compares live preamble pickles vs ledger ``MDP_pre`` authority with generative-process
attach stripped (``GA``/``GB``/``GU``/``GD``/``ID``/``chi`` on ``MDP[0]``), matching
state before MATLAB ``entry12_dem_attach_generative_process_``.

See ``OPTIM1.md`` § **11.7.4** Phase A; ``optim1full_parity_contract.py``.
"""
from __future__ import annotations

import argparse
import copy
import pickle
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_GP_ATTACH_KEYS = ("GA", "GB", "GU", "GD", "ID", "chi")


def _strip_gp_attach(mdp: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = copy.deepcopy(mdp)
    if out:
        for key in _GP_ATTACH_KEYS:
            out[0].pop(key, None)
    return out


def _compare(label: str, mdp_py: list[dict[str, Any]], mdp_mat: list[dict[str, Any]]) -> str:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    nm = len(mdp_py)
    if nm != len(mdp_mat):
        return f"{label}: Nm mismatch py={nm} mat={len(mdp_mat)}"
    try:
        _assert_mdp_full_equal(mdp_py, mdp_mat, nm)
        return f"{label}: PASS"
    except AssertionError as exc:
        return f"{label}: FAIL — {exc}"


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mdp_pre_active_inference_mat,
        optim1full_mdp_pre_pkl,
    )
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat

    p = argparse.ArgumentParser(description="OPTIM1FULL preamble bisect (classification)")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)

    pkl_path = args.pkl or optim1full_mdp_pre_pkl()
    mat_path = args.mat or optim1full_mdp_pre_active_inference_mat()
    for label, path in (("PKL", pkl_path), ("MAT", mat_path)):
        if not path.is_file():
            print(f"[preamble bisect] missing {label}: {path}", file=sys.stderr)
            return 2

    with pkl_path.open("rb") as f:
        payload = pickle.load(f)
    mdp_py = payload["mdp"]
    stop_after = str(payload.get("stop_after", payload.get("boundary", "?")))

    mdp_mat_full = load_mdp_from_mat(mat_path, "MDP_pre_active_inference")
    mdp_mat_pre_attach = _strip_gp_attach(mdp_mat_full)

    print(f"[preamble bisect] PKL={pkl_path} stop_after={stop_after}", file=sys.stderr)
    print(f"[preamble bisect] MAT={mat_path}", file=sys.stderr)

    r_pre = _compare("pre-attach MDP", mdp_py, mdp_mat_pre_attach)
    r_full = _compare("full MDP_pre (with attach)", mdp_py, mdp_mat_full)
    print(r_pre)
    print(r_full)

    if r_pre.startswith("pre-attach MDP: PASS"):
        return 0 if r_full.startswith("full MDP_pre") and "PASS" in r_full else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
