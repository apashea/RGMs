#!/usr/bin/env python3
"""**Validation 12** — Entry 12 artifact compare (MAT vs PKL).

Compares input ``RDP``, subentry checkpoints **12A**–**12I**, and final ``PDP`` produced by
``spm_MDP_VB_XXX(..., dump_subentries=True)`` on the MATLAB and Python sides.

Runs **causal 12D→12E→12F** boundary value asserts (**15** steps, **all** failures reported)
**before** input **RDP** and per-subentry type walks (``entry12_assert_causal_def_boundaries``).

RNG imperative (Entry 12): causal/value failures are actionable for compute only when
the paired replay lane is coherent on the same ``tag`` (scripts **1a→1b→3** with
matching ``K``/``vb_rand_buf`` contract). If RNG coherence is broken, fix that first;
do not tune ``spm_MDP_VB_XXX.py`` to force parity across different trajectories.

Causal payloads (``entry12_matlab_capture.py``): **12D** ``t``/``Mrow``/``MDP`` without parent
``A``/``O``/``o``; **12E** ``t``/workspace ``O``; **12F** ``Q``/``P``/``R``/``v``/``w``,
``MDP`` without parent ``A``, plus ``A_peaks_pre_vbx`` and ``A_peaks_pre_forwards`` (workspace
``A{m,g}`` from ``entry12_phase_log``). Struct ``MDP.A`` is not a causal gate.

Default fixtures under ``tests/oracle/toolbox/DEM/fixtures/`` (override paths via env; see
``Atari_example.md`` § Entry 12). Uses ``mat_nested_to_py``, nested type-walk, and
``_assert_nested_rdp_equal`` (511 vs 485 ledger policy on ``RDP`` / ``PDP`` tensor paths).

Each run overwrites ``matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt`` (module
docstring + teed stdout/stderr). ``-h`` / ``--help`` prints to the terminal only and does
not overwrite that file.

See ``Atari_example.md`` § **Entry 12** (XXX 12 / Validation 12 table).
"""

from __future__ import annotations

import argparse
import copy
import os
import pickle
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    entry12_align_12C_workspace_to_mat,
    entry12_align_entry12_workspace_to_mat,
    entry12_align_mdp_to_mat_workspace,
    entry12_mat_mdp_for_subentry_value_assert,
    entry12_mat_pdp_for_value_assert,
    entry12_align_py_rdp_to_validation_lane,
    entry12_assert_causal_def_boundaries,
    entry12_causal_boundary_steps_for_tag,
    entry12_print_phase_log_diagnostics,
    entry12_print_qo_ab_diagnostics,
    entry12_print_y_ab_diagnostics,
    entry12_rdp_for_validation_from_mat_nested,
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import (
    _TeeIO,
    _collect_type_mismatches,
    _emit_mdp_chain_field_inventory,
    _get_at_rdp_path,
    _ledger_511_485_pair,
    _mismatch_value_summary_lines,
    _norm_leaf,
    _repo_root,
    _safe_concise_value_desc,
    _summarize_one_side,
    _type_walk_path_from_line,
    _densify_sparse_leaves,
    compare_nested_rdp_oracle_lane,
)

_ENTRY12_SUBENTRY_CODES: tuple[str, ...] = tuple(f"12{c}" for c in "ABCDEFGHI")

_ACCEPTED_PDP_511_485_PREFIXES: tuple[str, ...] = (
    "PDP.A",
    "PDP.B",
    "PDP.H",
    "PDP.X",
    "PDP.MDP.A",
    "PDP.MDP.B",
    "PDP.MDP.H",
    "PDP.MDP.X",
)

_ACCEPTED_RDP_511_485_PREFIXES: tuple[str, ...] = (
    "RDP.A",
    "RDP.B",
    "RDP.H",
    "RDP.X",
    "RDP.MDP.A",
    "RDP.MDP.B",
    "RDP.MDP.H",
    "RDP.MDP.X",
)


