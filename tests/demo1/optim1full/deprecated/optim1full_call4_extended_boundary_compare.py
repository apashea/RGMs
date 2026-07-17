#!/usr/bin/env python3
"""OPTIM1FULL call4 — script **4** causal compare on extended keys ``out_t10/20/30`` only."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.optim1full.optim1full_entry12_extended_boundary_keys import (
    OPTIM1FULL_CALL4_EXTENDED_TAG,
    OPTIM1FULL_CALL4_EXTRA_BOUNDARY_KEYS,
)


def _report_dir() -> Path:
    p = _REPO / "tests" / "demo1" / "optim1full" / "probe" / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_band_workspaces(fix: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _entry12_workspace_payload,
        _load_subentry_pkl,
        _mat_blob_to_py,
    )
    from python_src.toolbox.DEM.entry12_matlab_capture import load_entry12_subentry_mat

    py_def: dict[str, dict[str, Any]] = {}
    mat_def: dict[str, dict[str, Any]] = {}
    for band in ("12D", "12E", "12F"):
        mat_p = fix / f"DEMAtariIII_entry12_{OPTIM1FULL_CALL4_EXTENDED_TAG}_{band}.mat"
        pkl_p = fix / f"DEMAtariIII_entry12_{OPTIM1FULL_CALL4_EXTENDED_TAG}_{band}.pkl"
        py_def[band] = _entry12_workspace_payload(_load_subentry_pkl(pkl_p), band)
        mat_def[band] = _entry12_workspace_payload(
            _mat_blob_to_py(load_entry12_subentry_mat(mat_p)),
            band,
        )
    return py_def, mat_def


def _compare_one(
    band: str,
    sub: str,
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
    *,
    densify: Any,
) -> str | None:
    """Script **4** causal payload compare for one boundary; ``None`` if OK."""
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_12D_snap_to_mat,
        entry12_align_12E_snap_to_mat,
        entry12_align_12F_snap_to_mat,
        entry12_canonicalize_saved_structures_for_compare,
        entry12_causal_payload_12d,
        entry12_causal_payload_12e,
        entry12_causal_payload_12f,
        entry12_mat_snap_for_value_assert,
        _entry12_prune_mat_mdp_snap_keys_for_py,
    )
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    label = f"{band}.{sub}"
    if sub not in py_ws or sub not in mat_ws:
        return f"{label} (missing key)"
    raw_py, raw_mat = py_ws[sub], mat_ws[sub]
    align = {
        "12D": entry12_align_12D_snap_to_mat,
        "12E": entry12_align_12E_snap_to_mat,
        "12F": entry12_align_12F_snap_to_mat,
    }[band]
    try:
        py_cmp = align(raw_py, raw_mat)
        mat_cmp = entry12_mat_snap_for_value_assert(band, raw_mat)
        if densify is not None:
            py_cmp = densify(py_cmp)
            mat_cmp = densify(mat_cmp)
        py_cmp = entry12_canonicalize_saved_structures_for_compare(py_cmp)
        mat_cmp = entry12_canonicalize_saved_structures_for_compare(mat_cmp)
        if isinstance(py_cmp.get("MDP"), dict) and isinstance(mat_cmp.get("MDP"), dict):
            mat_cmp["MDP"] = _entry12_prune_mat_mdp_snap_keys_for_py(
                mat_cmp["MDP"], py_cmp["MDP"]
            )
        if band == "12D":
            py_payload = entry12_causal_payload_12d(py_cmp)
            mat_payload = entry12_causal_payload_12d(mat_cmp)
        elif band == "12E":
            py_payload = entry12_causal_payload_12e(py_cmp)
            mat_payload = entry12_causal_payload_12e(mat_cmp)
        else:
            py_payload, py_missing = entry12_causal_payload_12f(py_cmp, raw_py)
            mat_payload, mat_missing = entry12_causal_payload_12f(mat_cmp, raw_mat)
            miss = sorted(set(py_missing) | set(mat_missing))
            if miss:
                return f"{label}: missing {', '.join(miss)} on entry12_phase_log"
        _assert_nested_rdp_equal(py_payload, mat_payload, label)
        return None
    except Exception as exc:
        return f"{label}: {exc}"


def run_compare() -> Path:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _densify_sparse_leaves

    fix = optim1full_fixtures_dir()
    py_def, mat_def = _load_band_workspaces(fix)
    lines: list[str] = [
        "OPTIM1FULL call4 extended boundary compare (script 4 causal lane)",
        f"tag={OPTIM1FULL_CALL4_EXTENDED_TAG}",
        f"keys={list(OPTIM1FULL_CALL4_EXTRA_BOUNDARY_KEYS)}",
        "",
    ]
    failures: list[str] = []
    for sub in OPTIM1FULL_CALL4_EXTRA_BOUNDARY_KEYS:
        lines.append(f"=== {sub} ===")
        for band in ("12D", "12E", "12F"):
            msg = _compare_one(
                band,
                sub,
                py_def[band],
                mat_def[band],
                densify=_densify_sparse_leaves,
            )
            if msg is None:
                lines.append(f"  {band}.{sub} OK")
            else:
                lines.append(f"  {msg}")
                failures.append(msg)

    lines.extend(["", "=== summary ==="])
    lines.append(f"extended causal reds: {len(failures)}")
    for f in failures:
        lines.append(f"  RED: {f}")
    if not failures:
        lines.append("  all extended probe boundaries OK (script 4 causal)")

    out = _report_dir() / f"call4_extended_boundary_compare_{date.today().isoformat()}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[optim1full call4 extended compare] wrote {out}", flush=True)
    return out


def main() -> int:
    try:
        run_compare()
        return 0
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
