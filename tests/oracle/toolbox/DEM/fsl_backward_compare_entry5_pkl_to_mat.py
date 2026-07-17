#!/usr/bin/env python3
"""FSL backward — Entry 5: compare Python post-forget ``MDP`` vs MATLAB authority.

**Authority:** ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` variable
``MDP_pre_entry7`` (post Entry 5 forget on ``rng(2)`` ledger; pre Entry 7 merges).

**Python:** ``fixtures/DEMAtariIII_fsl_backward_entry5_post.pkl`` field ``mdp``.

**Report:** ``matlab_custom/fsl_backward_compare_entry5_output.txt``
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

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry5_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY5_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry5_post.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY5_AUTHORITY_MAT_PATH", "")).strip()
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
    if not isinstance(blob, dict) or "mdp" not in blob:
        raise KeyError(f"expected dict with mdp in {pkl_path}")
    return blob


def _load_mat_mdp(mat_path: Path) -> list[dict[str, Any]]:
    import matlab.engine

    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    repo = _REPO
    eng = matlab.engine.start_matlab()
    try:
        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

        dem_path = configure_dem_matlab_engine(eng, repo)
        eng.eval(f"load('{str(mat_path.resolve()).replace(chr(92), '/')}');", nargout=0)
        if int(
            np.asarray(eng.eval("exist('MDP_pre_entry7','var')"), dtype=np.int64).reshape(-1)[0]
        ) != 1:
            raise KeyError(
                f"{mat_path} missing MDP_pre_entry7 — re-run dump_MDP_pre_entry10.m."
            )
        return _pull_mdp_from_matlab(eng, "MDP_pre_entry7")
    finally:
        eng.quit()


def _execute(args: argparse.Namespace) -> int:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing authority mat: {mat_path}")

    blob = _load_py_blob(pkl_path)
    py_mdp = blob["mdp"]
    if not isinstance(py_mdp, list):
        raise TypeError(f"mdp must be list in {pkl_path}")
    mat_mdp = _load_mat_mdp(mat_path)

    print(f"[FSL backward Entry 5] PKL post-Entry-5={pkl_path}", file=sys.stderr)
    print(
        f"[FSL backward Entry 5] MAT authority (MDP_pre_entry7)={mat_path}",
        file=sys.stderr,
    )
    print(
        f"[FSL backward Entry 5] levels py={len(py_mdp)} mat={len(mat_mdp)} "
        f"Nm={blob.get('Nm')} Ne={blob.get('Ne')}",
        file=sys.stderr,
    )

    _assert_mdp_full_equal(py_mdp, mat_mdp, k=5)
    print("OK: MDP parity (FSL backward Entry 5)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 5 MDP compare")
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
        "FSL backward — Entry 5: compare Python post-forget ``MDP`` vs "
        "``MDP_pre_entry7`` authority.\n\n"
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
