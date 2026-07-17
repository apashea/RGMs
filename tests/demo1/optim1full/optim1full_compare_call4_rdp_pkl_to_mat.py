#!/usr/bin/env python3
"""OPTIM1FULL Product B — compare call-4 assembled RDP vs MATLAB on same ``MDP_post_nr``.

Call-4 counterpart of ``optim1full_compare_call3_rdp_pkl_to_mat.py``. Call-4 adds
``spm_RDP_MI`` after ``spm_RDP_sort`` (before goals / costs / ``spm_mdp2rdp``).

**Authority:** MATLAB assembly on ``DEMAtariIII_optim1full_MDP_post_nr.mat`` (Engine):
``spm_RDP_sort`` → ``spm_RDP_MI`` → ``spm_set_goals`` → ``spm_set_costs`` → ``spm_mdp2rdp``.
**Python:** ``DEMAtariIII_optim1full_call4_rdp.pkl`` from
``optim1full_run_call4_assembly_isolated.py``.
**Report:** ``matlab_custom/optim1full_compare_call4_rdp_output.txt``
"""
from __future__ import annotations

import argparse
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "optim1full_compare_call4_rdp_output.txt"


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


def _matlab_call4_rdp_from_post_nr_mat(mat_path: Path, *, c_val: float, ns: float) -> dict:
    """Mirror ``entry12_dem_call4_rdp_post_loop_`` on frozen ``MDP_post_nr``."""
    import matlab.engine
    from scipy.io import loadmat

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        eng.eval(f"C = {c_val};", nargout=0)
        eng.eval(
            "RDP = spm_RDP_sort(MDP_post_nr); "
            "RDP = spm_RDP_MI(RDP); "
            "RDP = spm_set_goals(RDP,[2,3],[C,-C]); "
            "RDP = spm_set_costs(RDP,[2,3],[C,-C]); "
            f"RDP = spm_mdp2rdp(RDP,0,{1.0 / ns}); "
            "RDP.T = 128;",
            nargout=0,
        )
        tmp = _REPO / "matlab_custom" / "_optim1full_call4_rdp_ref.mat"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp_posix = str(tmp.resolve()).replace("\\", "/")
        eng.eval(f"save('{tmp_posix}','RDP');", nargout=0)
        raw = loadmat(str(tmp))
        return mat_nested_to_py(raw["RDP"])
    finally:
        eng.quit()


def _execute(args: argparse.Namespace) -> int:
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_call4_rdp_pkl,
        optim1full_mdp_post_nr_mat,
    )
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    for label, path in (("PKL", pkl_path), ("MDP_post_nr mat", mat_path)):
        if not path.is_file():
            print(f"[OPTIM1FULL call4 compare] missing {label}: {path}", file=sys.stderr)
            return 2

    with pkl_path.open("rb") as f:
        payload = pickle.load(f)
    rdp_py = payload["rdp"]
    c_val = float(payload.get("c_val", atari_c_value()))
    ns = float(payload.get("ns", 256.0))

    print(f"[OPTIM1FULL call4 compare] PKL={pkl_path}", file=sys.stderr)
    print(f"[OPTIM1FULL call4 compare] MAT={mat_path}", file=sys.stderr)
    print(
        "[OPTIM1FULL call4 compare] MATLAB path = sort → spm_RDP_MI → goals → costs → mdp2rdp",
        file=sys.stderr,
    )

    rdp_mat = _matlab_call4_rdp_from_post_nr_mat(mat_path, c_val=c_val, ns=ns)
    py_vb = entry12_rdp_for_vb_from_mat_nested(rdp_py)
    mat_vb = entry12_rdp_for_vb_from_mat_nested(rdp_mat)
    _assert_nested_rdp_equal(py_vb, mat_vb, "OPTIM1FULL call4 VB-input RDP")
    print("[OPTIM1FULL call4 compare] PASS", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_call4_rdp_pkl,
        optim1full_mdp_post_nr_mat,
    )

    p = argparse.ArgumentParser(description="OPTIM1FULL Product B call-4 RDP assembly compare")
    p.add_argument("--pkl", type=Path, default=None)
    p.add_argument("--mat", type=Path, default=None)
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = optim1full_call4_rdp_pkl()
    if args.mat is None:
        args.mat = optim1full_mdp_post_nr_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8") as rf:
        tee = _TeeIO(sys.stdout, rf)
        tee_err = _TeeIO(sys.stderr, rf)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = tee, tee_err
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = old_out, old_err


if __name__ == "__main__":
    raise SystemExit(main())