def _is_accepted_ledger_dim_mismatch(path: str, py: Any, mat: Any) -> bool:
    prefixes = _ACCEPTED_PDP_511_485_PREFIXES + _ACCEPTED_RDP_511_485_PREFIXES
    if not any(path.startswith(p) for p in prefixes):
        return False
    return _ledger_511_485_pair(py, mat)


def _mismatch_detail_lines(path: str, py: Any, mat: Any) -> list[str]:
    tag = ""
    if _is_accepted_ledger_dim_mismatch(path, py, mat):
        tag = "[accepted ledger dim 511 vs 485 - upstream Py/MATLAB; ENTRY 1-11 policy] "
    py_l = _summarize_one_side("PKL", py)
    mat_l = _summarize_one_side("MAT", mat)
    return [f"  {tag}[mismatch detail] {py_l}", f"  [mismatch detail] {mat_l}"]


def _mismatch_detail_pdp(path: str, py: Any, mat: Any) -> list[str]:
    return _mismatch_detail_lines(path, py, mat)


def _xxx12_validation_output_txt_path() -> Path:
    return _repo_root() / "matlab_custom" / "XXX_12_compare_pdp_pkl_to_mat_output.txt"


def _default_pkl_path() -> Path:
    raw = str(os.getenv("RGMS_XXX_12_PDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

    return entry12_signoff_artifact_paths(_entry12_run_tag())["pdp_pkl"]


def _default_mat_path() -> Path:
    raw = str(os.getenv("RGMS_XXX_12_PDP_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

    return entry12_signoff_artifact_paths(_entry12_run_tag())["pdp_mat"]


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def _entry12_run_tag() -> str:
    return (os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG") or ENTRY12_CANONICAL_RUN_TAG).strip()


def _entry12_out_dir() -> Path:
    raw = str(os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", "")).strip()
    return Path(raw).expanduser().resolve() if raw else _fixtures_dir()


def _default_rdp_pkl_path() -> Path:
    raw = str(os.getenv("RGMS_XXX_12_RDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

    return entry12_signoff_artifact_paths(_entry12_run_tag())["rdp_pkl"]


def _default_rdp_mat_path() -> Path:
    raw = str(os.getenv("RGMS_XXX_12_RDP_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

    return entry12_signoff_artifact_paths(_entry12_run_tag())["rdp_mat"]


def _subentry_pkl_path(code: str) -> Path:
    tag = _entry12_run_tag()
    return _entry12_out_dir() / f"DEMAtariIII_entry12_{tag}_{code}.pkl"


_ENTRY12_CAUSAL_BANDS: tuple[str, ...] = ("12D", "12E", "12F")


def _load_entry12_causal_band_workspaces(
    tag: str,
    out_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]] | None:
    """Load paired **12D** / **12E** / **12F** workspaces for the causal boundary gate."""
    py_def: dict[str, dict[str, Any]] = {}
    mat_def: dict[str, dict[str, Any]] = {}
    for band in _ENTRY12_CAUSAL_BANDS:
        mat_p = entry12_subentry_mat_path(tag, band, out_dir=out_dir)
        pkl_p = _subentry_pkl_path(band)
        if not mat_p.is_file() or not pkl_p.is_file():
            print(
                f"[XXX 12 validation] skip causal gate (missing {band}: "
                f"mat={mat_p.is_file()}, pkl={pkl_p.is_file()})",
                file=sys.stderr,
            )
            return None
        py_def[band] = _entry12_workspace_payload(_load_subentry_pkl(pkl_p), band)
        mat_def[band] = _entry12_workspace_payload(
            _mat_blob_to_py(load_entry12_subentry_mat(mat_p)),
            band,
        )
    return py_def, mat_def


def _run_entry12_causal_boundary_gate(
    tag: str,
    out_dir: Path,
    *,
    report_only: bool,
    coerce_sparse: bool,
) -> bool | None:
    """
    Print the causal plan and run value asserts (12D→12E→12F per boundary).

    Returns ``True`` if any causal step failed, ``False`` if all pass, ``None`` if skipped.
    """
    steps = entry12_causal_boundary_steps_for_tag(tag)
    print(
        "[XXX 12 validation] --- causal 12D→12E→12F boundaries (first in run) ---",
        file=sys.stderr,
    )
    for code, sub in steps:
        print(f"  {code}.{sub}", file=sys.stderr)
    loaded = _load_entry12_causal_band_workspaces(tag, out_dir)
    if loaded is None:
        return None
    py_def, mat_def = loaded
    if report_only:
        print(
            "[XXX 12 validation] skip causal value assert (--report-type-mismatches-only)",
            file=sys.stderr,
        )
        return None
    failures = entry12_assert_causal_def_boundaries(
        py_def,
        mat_def,
        densify=_densify_sparse_leaves if coerce_sparse else None,
        steps=steps,
    )
    if failures:
        print(
            f"[XXX 12 validation] FAIL: causal 12D→12E→12F boundaries "
            f"({len(failures)}/{len(steps)} steps red)",
            file=sys.stderr,
        )
        for i, msg in enumerate(failures, start=1):
            print(f"  [{i}] {msg}", file=sys.stderr)
        print(
            f"[XXX 12 validation] fix compute at first red: {failures[0]}",
            file=sys.stderr,
        )
        if "Q.O" in failures[0]:
            entry12_print_qo_ab_diagnostics(py_def, mat_def, stream=sys.stderr)
        elif "MDP.MDP.Y" in failures[0] or "MDP.Y" in failures[0] or "Q.Y" in failures[0]:
            entry12_print_y_ab_diagnostics(py_def, mat_def, stream=sys.stderr)
        elif "MDP.F" in failures[0] or "12F." in failures[0]:
            entry12_print_phase_log_diagnostics(py_def, mat_def, stream=sys.stderr)
        return True
    print(
        "[XXX 12 validation] OK: causal 12D→12E→12F boundaries "
        f"({len(steps)} steps)",
        file=sys.stderr,
    )
    return False


_MATLAB_LOADMAT_META = frozenset({"__header__", "__version__", "__globals__"})


def _load_matlab_pdp(mat_path: Path) -> Any:
    from scipy.io import loadmat

    p = mat_path.resolve()
    kw: dict[str, Any] = {}
    try:
        kw["simplify_cells"] = True
        raw = loadmat(str(p), **kw)
    except TypeError:
        raw = loadmat(str(p))
    if "PDP" not in raw:
        keys = sorted(k for k in raw if k not in _MATLAB_LOADMAT_META)
        raise KeyError(f"expected top-level PDP in {p}, got keys={keys}")
    return mat_nested_to_py(raw["PDP"])


def _emit_pdp_top_level_inventory(tag: str, pdp: Any) -> None:
    if not isinstance(pdp, dict):
        print(
            f"[XXX 12 validation] {tag} top-level: not a dict (type={type(pdp).__name__})",
            file=sys.stderr,
        )
        return
    for k in sorted(pdp.keys(), key=str):
        desc = _safe_concise_value_desc(pdp[k])
        print(f"[XXX 12 validation] {tag} field {k}={desc}", file=sys.stderr)


def _emit_pdp_top_level_key_diff(py_pdp: Any, mat_pdp: Any) -> None:
    if not isinstance(py_pdp, dict) or not isinstance(mat_pdp, dict):
        print(
            "[XXX 12 validation] PDP top-level key diff: skipped (one or both sides not dict-like)",
            file=sys.stderr,
        )
        return
    sp = set(py_pdp.keys())
    sm = set(mat_pdp.keys())
    only_py = sorted(sp - sm, key=str)
    only_mat = sorted(sm - sp, key=str)

    def _fmt(keys: list[Any], d: dict[str, Any]) -> str:
        if not keys:
            return "(none)"
        return ",".join(f"{k}={_safe_concise_value_desc(d[k])}" for k in keys)

    print(
        "[XXX 12 validation] PDP top-level key diff: "
        f"only_in_PKL={_fmt(only_py, py_pdp)}; only_in_MATLAB={_fmt(only_mat, mat_pdp)}",
        file=sys.stderr,
    )


def _emit_nested_type_walk_pdp(py_pdp: Any, mat_pdp: Any) -> None:
    lines: list[str] = []
    _collect_type_mismatches(py_pdp, mat_pdp, "PDP", lines)
    print(f"[XXX 12 validation] type walk: {len(lines)} mismatch line(s)", file=sys.stderr)
    wrap_py = {"PDP": py_pdp}
    wrap_mat = {"PDP": mat_pdp}
    for ln in lines:
        print(ln, file=sys.stderr)
        path = _type_walk_path_from_line(ln)
        if path is None:
            continue
        py_val = _norm_leaf(_get_at_rdp_path(wrap_py, path))
        mat_val = _norm_leaf(_get_at_rdp_path(wrap_mat, path))
        for dl in _mismatch_detail_pdp(path, py_val, mat_val)[:2]:
            print(dl, file=sys.stderr)


def _mat_blob_to_py(blob: dict[str, Any]) -> dict[str, Any]:
    return {k: mat_nested_to_py(v) for k, v in blob.items() if k not in _MATLAB_LOADMAT_META}


def _load_subentry_pkl(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"pickle must be dict, got {type(blob).__name__}")
    return blob


def _collapse_matlab_struct_broadcast(val: Any, *, code: str = "") -> Any:
    """MATLAB lean snaps: ``struct('t', t, 'O', Ot)`` with cell ``Ot`` saves as 1×N struct row in ``.mat``."""
    if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
        if code == "12E" and all("O" in x for x in val):
            row = [copy.deepcopy(x["O"]) for x in val]
            t0 = val[0].get("t")
            try:
                import numpy as np

                t0 = int(np.asarray(t0).item())
            except (TypeError, ValueError):
                pass
            return {"t": t0, "O": [row]}
        return val[0]
    return val


def _normalize_lean_boundary_payload(payload: Any, *, code: str = "") -> Any:
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    for key in ("in", "out_t1", "out_t2", "out_t3", "out_tT"):
        if key in out:
            out[key] = _collapse_matlab_struct_broadcast(out[key], code=code)
    return out


def _rdp_H_first_dim(rdp: Any) -> int | None:
    import numpy as np
    from scipy import sparse

    if not isinstance(rdp, dict):
        return None
    h = rdp.get("H")
    if h is None:
        return None
    if sparse.issparse(h):
        return int(h.shape[0])
    if isinstance(h, np.ndarray) and h.ndim >= 1:
        return int(h.shape[0])
    return None


def _warn_rdp_lane_mismatch(py_rdp: Any, mat_rdp: Any) -> None:
    py_n = _rdp_H_first_dim(py_rdp)
    mat_n = _rdp_H_first_dim(mat_rdp)
    if py_n is None or mat_n is None or py_n == mat_n:
        return
    print(
        "[XXX 12 validation] WARNING: RDP lane mismatch — "
        f"PKL H dim0={py_n} vs MAT H dim0={mat_n} "
        "(Phase 1 expects mat-sourced XXX 12; ctx PKL is 511 / mat is 485). "
        "Re-run XXX 12 without RGMS_XXX_12_RDP_FROM_CTX=1.",
        file=sys.stderr,
    )


def _entry12_workspace_payload(blob: dict[str, Any], code: str) -> Any:
    if code == "12A":
        return blob.get("MDP")
    if code == "12H":
        return blob.get("PDP")
    if code == "12I":
        spine = blob.get("spine")
        if isinstance(spine, dict):
            return {k: v for k, v in spine.items() if k != "matlab_release"}
        return spine
    if code in ("12D", "12E", "12F"):
        skip = frozenset({"OPTIONS", "meta", "per_t"})
        ws = {k: v for k, v in blob.items() if k not in skip}
        return _normalize_lean_boundary_payload(ws, code=code)
    return {k: v for k, v in blob.items() if k not in ("OPTIONS", "meta")}


def _emit_nested_compare(
    label: str,
    py_obj: Any,
    mat_obj: Any,
    root_prefix: str,
) -> None:
    lines: list[str] = []
    _collect_type_mismatches(py_obj, mat_obj, root_prefix, lines)
    print(f"[XXX 12 validation] {label} type walk: {len(lines)} mismatch line(s)", file=sys.stderr)
    wrap_py = {root_prefix: py_obj}
    wrap_mat = {root_prefix: mat_obj}
    for ln in lines:
        print(ln, file=sys.stderr)
        path = _type_walk_path_from_line(ln)
        if path is None:
            continue
        py_val = _norm_leaf(_get_at_rdp_path(wrap_py, path))
        mat_val = _norm_leaf(_get_at_rdp_path(wrap_mat, path))
        for dl in _mismatch_detail_lines(path, py_val, mat_val)[:2]:
            print(dl, file=sys.stderr)


def _compare_pair(
    label: str,
    py_obj: Any,
    mat_obj: Any,
    root_prefix: str,
    *,
    report_only: bool,
    coerce_sparse: bool,
) -> None:
    print(f"[XXX 12 validation] --- {label} ---", file=sys.stderr)
    _emit_nested_compare(label, py_obj, mat_obj, root_prefix)
    if report_only:
        return
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    if coerce_sparse:
        py_cmp = _densify_sparse_leaves(copy.deepcopy(py_obj))
        mat_cmp = _densify_sparse_leaves(copy.deepcopy(mat_obj))
        _assert_nested_rdp_equal(py_cmp, mat_cmp, root_prefix)
    else:
        _assert_nested_rdp_equal(py_obj, mat_obj, root_prefix)
    print(f"[XXX 12 validation] OK: {label}", file=sys.stderr)


def _argv_requests_help(argv: list[str]) -> bool:
    return any(a in ("-h", "--help") for a in argv)


def _build_argument_parser() -> ArgumentParser:
    p = argparse.ArgumentParser(
        description="Validation 12: compare PDP in XXX 12 PKL vs MATLAB XXX_12_pdp.mat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pkl", type=Path, default=None, help="XXX 12 PDP pickle (default: fixtures/...)")
    p.add_argument("--mat", type=Path, default=None, help="MATLAB PDP mat (default: fixtures/...)")
    p.add_argument(
        "--coerce-sparse-to-dense-for-compare",
        action="store_true",
        help="Dense SciPy sparse leaves on in-memory copies before assert (same as Validation 1-11).",
    )
    p.add_argument(
        "--report-type-mismatches-only",
        action="store_true",
        help="Emit inventory, key diff, and type walk only; exit 0 without nested assert.",
    )
    p.add_argument(
        "--entry12-causal-only",
        action="store_true",
        help=(
            "Run only the 15-step causal 12D→12E→12F gate (+ inspection blocks on failure); "
            "skip RDP, 12A–12I, and PDP. Fast iteration; full sign-off still requires full script 4."
        ),
    )
    return p


def _execute_validation(args: Namespace) -> int:
    report_only = bool(args.report_type_mismatches_only)
    coerce = bool(args.coerce_sparse_to_dense_for_compare)
    causal_only = bool(getattr(args, "entry12_causal_only", False))
    exit_code = 0

    tag = _entry12_run_tag()
    out_dir = _entry12_out_dir()

    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_assert_buf_k_coherent,
        entry12_assert_signoff_chain_ready,
        entry12_log_signoff_chain,
    )

    if tag != ENTRY12_CANONICAL_RUN_TAG or str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "")).strip():
        try:
            _gate = str(os.getenv("RGMS_FSL_ENTRY11_GATE_COMPARE", "")).strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            entry12_assert_signoff_chain_ready(
                tag, require_rand_buf=False, require_script3_pkls=not _gate
            )
            entry12_assert_buf_k_coherent(tag)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[XXX 12 validation] error: {exc}", file=sys.stderr)
            return 2
    entry12_log_signoff_chain(tag, stream=sys.stderr)

    if _run_entry12_causal_boundary_gate(
        tag, out_dir, report_only=report_only, coerce_sparse=coerce
    ):
        exit_code = 1

    if causal_only:
        return exit_code

    rdp_pkl = _default_rdp_pkl_path().resolve()
    rdp_mat = _default_rdp_mat_path().resolve()
    if rdp_pkl.is_file() and rdp_mat.is_file():
        with rdp_pkl.open("rb") as f:
            py_rdp_blob = pickle.load(f)
        if not isinstance(py_rdp_blob, dict) or "RDP" not in py_rdp_blob:
            print("error: RDP pickle must be dict with key 'RDP'", file=sys.stderr)
            return 2
        from tests.oracle.toolbox.DEM.fsl_1_11_compare_ctx_pkl_to_mat import (
            _load_matlab_nested_rdp_for_fsl_oracle,
        )

        py_rdp = py_rdp_blob["RDP"]
        mat_nested = _load_matlab_nested_rdp_for_fsl_oracle(rdp_mat)
        mat_rdp = entry12_rdp_for_validation_from_mat_nested(mat_nested)
        py_rdp = entry12_align_py_rdp_to_validation_lane(py_rdp, mat_rdp)
        _warn_rdp_lane_mismatch(py_rdp, mat_rdp)
        print("[XXX 12 validation] --- input RDP (FSL 1-11-style lane) ---", file=sys.stderr)
        rdp_code = compare_nested_rdp_oracle_lane(
            py_rdp,
            mat_rdp,
            lane="XXX 12 validation",
            report_only=report_only,
            coerce_sparse=coerce,
        )
        if rdp_code != 0:
            exit_code = 1
    else:
        print(
            f"[XXX 12 validation] skip input RDP (pkl={rdp_pkl.is_file()}, mat={rdp_mat.is_file()})",
            file=sys.stderr,
        )

    for code in _ENTRY12_SUBENTRY_CODES:
        mat_p = entry12_subentry_mat_path(tag, code, out_dir=out_dir)
        pkl_p = _subentry_pkl_path(code)
        if not mat_p.is_file() or not pkl_p.is_file():
            print(
                f"[XXX 12 validation] skip subentry {code} "
                f"(mat={mat_p.is_file()}, pkl={pkl_p.is_file()})",
                file=sys.stderr,
            )
            continue
        py_blob = _load_subentry_pkl(pkl_p)
        mat_blob = _mat_blob_to_py(load_entry12_subentry_mat(mat_p))
        py_ws = _entry12_workspace_payload(py_blob, code)
        mat_ws = _entry12_workspace_payload(mat_blob, code)
        if code == "12A" and isinstance(py_ws, dict) and isinstance(mat_ws, dict):
            py_ws = entry12_align_mdp_to_mat_workspace(py_ws, mat_ws)
            mat_ws = entry12_mat_mdp_for_subentry_value_assert(py_ws, mat_ws)
        elif code == "12B" and isinstance(py_ws, dict) and isinstance(mat_ws, dict):
            py_ws = entry12_align_entry12_workspace_to_mat(py_ws, mat_ws)
        elif code == "12C" and isinstance(py_ws, dict) and isinstance(mat_ws, dict):
            py_ws = entry12_align_12C_workspace_to_mat(py_ws, mat_ws)
        elif code == "12H" and isinstance(py_ws, dict) and isinstance(mat_ws, dict):
            py_ws = entry12_align_mdp_to_mat_workspace(py_ws, mat_ws)
            mat_ws = entry12_mat_pdp_for_value_assert(mat_ws)
        elif code in ("12D", "12E", "12F") and isinstance(py_ws, dict) and isinstance(mat_ws, dict):
            # Capture-shaped inventory: raw paired dumps (causal gate aligns separately).
            print(
                f"[XXX 12 validation] --- subentry {code} (capture-shaped type walk) ---",
                file=sys.stderr,
            )
            _emit_nested_compare(f"subentry {code}", py_ws, mat_ws, code)
            continue
        elif code == "12G":
            # Atari lane: OPTIONS.B=0 — spm_backwards never runs; 12G is informational only.
            print(
                "[XXX 12 validation] skip subentry 12G "
                "(postponed / non-gating for DEM_AtariIII; OPTIONS.B=0)",
                file=sys.stderr,
            )
            continue
        try:
            _compare_pair(
                f"subentry {code}",
                py_ws,
                mat_ws,
                code,
                report_only=report_only,
                coerce_sparse=coerce,
            )
        except AssertionError as exc:
            print(f"[XXX 12 validation] subentry {code} value assert: {exc}", file=sys.stderr)
            exit_code = 1

    pkl_path = (args.pkl or _default_pkl_path()).resolve()
    if not pkl_path.is_file():
        print(f"error: missing PDP pickle: {pkl_path}", file=sys.stderr)
        return 2

    mat_path = (args.mat or _default_mat_path()).resolve()
    if not mat_path.is_file():
        print(f"error: missing PDP .mat: {mat_path}", file=sys.stderr)
        return 2

    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "PDP" not in blob:
        print("error: pickle must be a dict with key 'PDP' (XXX 12 output)", file=sys.stderr)
        return 2

    py_pdp = blob["PDP"]
    mat_pdp = _load_matlab_pdp(mat_path)

    _emit_pdp_top_level_inventory("PKL PDP", py_pdp)
    _emit_mdp_chain_field_inventory("PKL PDP", py_pdp, "PDP")
    _emit_pdp_top_level_inventory("MATLAB PDP", mat_pdp)
    _emit_mdp_chain_field_inventory("MATLAB PDP", mat_pdp, "PDP")
    _emit_pdp_top_level_key_diff(py_pdp, mat_pdp)
    if isinstance(py_pdp, dict) and isinstance(mat_pdp, dict):
        import copy

        py_tw = entry12_align_mdp_to_mat_workspace(copy.deepcopy(py_pdp), mat_pdp)
        mat_tw = entry12_mat_pdp_for_value_assert(mat_pdp)
        print(
            "[XXX 12 validation] PDP type walk uses compare-aligned trees (same as final value assert)",
            file=sys.stderr,
        )
        _emit_nested_type_walk_pdp(py_tw, mat_tw)
    else:
        _emit_nested_type_walk_pdp(py_pdp, mat_pdp)

    if report_only:
        return exit_code

    try:
        py_pdp_cmp = py_pdp
        mat_pdp_cmp = mat_pdp
        if isinstance(py_pdp, dict) and isinstance(mat_pdp, dict):
            py_pdp_cmp = entry12_align_mdp_to_mat_workspace(py_pdp, mat_pdp)
            mat_pdp_cmp = entry12_mat_pdp_for_value_assert(mat_pdp)
        _compare_pair(
            "final PDP",
            py_pdp_cmp,
            mat_pdp_cmp,
            "PDP",
            report_only=False,
            coerce_sparse=coerce,
        )
    except AssertionError as exc:
        print(f"[XXX 12 validation] final PDP value assert: {exc}", file=sys.stderr)
        exit_code = 1

    if exit_code == 0:
        print(f"OK: Validation 12 passed (PDP mat {mat_path})", file=sys.stderr)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if _argv_requests_help(argv):
        _build_argument_parser().print_help(file=sys.stdout)
        return 0

    parser = _build_argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    out_path = _xxx12_validation_output_txt_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_f = open(out_path, "w", encoding="utf-8")
    try:
        report_f.write(__doc__ or "")
        report_f.write(f"\n--- RUN OUTPUT (stdout + stderr) — {out_path} ---\n")
        report_f.flush()
        old_err, old_out = sys.stderr, sys.stdout
        sys.stderr = _TeeIO(old_err, report_f)
        sys.stdout = _TeeIO(old_out, report_f)
        try:
            return _execute_validation(args)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 1
        finally:
            sys.stderr = old_err
            sys.stdout = old_out
    finally:
        report_f.close()


if __name__ == "__main__":
    raise SystemExit(main())
