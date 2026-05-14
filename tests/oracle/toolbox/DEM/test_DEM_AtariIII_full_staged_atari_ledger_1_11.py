"""Full staged Atari ledger (1–11, pre–Entry 12) — Python integration, not Entry 11 smoke.

**Vocabulary (do not confuse with per-entry smoke tests):**

- **Full staged Atari ledger (1–11, pre–Entry 12)** — one Python run of
  ``run_dem_atariiii(entry_stop=11)`` with **MATLAB-faithful driver loop counts**
  (``RGMS_ATARI_ENTRY8_OUTER=128``, ``RGMS_ATARI_TRAINING_T=10000``), i.e. **no**
  harness shortcuts such as ``outer=1`` / reduced ``training_t`` (see **§ Entry 11**
  smoke in ``Atari_example.md`` only there).
- Loose talk about *“entries 1–11”* can mean per-entry unit tests **or** this ledger;
  in docs and issues, prefer **full staged ledger** / **FSL 1–11** when you mean **this**
  integration bar.

**Opt-in:** ``RGMS_ATARI_RUN_FULL_STAGED_LEDGER_1_11=1`` (structural FSL run, long).

**Long runs — wall limit + where you died (applies here):** The structural test calls
``run_dem_atariiii``, so the **same** env toggles documented in ``DEM_AtariIII.py`` (comment block) and ``Atari_example.md``
§ **ENTRY 1-11** apply: ``RGMS_ATARI_RUN_DEADLINE_MINUTES`` (single knob; seeds ``perf_counter`` ceiling
and error text) or optional explicit ``RGMS_ATARI_RUN_DEADLINE_MONO``; ``RGMS_ATARI_RUN_SEGMENT_TIMING=1``
for stderr **segment** timings (labels at driver boundaries + inside long Entry **8/9** loops—not
every physical source line). **Tracing** is the driver's **last segment label** string
(``get_dem_atariiii_run_last_label()``). On **any** exception from ``run_dem_atariiii`` inside this
module, ``_run_fsl_entry11_context`` prints ``[FSL 1-11] last traced segment = …`` to stderr, then
re-raises (deadline ``RuntimeError`` from the driver already embeds that label).
**If neither deadline env is set,** ``_run_fsl_entry11_context`` sets ``RGMS_ATARI_RUN_DEADLINE_MINUTES=20``
for that run only (driver seeds the mono ceiling on first check), then restores prior env.

**MATLAB nested ``RDP`` parity (separate):** After a successful run, compare saved ``ctx`` (PKL) to the
FSL MATLAB ``.mat`` using ``python tests/oracle/toolbox/DEM/fsl_1_11_compare_ctx_pkl_to_mat.py`` only
(see ``Atari_example.md`` § **ENTRY 1-11**). This module does **not** load ``.mat`` or assert MATLAB parity.

**PKL snapshot:** After every **successful** structural run, full ``ctx`` is written to ``fixtures/DEMAtariIII_fsl_1_11_ctx.pkl`` (override output path only with ``RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH``).

**Run log:** Each invocation of ``test_full_staged_atari_ledger_1_through_11_pre_entry12`` overwrites ``matlab_custom/test_DEM_AtariIII_full_staged_atari_ledger_1_11_output.txt`` (module docstring + teed stdout/stderr during the test body).

See ``Atari_example.md`` § **ENTRY 1-11 — full Python pipeline gate (ENTRIES 1–11)**.
"""

from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from python_src.toolbox.DEM.DEM_AtariIII import get_dem_atariiii_run_last_label, run_dem_atariiii

_FSL_FULL_STAGED_REPO_ROOT = Path(__file__).resolve().parents[4]


def _fsl_full_staged_run_output_txt_path() -> Path:
    return _FSL_FULL_STAGED_REPO_ROOT / "matlab_custom" / "test_DEM_AtariIII_full_staged_atari_ledger_1_11_output.txt"


class _FslTeeIO:
    """Duplicate text writes to multiple streams (console + report file)."""

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


_FULL_STAGED_LEDGER = str(os.getenv("RGMS_ATARI_RUN_FULL_STAGED_LEDGER_1_11", "")).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _fsl_context_pkl_out_path() -> Path:
    raw = str(os.getenv("RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "fixtures" / "DEMAtariIII_fsl_1_11_ctx.pkl"


def _dump_fsl_context_pkl(ctx: dict[str, Any]) -> None:
    """Write full ``ctx`` after structural success (default or ``RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH``)."""
    path = _fsl_context_pkl_out_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(ctx, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[FSL 1-11] wrote context pickle: {path}", file=sys.stderr, flush=True)


_FSL_DEFAULT_TIMEOUT_MINUTES = 20


def _run_fsl_entry11_context() -> dict[str, Any]:
    """``run_dem_atariiii(entry_stop=11)`` at full driver scale; restores outer / training env."""
    old_mins = os.environ.get("RGMS_ATARI_RUN_DEADLINE_MINUTES")
    installed_default_minutes = not (
        str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MINUTES", "")).strip()
        or str(os.getenv("RGMS_ATARI_RUN_DEADLINE_MONO", "")).strip()
    )
    if installed_default_minutes:
        os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = str(_FSL_DEFAULT_TIMEOUT_MINUTES)

    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "128"
    os.environ["RGMS_ATARI_TRAINING_T"] = "10000"
    try:
        try:
            return run_dem_atariiii(entry_stop=11)
        except Exception:
            print(
                f"[FSL 1-11] last traced segment = {get_dem_atariiii_run_last_label()!r}",
                file=sys.stderr,
                flush=True,
            )
            raise
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

        if installed_default_minutes:
            if old_mins is None:
                os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MINUTES", None)
            else:
                os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = old_mins


@pytest.mark.slow
@pytest.mark.skipif(
    not _FULL_STAGED_LEDGER,
    reason=(
        "Full staged Atari ledger (FSL 1–11): set RGMS_ATARI_RUN_FULL_STAGED_LEDGER_1_11=1 "
        "(long run: outer=128, training_t=10000). See Atari_example.md § ENTRY 1-11."
    ),
)
def test_full_staged_atari_ledger_1_through_11_pre_entry12():
    """``run_dem_atariiii(entry_stop=11)`` at full scale; structural checks; then write ``ctx`` PKL."""
    out_path = _fsl_full_staged_run_output_txt_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_f = out_path.open("w", encoding="utf-8")
    report_f.write(__doc__ or "")
    report_f.write(f"\n--- RUN OUTPUT (stdout + stderr) — {out_path} ---\n")
    report_f.flush()
    old_err, old_out = sys.stderr, sys.stdout
    try:
        sys.stderr = _FslTeeIO(old_err, report_f)
        sys.stdout = _FslTeeIO(old_out, report_f)
        ctx = _run_fsl_entry11_context()

        assert int(ctx["entry8_outer"]) == 128
        assert int(ctx["entry8_NT"]) == 100
        assert int(float(ctx["GDP"]["T"])) == 10000
        assert float(ctx["GDP"]["tau"]) == 1.0

        assert "MDP" in ctx and isinstance(ctx["MDP"], list)
        assert "RDP" in ctx and isinstance(ctx["RDP"], dict)
        assert np.isclose(float(ctx["RDP"]["T"]), 64.0, rtol=0.0, atol=1e-12)
        assert "L" in ctx["RDP"]
        assert "MDP" in ctx["RDP"]
        assert "P" in ctx
        assert np.asarray(ctx["P"], dtype=np.float64).shape[0] == 32

        _dump_fsl_context_pkl(ctx)
    finally:
        sys.stderr = old_err
        sys.stdout = old_out
        report_f.close()
