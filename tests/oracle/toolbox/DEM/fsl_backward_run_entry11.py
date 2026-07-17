#!/usr/bin/env python3
"""DEPRECATED for routine Entry 11 sign-off — runs full ``entry_stop=11`` (~30+ min).

Use ``fsl_backward_run_entry11_isolated.py`` + MATLAB pre-Entry-11 boundary PKL.

FSL backward 3 (integration only) — ``run_dem_atariiii(entry_stop=11)`` → ``ctx`` PKL.

Default: ``fixtures/DEMAtariIII_fsl_backward_entry11_ctx.pkl``.

Set ``RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS=1`` (recommended) to replay **FSL backward 1b**
``dem_atari_rand_buf`` — **not** Entry 12 ``vb_rand_buf``.

Report: ``matlab_custom/fsl_backward_run_entry11_output.txt``

See ``Atari_example.md`` § **FSL backward validation (Entry 11 → 1)**.
"""
from __future__ import annotations

import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_run_entry11_output.txt"


def _default_pkl_out() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY11_CONTEXT_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry11_ctx.pkl"


def _replay_enabled() -> bool:
    v = str(os.getenv("RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS", "")).strip().lower()
    return v in ("1", "true", "yes", "on")


def main() -> int:
    from python_src.toolbox.DEM.DEM_AtariIII import (
        get_dem_atariiii_run_last_label,
        run_dem_atariiii,
    )
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        fsl_backward_replay_matlab_draws,
        fsl_entry11_driver_env,
        load_dem_atari_rand_buf,
    )

    out_pkl = _default_pkl_out()
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    report_path = _report_path()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    code = 0
    with report_path.open("w", encoding="utf-8") as report_f:
        report_f.write(__doc__ or "")
        report_f.write(f"\n--- RUN OUTPUT — {report_path} ---\n")
        report_f.flush()
        old_err, old_out = sys.stderr, sys.stdout

        class _Tee:
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

        sys.stderr = _Tee(old_err, report_f)
        sys.stdout = _Tee(old_out, report_f)
        try:
            with fsl_entry11_driver_env(deadline_minutes="60"):
                if _replay_enabled():
                    buf, k_11 = load_dem_atari_rand_buf()
                    print(f"[FSL backward 3] replay K_11={k_11}", file=sys.stderr)
                    with fsl_backward_replay_matlab_draws(k_11, buf) as ctr:
                        ctx = run_dem_atariiii(entry_stop=11)
                    used = int(ctr[0])
                    if used != k_11:
                        print(
                            f"[FSL backward 3] FAIL: used {used} draws, expected K_11={k_11}",
                            file=sys.stderr,
                        )
                        code = 1
                else:
                    print(
                        "[FSL backward 3] Python-native RNG — set "
                        "RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS=1 for sign-off",
                        file=sys.stderr,
                    )
                    ctx = run_dem_atariiii(entry_stop=11)

            with open(out_pkl, "wb") as f:
                pickle.dump(ctx, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"[FSL backward 3] wrote {out_pkl}", file=sys.stderr)
        except Exception:
            print(
                f"[FSL backward 3] last segment = {get_dem_atariiii_run_last_label()!r}",
                file=sys.stderr,
            )
            traceback.print_exc()
            code = 1
        finally:
            sys.stderr, sys.stdout = old_err, old_out

    return code


if __name__ == "__main__":
    raise SystemExit(main())
