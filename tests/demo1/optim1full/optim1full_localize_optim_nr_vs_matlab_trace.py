#!/usr/bin/env python3
"""OPTIM1FULL — localize the first NR game where optimized VB diverges from MATLAB.

Purpose
-------
The integrated 4a gate (``--full-replay-integration --vb-dev-optim``) reds post-NR at
``MDP_post_nr.a`` (accumulated Dirichlet counts). The fidelity control passes against the
same MATLAB authority, so the divergence is **optim-specific** and enters through the VB
output ``PDP.Q.O`` of some NR game (the only lane-varying input to the otherwise-fidelity
merge/basin assembly). This script pins **which** game.

How
---
For each of the 32 NR games it feeds the **genuine MATLAB per-game VB input ``RDP``**
(from the NR authority trace) into ``spm_MDP_VB_XXX_optim`` with the **exact MATLAB draw
segment** replayed (``spm_mdp_vb_xxx_with_ledger_segment_reuse``, ``vb_lane="optim"``),
then compares the optim ``PDP`` against the **genuine MATLAB ``PDP``** for that game using
the established W2 comparator (``_compare_pair`` + MATLAB-layout alignment).

Because every game's ``RDP`` is the frozen MATLAB input, each game is tested in isolation:
this needs **no** accumulating NR loop and **no** Python fidelity rerun. Up to the first
diverging game the optim and MATLAB accumulated states are identical, so the first PDP red
here is exactly the game that produces the integrated ``a`` red.

Authority
---------
Requires the per-game MATLAB authority trace produced once by::

    conda activate rgms
    python tests/demo1/optim1full/optim1full_capture_rand_ledger.py --nr-authority-trace

See ``OPTIM1FULL.md`` § "Per-game NR authority trace". Verify it with
``optim1full_verify_nr_authority_trace.py`` before relying on it.

Usage
-----
    conda activate rgms
    # scan all games, stop at first divergence:
    python tests/demo1/optim1full/optim1full_localize_optim_nr_vs_matlab_trace.py
    # single game (fast edit loop while fixing spm_MDP_VB_XXX_optim):
    python tests/demo1/optim1full/optim1full_localize_optim_nr_vs_matlab_trace.py --game 7
    # list every diverging game (do not stop at first):
    python tests/demo1/optim1full/optim1full_localize_optim_nr_vs_matlab_trace.py --report-only
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# NR-game RDPs share the call-2 generative-process dtype layout; this tag selects the
# correct loadmat dtype restoration in ``mat_nested_rdp_from_loadmat`` for all 32 files.
_NR_RDP_DTYPE_TAG = "rgms_atari_optim1full_nr_g01"

# VB computation/write order for the top-level PDP fields, used ONLY to order the
# per-field divergence report so the FIRST reported red is the earliest-computed field
# (not the alphabetical accident where downstream aggregate ``F`` precedes the sampled
# trajectory ``O``/``s``/``X`` and the posteriors ``Q`` that causally feed the merged
# ``a``). This is a reporting aid local to the localizer; it does NOT change the shared
# comparator's pass/fail. Keys not listed sort after known static inputs, before ``F``.
_PDP_FIELD_ORDER: tuple[str, ...] = (
    # static / model inputs — expected green (divergence here => upstream, not the kernel)
    "A", "B", "C", "D", "E", "G", "H", "L", "U", "T", "id", "sA", "sB", "sC", "ss", "MDP",
    # sampled trajectory & realized outcomes — earliest stochastic outputs, causal to a
    "s", "o", "O", "u",
    # posteriors over states / paths (Q.O is the direct driver of the merged a)
    "P", "R", "X", "Y", "Z", "Q",
    # bookkeeping
    "i", "j", "n", "v", "w",
    # free energy — DOWNSTREAM AGGREGATE (never the root; last on purpose)
    "F",
)
# Fields whose divergence is causally upstream of the integrated post-NR ``a`` red.
_CAUSAL_TO_A: frozenset[str] = frozenset({"O", "o", "s", "X", "u", "Q"})


def _field_rank(key: str) -> tuple[int, str]:
    """Sort key placing PDP fields in VB computation order (unknown => before ``F``)."""
    try:
        return (_PDP_FIELD_ORDER.index(key), key)
    except ValueError:
        # Unknown field: after static inputs, before the aggregate F block.
        return (_PDP_FIELD_ORDER.index("Q"), key)


def _leaf_maxabs(py_leaf: Any, mat_leaf: Any) -> float | None:
    """Best-effort max-abs elementwise diff for aligned array leaves (else ``None``)."""
    import numpy as np

    from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import _densify_sparse_leaves

    try:
        a = np.asarray(_densify_sparse_leaves(py_leaf), dtype=np.float64).ravel()
        b = np.asarray(_densify_sparse_leaves(mat_leaf), dtype=np.float64).ravel()
    except Exception:
        return None
    if a.size == 0 or a.size != b.size:
        return None
    return float(np.max(np.abs(a - b)))


def _diagnose_divergence(py_cmp: Any, mat_cmp: Any) -> list[tuple[str, str, float | None, bool]]:
    """Enumerate EVERY diverging top-level PDP field (descending one level into ``Q``).

    Reuses the shared ``_assert_nested_rdp_equal`` per field (identical semantics to the
    gate) but iterates fields ourselves so we see the complete set of reds in VB
    computation order rather than only the alphabetical-first leaf. Returns a list of
    ``(path, first_message, maxabs_or_None, is_causal_to_a)`` sorted by compute order.
    """
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    if not (isinstance(py_cmp, dict) and isinstance(mat_cmp, dict)):
        return [("PDP", "top-level objects are not both dicts", None, False)]

    reds: list[tuple[str, str, float | None, bool]] = []
    keys = sorted(set(py_cmp) | set(mat_cmp), key=_field_rank)
    for k in keys:
        path = f"PDP.{k}"
        if k not in py_cmp or k not in mat_cmp:
            reds.append((path, f"present py={k in py_cmp} mat={k in mat_cmp}", None, k in _CAUSAL_TO_A))
            continue
        try:
            _assert_nested_rdp_equal(py_cmp[k], mat_cmp[k], path)
        except AssertionError as exc:
            mx = _leaf_maxabs(py_cmp[k], mat_cmp[k])
            reds.append((path, str(exc), mx, k in _CAUSAL_TO_A))
            # For the posterior dict Q, also break out which subfield(s) diverge, since
            # Q.O is the direct driver of the merged a and Q.E is a known packing hotspot.
            if k == "Q" and isinstance(py_cmp[k], dict) and isinstance(mat_cmp[k], dict):
                q_py, q_mat = py_cmp[k], mat_cmp[k]
                for qk in sorted(set(q_py) | set(q_mat)):
                    qpath = f"PDP.Q.{qk}"
                    if qk not in q_py or qk not in q_mat:
                        reds.append((qpath, f"present py={qk in q_py} mat={qk in q_mat}", None, qk == "O"))
                        continue
                    try:
                        _assert_nested_rdp_equal(q_py[qk], q_mat[qk], qpath)
                    except AssertionError as qexc:
                        reds.append(
                            (qpath, str(qexc), _leaf_maxabs(q_py[qk], q_mat[qk]), qk == "O")
                        )
    return reds


def _compute_game_pdps(
    game: int,
    buf: Any,
    manifest: Any,
    *,
    vb_lane: str,
) -> tuple[Any, Any, Any]:
    """Run ``vb_lane`` VB on the MATLAB game-``game`` RDP + ledger segment; return
    ``(py_cmp, mat_cmp, seg)`` where ``py_cmp`` is MATLAB-layout-aligned to ``mat_cmp``.

    Single source of truth for the localizer's optim VB call (used by both the field
    comparison and the per-timestep trajectory diagnostic), so both exercise the exact
    same kernel invocation, RDP load, and draw replay.
    """
    import numpy as np

    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_nr_authority_pdp_mat,
        optim1full_nr_authority_rdp_mat,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        optim1full_nr_game_segment_id,
        spm_mdp_vb_xxx_with_ledger_segment_reuse,
    )
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
        load_entry12_rdp_mat_nested_for_tag,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp

    rdp_path = optim1full_nr_authority_rdp_mat(game)
    pdp_path = optim1full_nr_authority_pdp_mat(game)
    if not rdp_path.is_file():
        raise FileNotFoundError(f"game {game}: missing MATLAB RDP authority {rdp_path}")
    if not pdp_path.is_file():
        raise FileNotFoundError(f"game {game}: missing MATLAB PDP authority {pdp_path}")

    seg = manifest.segment(optim1full_nr_game_segment_id(game))
    nested_rdp = load_entry12_rdp_mat_nested_for_tag(_NR_RDP_DTYPE_TAG, rdp_path)

    pdp_optim = spm_mdp_vb_xxx_with_ledger_segment_reuse(
        nested_rdp,
        np.asarray(buf, dtype=np.float64).ravel(),
        start=int(seg.start),
        k=int(seg.k),
        vb_lane=vb_lane,
    )
    pdp_matlab = _load_matlab_pdp(pdp_path)

    if isinstance(pdp_optim, dict) and isinstance(pdp_matlab, dict):
        py_cmp = entry12_align_mdp_to_mat_workspace(copy.deepcopy(pdp_optim), pdp_matlab)
        mat_cmp = entry12_mat_pdp_for_value_assert(pdp_matlab)
    else:
        py_cmp, mat_cmp = pdp_optim, pdp_matlab
    return py_cmp, mat_cmp, seg


def _first_col_divergence(py_leaf: Any, mat_leaf: Any) -> tuple[int, Any, Any] | None:
    """First column (last axis = MATLAB time) where two arrays differ; ``None`` if equal.

    Returns ``(t, py_col, mat_col)`` with ``t`` 0-based. Handles shape/orientation
    mismatch by raveling to a common 2-D ``(rows, T)`` when the last-axis lengths agree.
    """
    import numpy as np

    from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import _densify_sparse_leaves

    try:
        a = np.atleast_2d(np.asarray(_densify_sparse_leaves(py_leaf), dtype=np.float64))
        b = np.atleast_2d(np.asarray(_densify_sparse_leaves(mat_leaf), dtype=np.float64))
    except Exception:
        return None
    if a.shape != b.shape:
        # Fall back to raw ravel compare if shapes disagree (report as t=-1).
        ar, br = a.ravel(), b.ravel()
        n = min(ar.size, br.size)
        for i in range(n):
            if not np.isclose(ar[i], br[i], rtol=0.0, atol=1e-9):
                return (-1, ar[i], br[i])
        if ar.size != br.size:
            return (-1, ar.size, br.size)
        return None
    T = a.shape[-1]
    for t in range(T):
        ca = a[..., t].ravel()
        cb = b[..., t].ravel()
        if not np.allclose(ca, cb, rtol=0.0, atol=1e-9):
            return (t, ca, cb)
    return None


def _trajectory_diff(game: int, buf: Any, manifest: Any, *, vb_lane: str = "optim") -> int:
    """Report the first timestep where optim's sampled trajectory diverges from MATLAB.

    Pins the sampling site of the draw-consumption desync in time. Compares the true
    sampled state ``s``, outcome ``o``, and action ``u`` (the fields that feed the
    accumulated ``a`` through the generative process) column-by-column.
    """
    import numpy as np

    py_cmp, mat_cmp, seg = _compute_game_pdps(game, buf, manifest, vb_lane=vb_lane)
    if not (isinstance(py_cmp, dict) and isinstance(mat_cmp, dict)):
        print(f"[traj_diff] game {game:02d}: PDPs not both dicts; cannot diff", file=sys.stderr)
        return 2

    print(
        f"[traj_diff] game {game:02d} ({vb_lane}) k={seg.k}: first per-timestep divergence "
        "of sampled trajectory (0-based t; last axis = MATLAB time):",
        file=sys.stderr,
        flush=True,
    )
    any_div = False
    for fld in ("s", "o", "u", "X"):
        if fld not in py_cmp or fld not in mat_cmp:
            print(f"    {fld}: present py={fld in py_cmp} mat={fld in mat_cmp}", file=sys.stderr)
            continue
        res = _first_col_divergence(py_cmp[fld], mat_cmp[fld])
        if res is None:
            print(f"    {fld}: MATCH (all timesteps equal)", file=sys.stderr, flush=True)
            continue
        any_div = True
        t, pc, mc = res
        loc = "raw-ravel(shape mismatch)" if t < 0 else f"t={t}"
        print(
            f"    {fld}: DIVERGE at {loc}\n"
            f"        optim = {np.array2string(np.asarray(pc), threshold=40)}\n"
            f"        matlab= {np.array2string(np.asarray(mc), threshold=40)}",
            file=sys.stderr,
            flush=True,
        )
    if not any_div:
        print(
            f"[traj_diff] game {game:02d}: s/o/u/X all match per timestep "
            "(divergence is elsewhere — inspect Q/F).",
            file=sys.stderr,
            flush=True,
        )
    return 0


def _sample_trace(game: int, buf: Any, manifest: Any, *, vb_lane: str) -> int:
    """Trace every ``_spm_sample`` call (arg summary + result) for one game/lane.

    Non-invasive: wraps the lane's imported ``_spm_sample`` (no source edits). Writes
    ``logs/optim1full_sample_trace_g{game}_{lane}.txt`` with one line per call::

        <call#> k=<size> sum=<arg sum> amax=<1-based argmax> bool=<0/1> -> <result>

    Diff the optim vs fidelity files: the first line whose ARG (k/sum/amax/bool) is equal
    but RESULT differs is a **draw desync** (a rand scalar was consumed differently before
    this call); the first line whose ARG differs is an **upstream compute** difference
    feeding the generative process.
    """
    import contextlib
    import numpy as np
    from unittest.mock import patch

    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_nr_authority_rdp_mat,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        optim1full_nr_game_segment_id,
        spm_mdp_vb_xxx_with_ledger_segment_reuse,
    )
    from tests.demo1.optim1full.optim1full_vb_dispatch import resolve_vb_lane
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
        load_entry12_rdp_mat_nested_for_tag,
    )

    lane = resolve_vb_lane(vb_lane)  # type: ignore[arg-type]
    if lane == "optim":
        # optim `_spm_sample` lives in vb_primitives_optim but is imported by value into
        # each caller's namespace; patch every namespace that invokes it directly.
        from python_src.optimized.toolbox.DEM.vb_primitives_optim import _spm_sample as orig
        targets = [
            "python_src.optimized.toolbox.DEM.vb_primitives_optim._spm_sample",
            "python_src.optimized.toolbox.DEM.vb_orchestrator_optim._spm_sample",
            "python_src.optimized.toolbox.DEM.vb_cold_native_optim._spm_sample",
        ]
    else:
        # fidelity routes all sampling through the single module-local _spm_sample.
        from python_src.toolbox.DEM.spm_MDP_VB_XXX import _spm_sample as orig
        targets = ["python_src.toolbox.DEM.spm_MDP_VB_XXX._spm_sample"]

    records: list[str] = []
    depth = [0]

    def _traced(p: Any) -> int:
        # Guard against double-counting if two patched namespaces nest (they don't here,
        # but keep the record 1:1 with real draws): only the outermost entry records.
        depth[0] += 1
        captured: list[float] = []
        real_rand = np.random.rand  # the active replay shim
        if depth[0] == 1:
            def _cap(*a: Any, **kw: Any) -> float:
                v = float(real_rand(*a, **kw))
                captured.append(v)
                return v

            np.random.rand = _cap  # type: ignore[assignment]
        try:
            res = int(orig(p))
        finally:
            depth[0] -= 1
            if depth[0] == 0:
                np.random.rand = real_rand  # type: ignore[assignment]
        if depth[0] == 0:
            is_bool = 1 if (isinstance(p, np.ndarray) and p.dtype == bool) else 0
            pv = np.asarray(p, dtype=np.float64).ravel(order="F")
            k = int(pv.size)
            s = float(np.nansum(pv)) if k else 0.0
            amax = int(np.argmax(pv) + 1) if k else 0
            draws = ",".join(f"{v:.6f}" for v in captured)
            records.append(
                f"{len(records)} k={k} sum={s:.6g} amax={amax} bool={is_bool} "
                f"draws=[{draws}] -> {res}"
            )
        return res

    rdp_path = optim1full_nr_authority_rdp_mat(game)
    if not rdp_path.is_file():
        raise FileNotFoundError(f"game {game}: missing MATLAB RDP authority {rdp_path}")
    seg = manifest.segment(optim1full_nr_game_segment_id(game))
    nested_rdp = load_entry12_rdp_mat_nested_for_tag(_NR_RDP_DTYPE_TAG, rdp_path)

    with contextlib.ExitStack() as stack:
        for tgt in targets:
            stack.enter_context(patch(tgt, side_effect=_traced))
        spm_mdp_vb_xxx_with_ledger_segment_reuse(
            nested_rdp,
            np.asarray(buf, dtype=np.float64).ravel(),
            start=int(seg.start),
            k=int(seg.k),
            vb_lane=vb_lane,
        )

    out = _REPO / "logs" / f"optim1full_sample_trace_g{game:02d}_{lane}.txt"
    out.write_text("\n".join(records) + "\n", encoding="utf-8")
    print(
        f"[sample_trace] game {game:02d} lane={lane}: {len(records)} _spm_sample calls -> {out}",
        file=sys.stderr,
        flush=True,
    )
    return 0


def _run_one_game(
    game: int,
    buf: Any,
    manifest: Any,
    *,
    vb_lane: str = "optim",
) -> bool:
    """Return True if ``vb_lane`` PDP matches MATLAB PDP for ``game``; False on divergence.

    ``vb_lane="fidelity"`` is the CONTROL: fidelity is proven == MATLAB, so a fidelity
    divergence here means the localizer harness (RDP/draw wiring) is wrong, not the kernel.

    Detection always uses the asserting comparison (``_compare_pair(report_only=False)``),
    which raises on the first diverging leaf. ``report_only`` at the caller only controls
    whether the scan stops at the first diverging game or continues through all games.
    """
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _densify_sparse_leaves,
    )

    py_cmp, mat_cmp, seg = _compute_game_pdps(game, buf, manifest, vb_lane=vb_lane)

    label = f"OPTIM1FULL NR game {game:02d} {vb_lane}-VB vs MATLAB"
    py_dense = _densify_sparse_leaves(copy.deepcopy(py_cmp))
    mat_dense = _densify_sparse_leaves(copy.deepcopy(mat_cmp))
    try:
        _compare_pair(
            label,
            py_dense,
            mat_dense,
            "PDP",
            report_only=False,
            coerce_sparse=False,
        )
    except AssertionError as exc:
        # The shared comparator raises on the ALPHABETICAL-first leaf (e.g. downstream
        # aggregate ``F`` before the causally-earlier sampled trajectory). Enumerate every
        # diverging field in VB computation order so we debug the ROOT, not the accident.
        reds = _diagnose_divergence(py_dense, mat_dense)
        print(
            f"[optim1full_localize] game {game:02d}: DIVERGE k={seg.k} "
            f"({len(reds)} field(s) differ). Computation-order report "
            "(★ = causally feeds merged a; F is a downstream aggregate):",
            file=sys.stderr,
            flush=True,
        )
        for path, msg, mx, causal in reds:
            mark = "★" if causal else " "
            mxs = "" if mx is None else f" maxabs={mx:.6g}"
            print(f"    {mark} {path}:{mxs} {msg}", file=sys.stderr, flush=True)
        print(
            f"[optim1full_localize] game {game:02d}: alphabetical-first (shared gate) was -> {exc}",
            file=sys.stderr,
            flush=True,
        )
        return False
    print(
        f"[optim1full_localize] game {game:02d}: PASS (optim PDP == MATLAB PDP, k={seg.k})",
        file=sys.stderr,
        flush=True,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import optim1full_nr_authority_manifest_json
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game", type=int, default=None, help="run only this NR game (1..32)")
    p.add_argument("--first", type=int, default=1, help="first game when scanning (default 1)")
    p.add_argument("--last", type=int, default=32, help="last game when scanning (default 32)")
    p.add_argument(
        "--lane",
        choices=["optim", "fidelity", "dispatch"],
        default="optim",
        help="VB lane (default optim). 'fidelity' is the harness control (== MATLAB).",
    )
    p.add_argument(
        "--report-only",
        action="store_true",
        help="scan all games and report every diverging one (do not stop at the first)",
    )
    p.add_argument(
        "--trajectory-diff",
        action="store_true",
        help=(
            "diagnostic: for --game N, report the first timestep where the sampled "
            "trajectory (s/o/u/X) diverges from MATLAB (pins the draw-desync site in time)"
        ),
    )
    p.add_argument(
        "--sample-trace",
        action="store_true",
        help=(
            "diagnostic: for --game N + --lane, log every _spm_sample call (arg summary + "
            "result) to logs/; diff optim vs fidelity to separate draw-desync from arg diff"
        ),
    )
    p.add_argument("--deadline-minutes", default="120")
    args = p.parse_args(argv)

    os.environ.setdefault("RGMS_ATARI_RUN_DEADLINE_MINUTES", str(args.deadline_minutes))

    man_path = optim1full_nr_authority_manifest_json()
    if not man_path.is_file():
        print(
            f"[optim1full_localize] FAIL: NR authority trace missing ({man_path}).\n"
            "Run: python tests/demo1/optim1full/optim1full_capture_rand_ledger.py "
            "--nr-authority-trace  (then optim1full_verify_nr_authority_trace.py).",
            file=sys.stderr,
            flush=True,
        )
        return 2

    buf, manifest = load_validated_optim1full_ledger()

    if args.trajectory_diff:
        if args.game is None:
            print(
                "[optim1full_localize] FAIL: --trajectory-diff requires --game N",
                file=sys.stderr,
            )
            return 2
        g = int(args.game)
        if g < 1 or g > 32:
            print(f"[optim1full_localize] FAIL: game {g} out of range 1..32", file=sys.stderr)
            return 2
        return _trajectory_diff(g, buf, manifest, vb_lane=str(args.lane))

    if args.sample_trace:
        if args.game is None:
            print("[optim1full_localize] FAIL: --sample-trace requires --game N", file=sys.stderr)
            return 2
        g = int(args.game)
        if g < 1 or g > 32:
            print(f"[optim1full_localize] FAIL: game {g} out of range 1..32", file=sys.stderr)
            return 2
        return _sample_trace(g, buf, manifest, vb_lane=str(args.lane))

    if args.game is not None:
        games = [int(args.game)]
    else:
        games = list(range(int(args.first), int(args.last) + 1))
    for g in games:
        if g < 1 or g > 32:
            print(f"[optim1full_localize] FAIL: game {g} out of range 1..32", file=sys.stderr)
            return 2

    first_diverge: int | None = None
    diverged: list[int] = []
    for g in games:
        ok = _run_one_game(g, buf, manifest, vb_lane=str(args.lane))
        if not ok:
            diverged.append(g)
            if first_diverge is None:
                first_diverge = g
            if not args.report_only:
                break

    if not diverged:
        print(
            f"[optim1full_localize] ALL PASS: optim VB == MATLAB PDP for games "
            f"{games[0]:02d}..{games[-1]:02d}. No per-game VB divergence — investigate "
            "merge/basin assembly or accumulation, not the VB kernel.",
            file=sys.stderr,
            flush=True,
        )
        return 0

    if args.report_only:
        print(
            f"[optim1full_localize] DIVERGING GAMES: {diverged} (first={first_diverge:02d})",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            f"[optim1full_localize] FIRST DIVERGING GAME: {first_diverge:02d}. "
            "See the computation-order field report above: the earliest ★-marked "
            "(causal-to-a) field is the root to fix in spm_MDP_VB_XXX_optim; a lone "
            "downstream F red is a symptom, not the root. Re-run with "
            f"--game {first_diverge} after each edit.",
            file=sys.stderr,
            flush=True,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
