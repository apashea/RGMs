#!/usr/bin/env python3
"""DEMO2 lane B — compare Python post–NR ``MDP`` vs MATLAB authority.

**Authority:** ``fixtures/DEMAtariIII_demo2_MDP_pre_call3_post_nr.mat`` variable
``MDP_pre_post_nr`` (after full ``NR=32`` loop, pre call **3** sort).

**Python:** ``fixtures/DEMAtariIII_demo2_post_nr_mdp.pkl`` field ``mdp`` from
``demo2_run_post_nr_isolated.py``.

**Report:** ``matlab_custom/demo2_compare_post_nr_mdp_output.txt``

**Prerequisite:** Run ``matlab_custom/demo2/dump_MDP_pre_call3_post_nr.m`` then
``python demo2_run_post_nr_isolated.py``.

See ``Atari_example.md`` § **ENTRY DEMO2 FULL ATARI** — lane B compare matrix.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "demo2_compare_post_nr_mdp_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_DEMO2_POST_NR_MDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "fixtures" / "DEMAtariIII_demo2_post_nr_mdp.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_DEMO2_POST_NR_AUTHORITY_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        Path(__file__).resolve().parent
        / "fixtures"
        / "DEMAtariIII_demo2_MDP_pre_call3_post_nr.mat"
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
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng = matlab.engine.start_matlab()
    try:
        eng.addpath(str(repo), nargout=0)
        eng.addpath(str(repo / "matlab_src"), nargout=0)
        eng.addpath(str(dem_path), nargout=0)
        eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
        eng.eval(f"load('{str(mat_path.resolve()).replace(chr(92), '/')}');", nargout=0)
        return _pull_mdp_from_matlab(eng, "MDP_pre_post_nr")
    finally:
        eng.quit()


def _execute(args: argparse.Namespace) -> int:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(
            f"missing PKL: {pkl_path}\nRun: python demo2_run_post_nr_isolated.py"
        )
    if not mat_path.is_file():
        raise FileNotFoundError(
            f"missing authority mat: {mat_path}\n"
            "Run: matlab_custom/demo2/dump_MDP_pre_call3_post_nr.m"
        )

    blob = _load_py_blob(pkl_path)
    py_mdp = blob["mdp"]
    if not isinstance(py_mdp, list):
        raise TypeError(f"mdp must be list in {pkl_path}")
    mat_mdp = _load_mat_mdp(mat_path)

    print(f"[DEMO2 post-NR compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[DEMO2 post-NR compare] MAT authority={mat_path}", file=sys.stderr)
    print(
        f"[DEMO2 post-NR compare] levels py={len(py_mdp)} mat={len(mat_mdp)} "
        f"lane_b_vb_replay_call2={blob.get('lane_b_vb_replay_call2')}",
        file=sys.stderr,
    )

    _assert_mdp_full_equal(py_mdp, mat_mdp, k=0)
    print("OK: MDP parity (DEMO2 post-NR loop)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="DEMO2 lane B post-NR MDP compare")
    p.add_argument("--pkl", type=Path, default=None, help="Python post-NR MDP PKL")
    p.add_argument("--mat", type=Path, default=None, help="MATLAB authority .mat")
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = _default_post_pkl()
    if args.mat is None:
        args.mat = _default_authority_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "DEMO2 lane B — compare Python post–NR ``MDP`` vs ``MDP_pre_post_nr`` authority.\n\n"
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
