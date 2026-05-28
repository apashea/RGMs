#!/usr/bin/env python3
"""Compare Python replay trace vs MATLAB dump trace (paired RNG site-class)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_atari_calls import entry12_fixtures_dir, entry12_resolve_run_tag


def _load_trace(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "trace" in raw:
        tr = raw["trace"]
        if isinstance(tr, list):
            return tr
    raise ValueError(f"unrecognized trace schema in {path}")


def main() -> int:
    tag = entry12_resolve_run_tag()
    fix = entry12_fixtures_dir()
    py_path = fix / f"entry12_sample_trace_{tag}.json"
    mat_path = fix / f"entry12_sample_trace_{tag}_mat.json"
    if not py_path.is_file():
        print(f"MISSING python trace: {py_path}", file=sys.stderr)
        return 2
    if not mat_path.is_file():
        print(f"MISSING matlab trace: {mat_path}", file=sys.stderr)
        return 2

    py_raw = json.loads(py_path.read_text(encoding="utf-8"))
    py_trace = _load_trace(py_path)
    mat_trace = _load_trace(mat_path)

    print(f"tag={tag!r} py_calls={len(py_trace)} mat_calls={len(mat_trace)}")
    if len(py_trace) != len(mat_trace):
        print(f"CALL_COUNT_MISMATCH py={len(py_trace)} mat={len(mat_trace)}", file=sys.stderr)
        n = min(len(py_trace), len(mat_trace))
    else:
        n = len(py_trace)
        print("call_count_match ok")

    first_pat = None
    first_draws = None
    first_py_parity = None
    for seq in range(n):
        pr = py_trace[seq]
        mr = mat_trace[seq]
        diffs = []
        for key in ("site", "pattern", "k_mask", "out", "t_gen", "depth"):
            pv, mv = pr.get(key), mr.get(key)
            if pv != mv:
                diffs.append(f"{key} py={pv!r} mat={mv!r}")
        py_nd = int(pr.get("n_draws", -1))
        mat_nd = int(mr.get("n_draws", -1))
        mat_py_p = int(mr.get("n_draws_py_parity", mat_nd))
        if py_nd != mat_py_p:
            diffs.append(f"n_draws_py_parity py={py_nd} mat_py_parity={mat_py_p}")
        if pr.get("pattern") != mr.get("pattern") and first_pat is None:
            first_pat = (seq, pr, mr, diffs)
        if py_nd != mat_py_p and first_draws is None:
            first_draws = (seq, pr, mr, diffs)
        if py_nd != int(pr.get("expected_n_draws", py_nd)) and first_py_parity is None:
            first_py_parity = (seq, pr)

    if first_pat:
        seq, pr, mr, diffs = first_pat
        print("\nFIRST pattern mismatch at seq", seq)
        for d in diffs:
            print(" ", d)
        print(" py:", {k: pr.get(k) for k in ("site", "pattern", "n_draws", "k_mask", "out", "t_gen", "depth", "dtype")})
        print(" mat:", {k: mr.get(k) for k in ("site", "pattern", "n_draws", "n_draws_py_parity", "k_mask", "out", "t_gen", "depth", "dtype")})
    else:
        print("pattern: all match through", n)

    if first_draws:
        seq, pr, mr, diffs = first_draws
        print("\nFIRST n_draws (py replay vs mat py-parity) mismatch at seq", seq)
        for d in diffs:
            print(" ", d)
    else:
        print("n_draws_py_parity: all match through", n)

    # Policy row at first multi Pu (from audit summary if present)
    if isinstance(py_raw, dict):
        fp = py_raw.get("trace_summary", {}).get("first_policy_uniform_multi")
        if fp and "seq" in fp:
            s = int(fp["seq"])
            if s < n:
                print("\npolicy anchor seq", s)
                print(" py", {k: py_trace[s].get(k) for k in ("pattern", "n_draws", "out", "pu_len", "t_gen")})
                print(" mat", {k: mat_trace[s].get(k) for k in ("pattern", "n_draws", "n_draws_py_parity", "out", "pu_len", "t_gen", "dtype")})

    if first_pat or first_draws or len(py_trace) != len(mat_trace):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
