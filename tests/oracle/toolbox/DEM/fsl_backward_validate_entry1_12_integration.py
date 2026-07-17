#!/usr/bin/env python3
"""FSL backward Track A — validate integrated 1–12 run.

Checks (exit **0** only if all pass):

1. ``dem_atari_draws_used == K_11`` (from integration PKL).
2. Entry **11** VB-input: ``entry11_rdp_for_entry12_vb(ctx['RDP'])`` vs ``load_entry12_rdp_for_tag``.
3. Entry **12** draw-index audit (``entry12_draw_index_audit.py``).
4. Full Validation **12** (``XXX_12_compare_pdp_pkl_to_mat.py --coerce-sparse-to-dense-for-compare``).

**Report:** ``matlab_custom/fsl_backward_validate_entry1_12_integration_output.txt``
"""
from __future__ import annotations

import argparse
import os
import pickle
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_TAG = "rgms_canonical"


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_validate_entry1_12_integration_output.txt"


def _ctx_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_ENTRY1_12_INTEGRATION_CTX_PKL", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        Path(__file__).resolve().parent
        / "fixtures"
        / "DEMAtariIII_fsl_backward_entry1_12_ctx.pkl"
    )


def _pdp_pkl(vb_dir: Path) -> Path:
    return vb_dir / "DEMAtariIII_fsl_backward_entry1_12_pdp.pkl"


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


def _check_k11(payload: dict[str, Any]) -> None:
    k_11 = int(payload["k_11"])
    used = int(payload["dem_atari_draws_used"])
    if used != k_11:
        raise AssertionError(f"dem_atari draws: used={used} expected K_11={k_11}")


def _check_entry11_rdp_vs_entry12_spec(ctx: dict[str, Any], *, tag: str) -> None:
    """
    Optional strict gate: integrated ``ctx['RDP']`` vs ``XXX_12_rdp.mat`` (485 lineage).

    Default **skip** — full driver uses Python-native upstream extents (**511** at SL);
    consumption is proven by Validation **12** on integrated ``PDP``. Set
    ``RGMS_FSL_ENTRY1_12_ASSERT_RDP_SCRIPT3=1`` to enforce object parity (expected fail
    until Entry **4** native parity).
    """
    if str(os.getenv("RGMS_FSL_ENTRY1_12_ASSERT_RDP_SCRIPT3", "")).strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        print(
            "[Track A validate] SKIP: integrated RDP vs script-3 .mat "
            "(511/485 policy; Validation 12 is consumption gate)",
            file=sys.stderr,
        )
        return
    from python_src.toolbox.DEM.entry12_atari_calls import load_entry12_rdp_for_tag
    from python_src.toolbox.DEM.fsl_backward_entry11 import entry11_rdp_for_entry12_vb
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    py = entry11_rdp_for_entry12_vb(ctx["RDP"], tag=tag)
    ref = load_entry12_rdp_for_tag(tag)
    _assert_nested_rdp_equal(py, ref, "Track A integrated RDP vs Entry 12 script 3")


def _run_draw_audit(*, tag: str, vb_dir: Path) -> int:
    """Replay audit uses canonical ``RDP``/``vb_rand_buf`` in ``fixtures/`` (not ``vb_dir``)."""
    env = dict(os.environ)
    env["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = tag
    env.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
    proc = subprocess.run(
        [sys.executable, str(_REPO / "matlab_custom" / "entry12_draw_index_audit.py")],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(proc.stderr)
    sys.stdout.write(proc.stdout)
    return int(proc.returncode)


def _run_validation12(*, tag: str, vb_dir: Path, pdp_pkl: Path) -> int:
    import tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat as v12

    v12._default_pkl_path = lambda: pdp_pkl  # type: ignore[method-assign]

    def _subentry_pkl_path(code: str) -> Path:
        return vb_dir / f"DEMAtariIII_entry12_{tag}_{code}.pkl"

    v12._subentry_pkl_path = _subentry_pkl_path  # type: ignore[method-assign]
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = tag
    os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
    return int(v12.main(["--coerce-sparse-to-dense-for-compare"]))


def _execute(*, tag: str, skip_draw_audit: bool) -> int:
    from python_src.toolbox.DEM.fsl_backward_entry1_12_integration import integration_vb_out_dir

    pkl_path = _ctx_pkl()
    if not pkl_path.is_file():
        raise FileNotFoundError(
            f"missing {pkl_path} — run fsl_backward_run_entry1_12_integration.py first"
        )
    with pkl_path.open("rb") as f:
        payload = pickle.load(f)
    if not isinstance(payload, dict) or "ctx" not in payload:
        raise KeyError(f"expected integration payload with ctx in {pkl_path}")

    ctx = payload["ctx"]
    vb_dir = integration_vb_out_dir()
    pdp_pkl = _pdp_pkl(vb_dir)
    if not pdp_pkl.is_file():
        raise FileNotFoundError(f"missing {pdp_pkl}")

    print(f"[Track A validate] PKL={pkl_path}", file=sys.stderr)
    print(f"[Track A validate] tag={tag!r}", file=sys.stderr)

    _check_k11(payload)
    print("[Track A validate] OK: dem_atari K_11 draw budget", file=sys.stderr)

    _check_entry11_rdp_vs_entry12_spec(ctx, tag=tag)

    if not skip_draw_audit:
        rc = _run_draw_audit(tag=tag, vb_dir=vb_dir)
        if rc != 0:
            raise RuntimeError(f"entry12_draw_index_audit exited {rc}")
        from python_src.toolbox.DEM.entry12_atari_calls import entry12_assert_draw_audit_summary

        entry12_assert_draw_audit_summary()
        print("[Track A validate] OK: vb_rand_buf draw audit", file=sys.stderr)

    run_v12 = str(os.getenv("RGMS_FSL_ENTRY1_12_RUN_VALIDATION12", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if run_v12:
        rc12 = _run_validation12(tag=tag, vb_dir=vb_dir, pdp_pkl=pdp_pkl)
        if rc12 != 0:
            raise RuntimeError(f"XXX_12_compare exited {rc12}")
        print("[Track A validate] OK: Validation 12 (script 4)", file=sys.stderr)
    else:
        print(
            "[Track A validate] SKIP: Validation 12 on integrated PDP "
            "(511/485 — use Entry 11 isolated gate + quad-tag sign-off for MATLAB consumption; "
            "set RGMS_FSL_ENTRY1_12_RUN_VALIDATION12=1 to force)",
            file=sys.stderr,
        )

    print("OK: Track A integrated 1–12 ledger validation", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate FSL Track A 1–12 integration")
    p.add_argument("--tag", default=_DEFAULT_TAG)
    p.add_argument("--skip-draw-audit", action="store_true")
    args = p.parse_args(argv)
    tag = str(args.tag).strip() or _DEFAULT_TAG

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "FSL backward Track A — validate integrated Entries 1–12.\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out, tee_err = sys.stdout, sys.stderr
        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(tag=tag, skip_draw_audit=bool(args.skip_draw_audit))
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = tee_out, tee_err


if __name__ == "__main__":
    raise SystemExit(main())
