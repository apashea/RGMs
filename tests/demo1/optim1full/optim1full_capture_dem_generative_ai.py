#!/usr/bin/env python3
"""OPTIM1FULL W1 — ``dem_generative_ai`` fixture capture (one process).

**Phase 1 (MATLAB):** ``capture_optim1full_dem_generative_ai`` — Model **B** ledger replay
through ``entries_1_11`` + ``vb_call1`` → ``DEMAtariIII_optim1full_dem_generative_ai_input.mat``
+ ``…_oracle.mat``.

**Phase 2 (Python):** same ledger boundary ``stop_after='vb_call1'`` → ``…_input.pkl``.

See ``OPTIM1FULL.md`` § W1 / ``Atari_plotting.md`` § **13** row **4**.
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_SITE_ID = "dem_generative_ai"


def _log_line(log_fp: TextIO | None, msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
    if log_fp is not None:
        log_fp.write(msg + "\n")
        log_fp.flush()


def _site_paths() -> dict[str, Path]:
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site

    return optim1full_plot_paths_for_site(_SITE_ID)


def _set_matlab_fixture_env(eng: Any) -> None:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fix = str(optim1full_fixtures_dir().resolve())
    eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
    eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix, nargout=0)


def _capture_matlab(log_fp: TextIO | None) -> dict[str, str]:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

    paths = _site_paths()
    for key in ("input_mat", "oracle_mat"):
        if paths[key].is_file():
            paths[key].unlink()

    _log_line(log_fp, "[optim1full_capture_dem_generative_ai] phase 1: MATLAB ledger replay + 12PLOT")
    t0 = time.perf_counter()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _set_matlab_fixture_env(eng)
        eng.cd(str(_REPO), nargout=0)
        eng.addpath(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_dem_generative_ai');",
            nargout=0,
        )
    finally:
        eng.quit()

    missing = [f"{k}={p}" for k, p in paths.items() if k in ("input_mat", "oracle_mat") and not p.is_file()]
    if missing:
        raise FileNotFoundError("MATLAB capture did not write expected fixtures:\n" + "\n".join(missing))

    wall_s = time.perf_counter() - t0
    _log_line(log_fp, f"[optim1full_capture_dem_generative_ai] phase 1 done wall_s={wall_s:.1f}")
    return {
        "input_mat": str(paths["input_mat"].resolve()),
        "oracle_mat": str(paths["oracle_mat"].resolve()),
        "matlab_wall_s": f"{wall_s:.3f}",
    }


def _capture_python_pkl(*, deadline_minutes: str, log_fp: TextIO | None) -> dict[str, str]:
    from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim1full_parity import (
        run_optim1full_optim1_through_mdp_pre,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env

    paths = _site_paths()
    pkl_out = paths["input_pkl"]
    pkl_out.parent.mkdir(parents=True, exist_ok=True)

    _log_line(
        log_fp,
        f"[optim1full_capture_dem_generative_ai] phase 2: Python stop_after=vb_call1 → {pkl_out.name}",
    )
    buf, manifest = load_validated_optim1full_ledger()
    t0 = time.perf_counter()
    with optim1full_signoff_env(deadline_minutes=str(deadline_minutes)):
        ctx = run_optim1full_optim1_through_mdp_pre(
            buf,
            manifest,
            deadline_minutes=str(deadline_minutes),
            stop_after="vb_call1",
        )
    if "PDP" not in ctx:
        raise RuntimeError("vb_call1 segment did not produce ctx['PDP']")
    with pkl_out.open("wb") as f:
        pickle.dump({"PDP": ctx["PDP"]}, f, protocol=pickle.HIGHEST_PROTOCOL)
    wall_s = time.perf_counter() - t0
    _log_line(log_fp, f"[optim1full_capture_dem_generative_ai] phase 2 wrote {pkl_out} wall_s={wall_s:.1f}")
    return {
        "input_pkl": str(pkl_out.resolve()),
        "python_wall_s": f"{wall_s:.3f}",
        "vb_call1_k": str(manifest.segment("vb_call1").k),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--deadline-minutes", default="240", help="entries_1_11 + vb_call1 budget")
    p.add_argument("--matlab-only", action="store_true", help="phase 1 only")
    p.add_argument("--python-only", action="store_true", help="phase 2 only (requires input.mat)")
    args = p.parse_args(argv)

    if args.matlab_only and args.python_only:
        print("[optim1full_capture_dem_generative_ai] choose at most one phase flag", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _REPO / "logs" / f"optim1full_capture_dem_generative_ai_{stamp}.log"
    manifest: dict[str, Any] = {
        "capture_script": "optim1full_capture_dem_generative_ai.py",
        "site_id": _SITE_ID,
        "timestamp": stamp,
        "deadline_minutes": str(args.deadline_minutes),
    }

    with log_path.open("w", encoding="utf-8") as log_fp:
        _log_line(log_fp, f"[optim1full_capture_dem_generative_ai] log {log_path}")
        if not args.python_only:
            manifest["matlab"] = _capture_matlab(log_fp)
        if not args.matlab_only:
            mat_path = _site_paths()["input_mat"]
            if not mat_path.is_file():
                _log_line(log_fp, f"[optim1full_capture_dem_generative_ai] missing {mat_path} — run phase 1 first")
                return 2
            manifest["python"] = _capture_python_pkl(
                deadline_minutes=str(args.deadline_minutes),
                log_fp=log_fp,
            )
        _log_line(log_fp, f"[optim1full_capture_dem_generative_ai] manifest: {manifest}")

    print(f"[optim1full_capture_dem_generative_ai] done log={log_path}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
