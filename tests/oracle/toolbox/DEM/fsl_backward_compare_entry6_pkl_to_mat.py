#!/usr/bin/env python3
"""FSL backward — Entry 6: compare Python events/windows vs MATLAB authority.

**Authority:** ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` variables
``entry6_r``, ``entry6_c``, ``entry6_t_windows``.

**Python:** ``fixtures/DEMAtariIII_fsl_backward_entry6_post.pkl``.

**Report:** ``matlab_custom/fsl_backward_compare_entry6_output.txt``
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
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry6_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY6_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry6_post.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY6_AUTHORITY_MAT_PATH", "")).strip()
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


def _load_py_blob(pkl_path: Path) -> dict[str, Any]:
    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    for key in ("r", "c", "entry6_windows"):
        if key not in blob:
            raise KeyError(f"expected {key} in {pkl_path}")
    return blob


def _mat_entry6_authority(mat_path: Path) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    raw = loadmat(str(mat_path), simplify_cells=True)
    for key in ("entry6_r", "entry6_c", "entry6_t_windows"):
        if key not in raw:
            raise KeyError(
                f"{mat_path} missing {key} — run patch_entry6_authority_to_pre_entry10_mat.m "
                "or re-run dump_MDP_pre_entry10.m."
            )
    mat_r = np.asarray(raw["entry6_r"], dtype=np.int64).reshape(-1)
    mat_c = np.asarray(raw["entry6_c"], dtype=np.int64).reshape(-1)
    tw = raw["entry6_t_windows"]
    if isinstance(tw, np.ndarray) and tw.dtype == object:
        mat_t_list = [np.asarray(tw.flat[i], dtype=np.int64).reshape(-1) for i in range(tw.size)]
    elif isinstance(tw, list):
        mat_t_list = [np.asarray(t, dtype=np.int64).reshape(-1) for t in tw]
    else:
        mat_t_list = [np.asarray(tw, dtype=np.int64).reshape(-1)]
    return mat_r, mat_c, mat_t_list


def _py_window_t_vectors(windows: list[dict[str, Any]]) -> list[np.ndarray]:
    return [np.asarray(w["t"], dtype=np.int64).reshape(-1) for w in windows]


def _assert_entry6_equal(py_blob: dict[str, Any], mat_path: Path) -> None:
    py_r = np.asarray(py_blob["r"], dtype=np.int64).reshape(-1)
    py_c = np.asarray(py_blob["c"], dtype=np.int64).reshape(-1)
    py_t = _py_window_t_vectors(py_blob["entry6_windows"])
    mat_r, mat_c, mat_t = _mat_entry6_authority(mat_path)

    if not np.array_equal(py_r, mat_r):
        raise AssertionError(f"r mismatch py={py_r.size} mat={mat_r.size} first diff index")
    if not np.array_equal(py_c, mat_c):
        raise AssertionError(f"c mismatch py={py_c.size} mat={mat_c.size}")
    if len(py_t) != len(mat_t):
        raise AssertionError(f"n_windows py={len(py_t)} mat={len(mat_t)}")
    for i, (pt, mt) in enumerate(zip(py_t, mat_t)):
        if not np.array_equal(pt, mt):
            raise AssertionError(f"window[{i}] t mismatch py={pt} mat={mt}")


def _execute(args: argparse.Namespace) -> int:
    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing authority mat: {mat_path}")

    blob = _load_py_blob(pkl_path)
    print(f"[FSL backward Entry 6] PKL post-Entry-6={pkl_path}", file=sys.stderr)
    print(f"[FSL backward Entry 6] MAT authority={mat_path}", file=sys.stderr)
    print(
        f"[FSL backward Entry 6] n_windows={blob.get('n_windows')} "
        f"numel(r)={np.asarray(blob['r']).size}",
        file=sys.stderr,
    )

    _assert_entry6_equal(blob, mat_path)
    print("OK: Entry 6 r/c/window parity (FSL backward Entry 6)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 6 compare")
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
        "FSL backward — Entry 6: compare Python ``r``/``c``/windows vs "
        "``entry6_*`` authority.\n\n"
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
