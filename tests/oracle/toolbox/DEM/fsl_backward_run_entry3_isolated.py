#!/usr/bin/env python3
"""FSL backward — run Entry 3 only on ``rng(2)`` ledger (no ``entry_stop=3``).

Writes ``fixtures/DEMAtariIII_fsl_backward_entry3_post.pkl``.

**Sign-off (default):** ``RGMS_FSL_ENTRY3_MATLAB_GENERATE=1`` — Engine MATLAB
``spm_MDP_pong`` + ``spm_MDP_generate`` (``T=10000``, ``tau=1``); compare vs ``PDP_o`` / ``PDP_O``.

**Native ledger:** ``RGMS_FSL_ENTRY3_MATLAB_GENERATE=0`` + ``RGMS_FSL_ENTRY3_DRIVER_REPLAY=1`` —
``run_entry3_driver_ledger_replay`` (requires ``fsl_backward_preflight_rand_k_entry3.py``).

**Boundary-only native:** both flags ``0`` + GDP in ``DEMAtariIII_fsl_backward_MDP_pre_entry3.pkl``.

Compare with ``fsl_backward_compare_entry3_pkl_to_mat.py``.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY3_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry3_post.pkl"


def _authority_mat() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def _env_on(name: str, default: str = "1") -> bool:
    raw = str(os.getenv(name, default)).strip().lower()
    return raw not in ("0", "false", "no", "off")


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry3 import (
        run_entry3_driver_ledger_replay,
        run_entry3_from_boundary,
        run_entry3_matlab_generate,
    )

    mat_path = _authority_mat()
    if not mat_path.is_file():
        print(f"[FSL backward Entry 3 isolated] missing {mat_path}", file=sys.stderr)
        return 2

    if _env_on("RGMS_FSL_ENTRY3_DRIVER_REPLAY") and not _env_on(
        "RGMS_FSL_ENTRY3_MATLAB_GENERATE", default="0"
    ):
        print(
            "[FSL backward Entry 3 isolated] driver ledger + dem_atari_rand_buf replay (K_3)",
            file=sys.stderr,
        )
        try:
            out_payload = run_entry3_driver_ledger_replay()
        except FileNotFoundError as exc:
            print(f"[FSL backward Entry 3 isolated] {exc}", file=sys.stderr)
            return 2
    elif _env_on("RGMS_FSL_ENTRY3_MATLAB_GENERATE"):
        import matlab.engine

        eng = matlab.engine.start_matlab()
        try:
            from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

            dem_path = configure_dem_matlab_engine(eng, _REPO)
            print(
                "[FSL backward Entry 3 isolated] RGMS_FSL_ENTRY3_MATLAB_GENERATE=1 "
                "(Engine rng(2) pong + spm_MDP_generate)",
                file=sys.stderr,
            )
            out_payload = run_entry3_matlab_generate(eng, authority_mat_path=mat_path)
        finally:
            eng.quit()
    else:
        pre = _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry3.pkl"
        if not pre.is_file():
            print(
                f"[FSL backward Entry 3 isolated] native path needs GDP boundary in {pre}\n"
                "Run materialize or use RGMS_FSL_ENTRY3_MATLAB_GENERATE=1",
                file=sys.stderr,
            )
            return 2
        with pre.open("rb") as f:
            boundary = pickle.load(f)
        if "gdp" not in boundary:
            raise KeyError(
                f"{pre} missing gdp — native Entry 3 requires GDP pickle or MATLAB generate lane"
            )
        print("[FSL backward Entry 3 isolated] native spm_MDP_generate", file=sys.stderr)
        out_payload = run_entry3_from_boundary(boundary)

    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "validation": {
                    "lane": "fsl_backward_entry3",
                    "authority_var": "PDP_o, PDP_O",
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 3 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
