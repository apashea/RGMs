#!/usr/bin/env python3
"""FSL backward Track A — integrated ``run_dem_atariiii`` 1–11 + Entry 12 VB.

**Entries 1–11:** ``RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS=1`` (default) — ``dem_atari_rand_buf`` through ``K_11``.

**Entry 12:** ``vb_rand_buf`` replay on ``spm_MDP_VB_XXX`` (canonical ``rgms_canonical`` tag).

Writes ``fixtures/DEMAtariIII_fsl_backward_entry1_12_ctx.pkl`` and VB dumps under
``fixtures/fsl_backward_entry1_12_integration_vb/``.

Validate with ``fsl_backward_validate_entry1_12_integration.py``.

Report: ``matlab_custom/fsl_backward_run_entry1_12_integration_output.txt``
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


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_run_entry1_12_integration_output.txt"


def _ctx_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_ENTRY1_12_INTEGRATION_CTX_PKL", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        Path(__file__).resolve().parent
        / "fixtures"
        / "DEMAtariIII_fsl_backward_entry1_12_ctx.pkl"
    )


def _replay_dem_atari_enabled() -> bool:
    v = str(os.getenv("RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS", "1")).strip().lower()
    return v in ("1", "true", "yes", "on")


def main() -> int:
    from python_src.toolbox.DEM.DEM_AtariIII import get_dem_atariiii_run_last_label
    from python_src.toolbox.DEM.fsl_backward_entry1_12_integration import (
        integration_vb_out_dir,
        run_track_a_integration,
    )

    if not _replay_dem_atari_enabled():
        print(
            "[Track A 1-12] FAIL: set RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS=1 for sign-off",
            file=sys.stderr,
        )
        return 1

    tag = str(os.getenv("RGMS_FSL_ENTRY1_12_INTEGRATION_TAG", "rgms_canonical")).strip() or "rgms_canonical"
    deadline = str(os.getenv("RGMS_FSL_ENTRY1_12_INTEGRATION_DEADLINE_MINUTES", "90")).strip() or "90"
    out_pkl = _ctx_pkl()
    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)

    code = 0
    with report.open("w", encoding="utf-8") as report_f:
        report_f.write(__doc__ or "")
        report_f.write(f"\n--- RUN OUTPUT — {report} ---\n")
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
            print(
                f"[Track A 1-12] tag={tag!r} dem_atari replay=1 vb_out={integration_vb_out_dir()}",
                file=sys.stderr,
            )
            payload = run_track_a_integration(
                tag=tag,
                replay_dem_atari=True,
                deadline_minutes=deadline,
            )
            out_pkl.parent.mkdir(parents=True, exist_ok=True)
            with out_pkl.open("wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            pdp_pkl = integration_vb_out_dir() / "DEMAtariIII_fsl_backward_entry1_12_pdp.pkl"
            pdp_pkl.parent.mkdir(parents=True, exist_ok=True)
            with pdp_pkl.open("wb") as f:
                pickle.dump({"PDP": payload["ctx"]["PDP"]}, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(
                f"[Track A 1-12] K_11={payload['k_11']} dem_atari_used={payload['dem_atari_draws_used']} "
                f"vb_wall_s={payload['entry12']['vb_wall_s']:.3f}",
                file=sys.stderr,
            )
            print(f"[Track A 1-12] wrote {out_pkl}", file=sys.stderr)
            print(f"[Track A 1-12] wrote {pdp_pkl}", file=sys.stderr)
        except Exception:
            print(
                f"[Track A 1-12] last segment = {get_dem_atariiii_run_last_label()!r}",
                file=sys.stderr,
            )
            traceback.print_exc()
            code = 1
        finally:
            sys.stderr, sys.stdout = old_err, old_out

    return code


if __name__ == "__main__":
    raise SystemExit(main())
