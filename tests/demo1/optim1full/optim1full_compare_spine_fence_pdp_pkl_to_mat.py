#!/usr/bin/env python3
"""OPTIM1FULL spine fence — paired ``PDP`` ``.pkl`` vs ``.mat`` compare at illustrate boundary.

Pairing gate for parity-with-plots **before** plot oracle sign-off. Compares spine
``input.pkl`` (``capture=optim1full_export_spine_fence_pdp``) to spine ``input.mat``
from the same lineage — **not** Entry **12** Validation **12** causal gate.

**Report:** ``matlab_custom/optim1full_compare_spine_fence_pdp_output.txt``
"""
from __future__ import annotations

import argparse
import copy
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.optim1full.optim1full_export_spine_fence_pdp import (
    CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
)


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "optim1full_compare_spine_fence_pdp_output.txt"


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


def _load_spine_pkl(pkl_path: Path) -> dict[str, Any]:
    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise KeyError(f"spine pkl must be dict: {pkl_path}")
    capture = blob.get("capture")
    if capture != CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP:
        raise RuntimeError(
            f"refusing compare on non-spine pkl capture={capture!r} path={pkl_path}"
        )
    return blob


def _load_spine_mat_pdp(mat_path: Path) -> Any:
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp

    return _load_matlab_pdp(mat_path)


_BASIN_SERIES_KEYS = ("NS", "NU", "NA", "NO", "NH")
_POST_SORT_PAYLOAD_KEYS = ("b1", "hid")


def _assert_payload_mat_meta(
    mat_path: Path,
    *,
    require_matlab_authority: bool = False,
) -> None:
    """Assert ``meta.capture`` on a non-PDP ``…_matlab_payload.mat`` authority."""
    from scipy.io import loadmat

    from tests.demo1.optim1full.optim1full_paths import (
        OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE,
    )

    raw = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
    if "meta" not in raw:
        raise KeyError(f"payload mat missing meta: {mat_path}")
    meta = raw["meta"]
    capture = str(getattr(meta, "capture", ""))
    if require_matlab_authority:
        if capture != OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE:
            raise RuntimeError(
                f"payload mat meta.capture={capture!r} expected "
                f"{OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE!r} (MATLAB-owned plot-fence authority). "
                f"path={mat_path}"
            )
        return
    if capture != OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE:
        raise RuntimeError(
            f"payload mat meta.capture={capture!r} expected "
            f"{OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE!r}. path={mat_path}"
        )


def _assert_spine_authority_mat_meta(
    mat_path: Path,
    *,
    authority_kind: str,
    require_matlab_authority: bool = True,
) -> None:
    """Kind-aware authority meta check (PDP ``metaPdp`` or payload ``meta``)."""
    from tests.demo1.optim1full.optim1full_plot_sites import AUTHORITY_KIND_PAYLOAD

    if authority_kind == AUTHORITY_KIND_PAYLOAD:
        _assert_payload_mat_meta(mat_path, require_matlab_authority=require_matlab_authority)
    else:
        _assert_spine_mat_meta(mat_path, require_matlab_authority=require_matlab_authority)


def _assert_spine_mat_meta(
    mat_path: Path,
    *,
    allow_matlab_fence_capture: bool = False,
    require_matlab_authority: bool = False,
) -> None:
    from scipy.io import loadmat

    from tests.demo1.optim1full.optim1full_paths import (
        OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE,
    )

    raw = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
    if "metaPdp" not in raw:
        raise KeyError(f"spine mat missing metaPdp: {mat_path}")
    meta = raw["metaPdp"]
    capture = str(getattr(meta, "capture", ""))

    if require_matlab_authority:
        # Genuine plot-parity: the .mat MUST be the INDEPENDENT MATLAB-computed fence PDP.
        # A Python-resaved .mat (--save-mat-from-pkl, capture=optim1full_export_spine_fence_pdp)
        # is CIRCULAR here and is refused outright.
        if capture == CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP:
            raise RuntimeError(
                "REFUSING circular plot-parity authority: spine mat "
                f"metaPdp.capture={capture!r} is a Python re-save (--save-mat-from-pkl), "
                "not an independent MATLAB fence. Regenerate the MATLAB-owned authority via "
                "capture_optim1full_rand_ledger + RGMS_OPTIM1FULL_PLOT_FENCE_TRACE=1 "
                f"(expected capture={OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE!r}). path={mat_path}"
            )
        if capture != OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE:
            raise RuntimeError(
                f"spine mat metaPdp.capture={capture!r} expected "
                f"{OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE!r} (MATLAB-owned plot-fence authority). "
                f"path={mat_path}"
            )
        return

    allowed = {CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP, OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE}
    if allow_matlab_fence_capture:
        allowed.add("capture_optim1full_dem_generative_ai")
    if capture not in allowed:
        raise RuntimeError(
            f"spine mat metaPdp.capture={capture!r} expected one of {sorted(allowed)!r}"
        )


