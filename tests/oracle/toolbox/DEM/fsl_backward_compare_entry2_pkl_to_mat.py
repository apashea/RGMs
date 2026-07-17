#!/usr/bin/env python3
"""FSL backward — Entry 2: compare Python post-pong vs MATLAB authority.

**Authority:** ``GDP_post_entry2``, ``RGB_post_entry2``, ``S_post_entry2`` in
``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat`` (append via
``patch_entry2_authority_to_pre_entry10_mat.m``).

**Python:** ``fixtures/DEMAtariIII_fsl_backward_entry2_post.pkl``.

**Report:** ``matlab_custom/fsl_backward_compare_entry2_output.txt``
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
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry2_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY2_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry2_post.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY2_AUTHORITY_MAT_PATH", "")).strip()
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


def _execute(args: argparse.Namespace) -> int:
    import matlab.engine

    from tests.oracle.toolbox.DEM.fsl_backward_assert_gdp import assert_entry2_bundle_equal_eng

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing authority mat: {mat_path}")

    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "gdp" not in blob:
        raise KeyError(f"expected dict with gdp in {pkl_path}")

    mat_s = mat_path.as_posix()
    eng = matlab.engine.start_matlab()
    try:
        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

        dem_path = configure_dem_matlab_engine(eng, _REPO)
        eng.eval(f"load('{mat_s}');", nargout=0)
        for key in (
            "GDP_post_entry2",
            "RGB_post_entry2",
            "S_post_entry2",
            "hid_post_entry2",
            "cid_post_entry2",
            "con_post_entry2",
        ):
            ex = int(np.asarray(eng.eval(f"exist('{key}','var')"), dtype=np.int64).reshape(-1)[0])
            if ex == 0:
                raise KeyError(
                    f"{mat_path} missing {key} — run patch_entry2_authority_to_pre_entry10_mat.m"
                )
        print(f"[FSL backward Entry 2] PKL post={pkl_path}", file=sys.stderr)
        print(f"[FSL backward Entry 2] MAT authority={mat_path}", file=sys.stderr)
        print(
            f"[FSL backward Entry 2] lane={blob.get('validation_lane')} "
            f"nr={blob.get('nr')} nc={blob.get('nc')} nd={blob.get('nd')}",
            file=sys.stderr,
        )
        assert_entry2_bundle_equal_eng(eng, blob)
    finally:
        eng.quit()

    print("OK: GDP_post_entry2, RGB_post_entry2.G, S_post_entry2 parity (FSL backward Entry 2)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 2 compare")
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
        "FSL backward — Entry 2: compare Python post-pong vs MATLAB authority.\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out, tee_err = sys.stdout, sys.stderr
        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = tee_out, tee_err


if __name__ == "__main__":
    raise SystemExit(main())
