#!/usr/bin/env python3
"""OPTIM1FULL — verify the per-game NR authority trace is complete and loadable.

Run this ONCE, immediately after producing the trace with::

    python tests/demo1/optim1full/optim1full_capture_rand_ledger.py --nr-authority-trace

Its job is to guarantee — before any debugging relies on the dumps — that the trace is
reusable and correct, so we never discover mid-debug that a dump is missing/unloadable and
have to re-run the (slow) MATLAB capture. It checks, for all 32 games:

  1. RDP/PDP/MDP files exist and load through the **exact** code paths the localizer uses
     (``load_entry12_rdp_mat_nested_for_tag`` for RDP, ``_load_matlab_pdp`` for PDP).
  2. Each game's ledger segment (id/start/k) in the NR authority manifest matches the
     global ``optim1full_rand_manifest.json`` ``nr_game_%02d`` segment.
  3. Game 32's ``MDP_post_game`` ``a``/``b`` equal the frozen authority
     ``DEMAtariIII_optim1full_MDP_post_nr.mat`` (by construction identical; a corruption
     guard on the dump).

Exit 0 = trace is trustworthy; non-zero = re-capture needed (message says why).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_NR_RDP_DTYPE_TAG = "rgms_atari_optim1full_nr_g01"
_NR = 32


def _mdp_cells(path: Path, var: str) -> list[dict[str, Any]]:
    from scipy.io import loadmat

    raw = loadmat(str(path), simplify_cells=True)
    if var not in raw:
        keys = sorted(k for k in raw if not k.startswith("__"))
        raise KeyError(f"{path.name}: expected variable {var!r}, got {keys}")
    mdp = raw[var]
    if isinstance(mdp, dict):
        return [mdp]
    return list(mdp)


def _ab_arrays(mdp_n: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    import numpy as np

    def _cells(field: Any) -> list[Any]:
        if field is None:
            return []
        if isinstance(field, (list, tuple)):
            return list(field)
        arr = np.asarray(field)
        if arr.dtype == object:
            return list(arr.ravel())
        return [arr]

    return _cells(mdp_n.get("a")), _cells(mdp_n.get("b"))


def _assert_mdp_ab_equal(m_game: list[dict[str, Any]], m_post: list[dict[str, Any]]) -> None:
    import numpy as np

    if len(m_game) != len(m_post):
        raise AssertionError(f"MDP length game32={len(m_game)} != post_nr={len(m_post)}")
    for n in range(len(m_game)):
        ga, gb = _ab_arrays(m_game[n])
        pa, pb = _ab_arrays(m_post[n])
        if len(ga) != len(pa):
            raise AssertionError(f"MDP[{n}] len(a) game32={len(ga)} != post_nr={len(pa)}")
        if len(gb) != len(pb):
            raise AssertionError(f"MDP[{n}] len(b) game32={len(gb)} != post_nr={len(pb)}")
        for g in range(len(ga)):
            if not np.array_equal(np.asarray(ga[g]), np.asarray(pa[g])):
                raise AssertionError(f"MDP[{n}].a[{g}] game32 != post_nr")
        for f in range(len(gb)):
            if not np.array_equal(np.asarray(gb[f]), np.asarray(pb[f])):
                raise AssertionError(f"MDP[{n}].b[{f}] game32 != post_nr")


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mdp_post_nr_mat,
        optim1full_nr_authority_manifest_json,
        optim1full_nr_authority_mdp_mat,
        optim1full_nr_authority_pdp_mat,
        optim1full_nr_authority_rdp_mat,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import load_optim1full_rand_manifest
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
        load_entry12_rdp_mat_nested_for_tag,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp

    man_path = optim1full_nr_authority_manifest_json()
    if not man_path.is_file():
        print(
            f"[verify_nr_authority] FAIL: manifest missing ({man_path}). "
            "Run optim1full_capture_rand_ledger.py --nr-authority-trace first.",
            file=sys.stderr,
            flush=True,
        )
        return 2
    nr_man = json.loads(man_path.read_text(encoding="utf-8"))
    games_meta = nr_man.get("games", [])
    if len(games_meta) != _NR:
        print(
            f"[verify_nr_authority] FAIL: manifest lists {len(games_meta)} games, expected {_NR}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    global_manifest = load_optim1full_rand_manifest()

    # 1 + 2: per-game load-path exercise + segment cross-check.
    for i in range(1, _NR + 1):
        rdp_path = optim1full_nr_authority_rdp_mat(i)
        pdp_path = optim1full_nr_authority_pdp_mat(i)
        mdp_path = optim1full_nr_authority_mdp_mat(i)
        for pth in (rdp_path, pdp_path, mdp_path):
            if not pth.is_file():
                print(f"[verify_nr_authority] FAIL: game {i:02d} missing {pth}", file=sys.stderr)
                return 1

        # Exercise the localizer's real RDP load path.
        nested = load_entry12_rdp_mat_nested_for_tag(_NR_RDP_DTYPE_TAG, rdp_path)
        if not isinstance(nested, dict) or "MDP" not in nested:
            print(
                f"[verify_nr_authority] FAIL: game {i:02d} RDP nested load malformed",
                file=sys.stderr,
            )
            return 1
        # Exercise the localizer's real PDP load path.
        pdp = _load_matlab_pdp(pdp_path)
        if not isinstance(pdp, dict) or "Q" not in pdp:
            print(
                f"[verify_nr_authority] FAIL: game {i:02d} PDP load malformed (no Q)",
                file=sys.stderr,
            )
            return 1

        seg = global_manifest.segment(f"nr_game_{i:02d}")
        gm = games_meta[i - 1]
        gseg = gm.get("segment", {})
        if int(gseg.get("start", -1)) != int(seg.start) or int(gseg.get("k", -1)) != int(seg.k):
            print(
                f"[verify_nr_authority] FAIL: game {i:02d} segment mismatch "
                f"trace(start={gseg.get('start')},k={gseg.get('k')}) vs "
                f"global(start={seg.start},k={seg.k})",
                file=sys.stderr,
            )
            return 1

    # 3: game 32 MDP a/b == frozen MDP_post_nr authority.
    post_nr_path = optim1full_mdp_post_nr_mat()
    if not post_nr_path.is_file():
        print(
            f"[verify_nr_authority] FAIL: authority {post_nr_path} missing",
            file=sys.stderr,
        )
        return 1
    try:
        m_game32 = _mdp_cells(optim1full_nr_authority_mdp_mat(_NR), "MDP_post_game")
        m_post = _mdp_cells(post_nr_path, "MDP_post_nr")
        _assert_mdp_ab_equal(m_game32, m_post)
    except (AssertionError, KeyError) as exc:
        print(f"[verify_nr_authority] FAIL: game32 vs MDP_post_nr — {exc}", file=sys.stderr)
        return 1

    print(
        f"[verify_nr_authority] PASS: {_NR} games load via localizer paths; segments match "
        "global manifest; game32 a/b == MDP_post_nr. Trace is trustworthy for optim localization.",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