def _is_ss_sparse_dict(x: Any) -> bool:
    return isinstance(x, dict) and bool(x) and all(isinstance(k, tuple) and len(k) == 2 for k in x)


def _normalize_spine_ss_cell(cell: Any) -> Any:
    if cell is None:
        return []
    if _is_ss_sparse_dict(cell):
        from tests.demo1.optim1full.optim1full_mdp_engine_io import _ss_dict_to_dense

        return _ss_dict_to_dense(cell)
    return cell


def _normalize_spine_ss_grids(pdp: dict[str, Any]) -> None:
    """Compare-lane: ``None`` / sparse-dict ``ss.*`` cells → MATLAB ``[]`` / dense arrays."""
    ss = pdp.get("ss")
    if isinstance(ss, dict):
        for fk in ("D", "E", "ID", "IE"):
            grid = ss.get(fk)
            if isinstance(grid, list) and grid and isinstance(grid[0], list):
                ss[fk] = [[_normalize_spine_ss_cell(c) for c in row] for row in grid]
    mdp = pdp.get("MDP")
    if isinstance(mdp, dict):
        _normalize_spine_ss_grids(mdp)


def _normalize_spine_mat_pa_for_align(mat_pdp: dict[str, Any]) -> None:
    """Empty ``Pa{i}`` cells from ``loadmat`` → ``{}`` for py dict lane alignment."""
    import numpy as np

    pa = mat_pdp.get("Pa")
    if not isinstance(pa, list):
        return
    fixed: list[Any] = []
    for item in pa:
        if isinstance(item, np.ndarray) and item.size == 0:
            fixed.append({})
        else:
            fixed.append(item)
    mat_pdp["Pa"] = fixed


def _spine_mat_pdp_for_value_assert(mat_pdp: dict[str, Any]) -> dict[str, Any]:
    """MATLAB spine ``PDP`` lane for value assert (empty ``MDP.Pa`` omitted like Python strip)."""
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_mat_pdp_for_value_assert

    out = entry12_mat_pdp_for_value_assert(mat_pdp)
    mdp = out.get("MDP")
    if isinstance(mdp, dict):
        pa = mdp.get("Pa")
        if pa == {} or pa == [] or pa is None:
            mdp.pop("Pa", None)
    return out


def _execute_basin_series(args: argparse.Namespace) -> int:
    """Compare spine ``input.pkl`` ``NS``…``NH`` to MATLAB-owned ``matlab_payload``."""
    import numpy as np
    from scipy.io import loadmat

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    for label, path in (("PKL", pkl_path), ("MAT", mat_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL spine basin compare] missing {label}: {path}", file=sys.stderr)
            return 2

    blob = _load_spine_pkl(pkl_path)
    _assert_payload_mat_meta(
        mat_path,
        require_matlab_authority=bool(getattr(args, "require_matlab_authority", False)),
    )
    raw = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)

    site = str(args.site)
    boundary = blob.get("boundary", "after_basin")
    print(
        f"[OPTIM1FULL spine basin compare] site={site} boundary={boundary}",
        file=sys.stderr,
    )
    print(f"[OPTIM1FULL spine basin compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL spine basin compare] MAT={mat_path}", file=sys.stderr)

    for key in _BASIN_SERIES_KEYS:
        if key not in blob:
            raise KeyError(f"spine basin pkl missing {key!r}")
        if key not in raw:
            raise KeyError(f"payload mat missing {key!r}: {mat_path}")
        py = np.asarray(blob[key], dtype=np.float64).reshape(-1)
        mat = np.asarray(raw[key], dtype=np.float64).reshape(-1)
        if py.shape != mat.shape:
            raise AssertionError(f"{key}: shape py={py.shape} mat={mat.shape}")
        if not np.array_equal(py, mat):
            diff = np.max(np.abs(py - mat)) if py.size else 0.0
            raise AssertionError(f"{key}: values differ (max abs diff={diff})")
        print(f"[OPTIM1FULL spine basin compare] {key} OK len={py.size}", file=sys.stderr)

    print("[OPTIM1FULL spine basin compare] PASS", file=sys.stderr)
    return 0


