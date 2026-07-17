#!/usr/bin/env python3
"""FSL backward — Entry 3: compare Python ``PDP`` vs MATLAB authority.

**Authority:** ``PDP_o``, ``PDP_O`` in ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat``.

**Python:** ``fixtures/DEMAtariIII_fsl_backward_entry3_post.pkl`` field ``pdp``.

**Report:** ``matlab_custom/fsl_backward_compare_entry3_output.txt``
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry3_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY3_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry3_post.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY3_AUTHORITY_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    )


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

    def isatty(self) -> bool:
        return bool(getattr(self._streams[0], "isatty", lambda: False)())


def _pdp_o_from_loadmat(pdp_o_raw: Any) -> list[list[Any]]:
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    pdp = mat_nested_to_py(pdp_o_raw)
    if not isinstance(pdp, list):
        raise TypeError(f"PDP_O expected list rows, got {type(pdp).__name__}")
    out: list[list[Any]] = []
    for row in pdp:
        if not isinstance(row, list):
            raise TypeError("PDP_O row must be list of time columns")
        py_row: list[Any] = []
        for cell in row:
            arr = np.asarray(cell, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape((-1, 1), order="F")
            if arr.ndim == 0:
                arr = np.reshape(arr, (1, 1), order="F")
            py_row.append(arr)
        out.append(py_row)
    return out


def _assert_pdp_o_equal(py_o: np.ndarray, mat_o: np.ndarray) -> None:
    from tests.helpers.compare import assert_matlab_match

    assert_matlab_match(np.asarray(mat_o, dtype=np.float64), np.asarray(py_o, dtype=np.float64))


def _assert_pdp_O_equal(
    py_O: list[list[Any]],
    mat_O: list[list[Any]],
    *,
    max_cols: int | None = None,
) -> None:
    from tests.helpers.compare import assert_matlab_match

    if len(py_O) != len(mat_O):
        raise AssertionError(f"PDP.O row-count py={len(py_O)} mat={len(mat_O)}")
    for g, (py_row, mat_row) in enumerate(zip(py_O, mat_O)):
        n_cmp = len(py_row)
        if max_cols is not None:
            n_cmp = min(n_cmp, int(max_cols), len(mat_row))
        if len(py_row) < n_cmp or len(mat_row) < n_cmp:
            raise AssertionError(
                f"PDP.O row {g + 1} col-count py={len(py_row)} mat={len(mat_row)} need>={n_cmp}"
            )
        for t in range(n_cmp):
            pc, mc = py_row[t], mat_row[t]
            try:
                assert_matlab_match(
                    np.asarray(mc, dtype=np.float64),
                    np.asarray(pc, dtype=np.float64),
                )
            except AssertionError as exc:
                raise AssertionError(
                    f"PDP.O{{{g + 1},{t + 1}}} mismatch: {exc}"
                ) from exc


def _execute(args: argparse.Namespace) -> int:
    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing authority mat: {mat_path}")

    blob = _load_py_blob(pkl_path)
    pdp = blob["pdp"]
    raw = loadmat(str(mat_path), simplify_cells=True)
    for key in ("PDP_o", "PDP_O"):
        if key not in raw:
            raise KeyError(f"{mat_path} missing {key}")

    print(f"[FSL backward Entry 3] PKL post-Entry-3={pkl_path}", file=sys.stderr)
    print(f"[FSL backward Entry 3] MAT authority={mat_path}", file=sys.stderr)
    print(
        f"[FSL backward Entry 3] T={pdp.get('T')} o shape={np.asarray(pdp['o']).shape}",
        file=sys.stderr,
    )

    from python_src.toolbox.DEM.dem_atariiii_entry4 import ENTRY4_O_COLS

    _assert_pdp_o_equal(pdp["o"], raw["PDP_o"])
    mat_O = _pdp_o_from_loadmat(raw["PDP_O"])
    o_cols = int(blob.get("pdp", {}).get("O_cols_pulled", ENTRY4_O_COLS))
    _assert_pdp_O_equal(pdp["O"], mat_O, max_cols=o_cols)
    print(
        f"OK: PDP.o and PDP.O(:,1:{o_cols}) parity (FSL backward Entry 3)",
        file=sys.stderr,
    )
    return 0


def _load_py_blob(pkl_path: Path) -> dict[str, Any]:
    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "pdp" not in blob:
        raise KeyError(f"expected dict with pdp in {pkl_path}")
    return blob


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 3 PDP compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = _default_post_pkl()
    if args.mat is None:
        args.mat = _default_authority_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "FSL backward — Entry 3: compare Python ``PDP`` vs ``PDP_o`` / ``PDP_O`` authority.\n\n"
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