def _execute_post_sort_payload(args: argparse.Namespace) -> int:
    """Compare spine ``input.pkl`` ``b1``/``hid`` to MATLAB-owned ``matlab_payload``."""
    import numpy as np
    from scipy.io import loadmat

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    for label, path in (("PKL", pkl_path), ("MAT", mat_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL spine post_sort compare] missing {label}: {path}", file=sys.stderr)
            return 2

    blob = _load_spine_pkl(pkl_path)
    _assert_payload_mat_meta(
        mat_path,
        require_matlab_authority=bool(getattr(args, "require_matlab_authority", False)),
    )
    raw = loadmat(str(mat_path), squeeze_me=False, struct_as_record=False)

    site = str(args.site)
    boundary = blob.get("boundary", "after_post_sort")
    print(
        f"[OPTIM1FULL spine post_sort compare] site={site} boundary={boundary}",
        file=sys.stderr,
    )
    print(f"[OPTIM1FULL spine post_sort compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL spine post_sort compare] MAT={mat_path}", file=sys.stderr)

    for key in _POST_SORT_PAYLOAD_KEYS:
        if key not in blob:
            raise KeyError(f"spine post_sort pkl missing {key!r}")
        if key not in raw:
            raise KeyError(f"payload mat missing {key!r}: {mat_path}")
        py = np.asarray(blob[key])
        mat = np.asarray(raw[key])
        if key == "hid":
            py = np.asarray(py, dtype=np.int64).ravel(order="F")
            mat = np.asarray(mat, dtype=np.int64).ravel(order="F")
            if py.shape != mat.shape:
                raise AssertionError(f"{key}: shape py={py.shape} mat={mat.shape}")
            if not np.array_equal(py, mat):
                raise AssertionError(f"{key}: values differ")
        else:
            py = np.asarray(py, dtype=np.float64)
            mat = np.asarray(mat, dtype=np.float64)
            if py.shape != mat.shape:
                raise AssertionError(f"{key}: shape py={py.shape} mat={mat.shape}")
            if not np.allclose(py, mat, rtol=0.0, atol=0.0):
                # uint8 authority vs float spine — exact after cast
                if not np.array_equal(py, mat):
                    diff = float(np.max(np.abs(py - mat))) if py.size else 0.0
                    raise AssertionError(f"{key}: values differ (max abs diff={diff})")
        print(
            f"[OPTIM1FULL spine post_sort compare] {key} OK shape={tuple(py.shape)}",
            file=sys.stderr,
        )

    print("[OPTIM1FULL spine post_sort compare] PASS", file=sys.stderr)
    return 0


def _execute_structure_f(args: argparse.Namespace) -> int:
    """Compare spine ``input.pkl`` ``F`` to MATLAB-owned ``matlab_payload``."""
    import numpy as np
    from scipy.io import loadmat

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    for label, path in (("PKL", pkl_path), ("MAT", mat_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL spine structure compare] missing {label}: {path}", file=sys.stderr)
            return 2

    blob = _load_spine_pkl(pkl_path)
    _assert_payload_mat_meta(
        mat_path,
        require_matlab_authority=bool(getattr(args, "require_matlab_authority", False)),
    )
    raw = loadmat(str(mat_path), squeeze_me=False, struct_as_record=False)

    site = str(args.site)
    boundary = blob.get("boundary", "nr_game_32")
    print(
        f"[OPTIM1FULL spine structure compare] site={site} boundary={boundary}",
        file=sys.stderr,
    )
    print(f"[OPTIM1FULL spine structure compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL spine structure compare] MAT={mat_path}", file=sys.stderr)

    if "F" not in blob:
        raise KeyError("spine structure pkl missing 'F'")
    if "F" not in raw:
        raise KeyError(f"payload mat missing F: {mat_path}")
    py = np.asarray(blob["F"], dtype=np.float64)
    mat = np.asarray(raw["F"], dtype=np.float64)
    if py.shape != mat.shape:
        raise AssertionError(f"F: shape py={py.shape} mat={mat.shape}")
    if not np.allclose(py, mat, rtol=0.0, atol=1e-10):
        diff = float(np.max(np.abs(py - mat))) if py.size else 0.0
        raise AssertionError(f"F: values differ (max abs diff={diff})")
    print(f"[OPTIM1FULL spine structure compare] F OK shape={tuple(py.shape)}", file=sys.stderr)
    print("[OPTIM1FULL spine structure compare] PASS", file=sys.stderr)
    return 0


def _execute(args: argparse.Namespace) -> int:
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _emit_pdp_top_level_inventory,
        _emit_pdp_top_level_key_diff,
        _emit_nested_type_walk_pdp,
    )

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    for label, path in (("PKL", pkl_path), ("MAT", mat_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL spine PDP compare] missing {label}: {path}", file=sys.stderr)
            return 2

    blob = _load_spine_pkl(pkl_path)
    if "PDP" not in blob:
        raise KeyError(f"spine pkl must contain PDP for PDP compare: {pkl_path}")
    py_pdp = blob["PDP"]
    _assert_spine_mat_meta(
        mat_path,
        allow_matlab_fence_capture=bool(getattr(args, "allow_matlab_fence_capture", False)),
        require_matlab_authority=bool(getattr(args, "require_matlab_authority", False)),
    )
    mat_pdp = _load_spine_mat_pdp(mat_path)
    _normalize_spine_mat_pa_for_align(mat_pdp)

    site = str(args.site)
    boundary = blob.get("boundary", "vb_call1")
    print(
        f"[OPTIM1FULL spine PDP compare] site={site} boundary={boundary}",
        file=sys.stderr,
    )
    print(f"[OPTIM1FULL spine PDP compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL spine PDP compare] MAT={mat_path}", file=sys.stderr)

    _emit_pdp_top_level_inventory("PKL PDP", py_pdp)
    _emit_pdp_top_level_inventory("MATLAB PDP", mat_pdp)
    _emit_pdp_top_level_key_diff(py_pdp, mat_pdp)

    py_cmp = entry12_align_mdp_to_mat_workspace(copy.deepcopy(py_pdp), mat_pdp)
    _normalize_spine_ss_grids(py_cmp)
    mat_cmp = _spine_mat_pdp_for_value_assert(mat_pdp)
    _emit_nested_type_walk_pdp(py_cmp, mat_cmp)

    if args.report_type_mismatches_only:
        print("[OPTIM1FULL spine PDP compare] report-only — skip value assert", file=sys.stderr)
        return 0

    _compare_pair(
        "spine fence PDP",
        py_cmp,
        mat_cmp,
        "PDP",
        report_only=False,
        coerce_sparse=bool(args.coerce_sparse_to_dense),
    )
    print("[OPTIM1FULL spine PDP compare] PASS", file=sys.stderr)
    return 0


def _execute_pkl_to_pkl(args: argparse.Namespace) -> int:
    """Resume-proof: compare two spine ``input.pkl`` artifacts (same Python driver lineage)."""
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _emit_pdp_top_level_inventory,
        _emit_pdp_top_level_key_diff,
        _emit_nested_type_walk_pdp,
    )

    pkl_path = args.pkl.resolve()
    ref_path = args.ref_pkl.resolve()
    for label, path in (("PKL", pkl_path), ("REF", ref_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL spine PDP compare] missing {label}: {path}", file=sys.stderr)
            return 2

    blob = _load_spine_pkl(pkl_path)
    ref_blob = _load_spine_pkl(ref_path)
    if "PDP" not in blob or "PDP" not in ref_blob:
        raise KeyError("pkl_to_pkl resume proof requires PDP in both spine pkls")
    py_pdp = copy.deepcopy(blob["PDP"])
    ref_pdp = copy.deepcopy(ref_blob["PDP"])
    _normalize_spine_ss_grids(py_pdp)
    _normalize_spine_ss_grids(ref_pdp)

    site = str(args.site)
    boundary = blob.get("boundary", "vb_call1")
    print(
        f"[OPTIM1FULL spine PDP compare] mode=pkl_to_pkl site={site} boundary={boundary}",
        file=sys.stderr,
    )
    print(f"[OPTIM1FULL spine PDP compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL spine PDP compare] REF={ref_path}", file=sys.stderr)
    print(
        f"[OPTIM1FULL spine PDP compare] resume_from={blob.get('resume_from')} "
        f"resume_mode={blob.get('resume_mode')}",
        file=sys.stderr,
    )

    _emit_pdp_top_level_inventory("PKL PDP", py_pdp)
    _emit_pdp_top_level_inventory("REF PDP", ref_pdp)
    _emit_pdp_top_level_key_diff(py_pdp, ref_pdp)
    _emit_nested_type_walk_pdp(py_pdp, ref_pdp)

    if args.report_type_mismatches_only:
        print("[OPTIM1FULL spine PDP compare] report-only — skip value assert", file=sys.stderr)
        return 0

    _compare_pair(
        "spine fence PDP (resume vs cold)",
        py_pdp,
        ref_pdp,
        "PDP",
        report_only=False,
        coerce_sparse=bool(args.coerce_sparse_to_dense),
    )
    print("[OPTIM1FULL spine PDP compare] PASS (pkl_to_pkl)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site
    from tests.demo1.optim1full.optim1full_plot_sites import (
        SITE_KIND_BASIN_SERIES,
        SITE_KIND_POST_SORT_ORBITS,
        SITE_KIND_STRUCTURE_F,
        optim1full_plot_site_kind,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site", default="dem_generative_ai", help="§13 plot site_id")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    p.add_argument(
        "--ref-pkl",
        type=Path,
        default=None,
        help="resume proof: compare --pkl PDP to reference cold-start spine .pkl (no .mat)",
    )
    p.add_argument(
        "--coerce-sparse-to-dense",
        action="store_true",
        help="densify sparse leaves before nested assert",
    )
    p.add_argument(
        "--report-type-mismatches-only",
        action="store_true",
        help="inventory + type walk only; no value assert",
    )
    p.add_argument(
        "--allow-matlab-fence-capture",
        action="store_true",
        help="accept metaPdp.capture=capture_optim1full_dem_generative_ai (row 4 MATLAB fence audit)",
    )
    p.add_argument(
        "--require-matlab-authority",
        action="store_true",
        help=(
            "genuine plot-parity: require the .mat to be the INDEPENDENT MATLAB-owned fence "
            "(capture=capture_optim1full_plot_fence); REFUSE a Python-resaved .mat as authority. "
            "Defaults --mat to the site's authority_mat (matlab_pdp or matlab_payload)."
        ),
    )
    args = p.parse_args(argv)

    paths = optim1full_plot_paths_for_site(str(args.site))
    if args.pkl is None:
        args.pkl = paths["input_pkl"]
    if args.ref_pkl is None and args.mat is None:
        if bool(getattr(args, "require_matlab_authority", False)):
            args.mat = paths.get("authority_mat", paths["matlab_pdp_mat"])
        else:
            args.mat = paths["input_mat"]

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "OPTIM1FULL — spine fence PDP pairing compare"
        + (" (`.pkl` vs `.pkl` resume proof).\n\n" if args.ref_pkl is not None else " (`.pkl` vs `.mat`).\n\n")
        + f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out = sys.stdout
        tee_err = sys.stderr
        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            if args.ref_pkl is not None:
                return _execute_pkl_to_pkl(args)
            site_kind = optim1full_plot_site_kind(str(args.site))
            if site_kind == SITE_KIND_BASIN_SERIES:
                return _execute_basin_series(args)
            if site_kind == SITE_KIND_POST_SORT_ORBITS:
                return _execute_post_sort_payload(args)
            if site_kind == SITE_KIND_STRUCTURE_F:
                return _execute_structure_f(args)
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout = tee_out
            sys.stderr = tee_err


if __name__ == "__main__":
    raise SystemExit(main())
