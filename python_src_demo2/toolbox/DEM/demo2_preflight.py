"""DEMO2 fixture preflight — verify dumps exist before execution (see ``Atari_example.md``)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from python_src_demo2.toolbox.DEM.demo2_preamble_ctx import (
    build_demo2_preamble_companion_manifest,
    demo2_preamble_ctx_load_enabled,
    resolve_demo2_preamble_ctx_pkl_path,
)

Demo2PreflightMode = Literal["off", "native", "resume", "lane_b"]

_REPO = Path(__file__).resolve().parents[3]
_FIXTURES = _REPO / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"


@dataclass(frozen=True)
class _Check:
    label: str
    path: Path
    required: bool


def _resolve_preflight_mode() -> Demo2PreflightMode:
    raw = str(os.getenv("RGMS_DEMO2_PREFLIGHT_MODE", "")).strip().lower()
    if raw in ("off", "0", "false", "no"):
        return "off"
    if raw in ("native", "full", "lane_a"):
        return "native"
    if raw in ("resume", "load", "dev"):
        return "resume"
    if raw in ("lane_b", "paired", "matlab"):
        return "lane_b"
    if demo2_preamble_ctx_load_enabled():
        return "resume"
    return "native"


def _path_checks_for_mode(mode: Demo2PreflightMode) -> list[_Check]:
    manifest = build_demo2_preamble_companion_manifest(
        primary_ctx_pkl=resolve_demo2_preamble_ctx_pkl_path()
    )
    checks: list[_Check] = []

    def add(label: str, rel: str | None, *, required: bool) -> None:
        if not rel:
            return
        checks.append(_Check(label, _REPO / rel.replace("/", os.sep), required))

    if mode in ("resume", "lane_b"):
        add("preamble ctx PKL", manifest.get("primary_ctx_pkl"), required=True)
        native = manifest.get("native_python_rng") or {}
        add("preamble native rand mat", native.get("path"), required=mode == "lane_b")
        add(
            "preamble manifest JSON",
            "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_demo2_preamble_manifest.json",
            required=False,
        )

    if mode == "lane_b":
        rng = manifest.get("rng_matlab_ledger") or {}
        e11 = rng.get("dem_atari_through_entry11") or {}
        e12 = rng.get("dem_atari_through_entry12") or {}
        add("dem_atari_rand_buf through Entry 11", e11.get("path"), required=True)
        add("dem_atari_rand_buf through Entry 12", e12.get("path"), required=True)

        canonical = rng.get("entry12_vb_call1_rgms_canonical") or {}
        for key in ("K_mat", "buf_mat", "rdp_mat", "pdp_mat"):
            add(f"Entry 12 canonical {key}", canonical.get(key), required=True)

        sl4 = manifest.get("structure_learning_entry4") or {}
        add("FSL Entry 4/merge authority mat", sl4.get("matlab_authority_mat"), required=True)

        sl10 = manifest.get("structure_learning_entry10_sort") or {}
        add("FSL Entry 10 authority mat", sl10.get("matlab_authority_mat"), required=True)

        post_nr = manifest.get("structure_learning_post12_nr_loop") or {}
        add("post-NR MDP authority mat", post_nr.get("planned_authority_mat"), required=True)

        tags = manifest.get("demo2_post12_vb_tags") or {}
        for call_name, tag in (
            ("call2", tags.get("call2")),
            ("call3", tags.get("call3")),
            ("call4", tags.get("call4")),
        ):
            if not tag:
                continue
            prefix = "DEMAtariIII_entry12_vb_matlab_rand_buf"
            buf_name = f"{prefix}.mat" if tag == "rgms_canonical" else f"{prefix}_{tag}.mat"
            k_name = "entry12_vb_rand_K.mat" if tag == "rgms_canonical" else f"entry12_vb_rand_K_{tag}.mat"
            rdp_name = (
                "DEMAtariIII_XXX_12_rdp.mat"
                if tag == "rgms_canonical"
                else f"DEMAtariIII_XXX_12_{tag}_rdp.mat"
            )
            add(f"VB {call_name} K", f"tests/oracle/toolbox/DEM/fixtures/{k_name}", required=True)
            add(f"VB {call_name} rand buf", f"tests/oracle/toolbox/DEM/fixtures/{buf_name}", required=True)
            add(f"VB {call_name} RDP", f"tests/oracle/toolbox/DEM/fixtures/{rdp_name}", required=True)

    if mode == "native":
        checks.append(
            _Check(
                "preamble ctx PKL (recommended for dev)",
                resolve_demo2_preamble_ctx_pkl_path(),
                required=False,
            )
        )

    return checks


def run_demo2_preflight(*, mode: Demo2PreflightMode | None = None) -> dict[str, object]:
    """Return report dict; raises ``RuntimeError`` if a required check fails."""
    mode_use: Demo2PreflightMode = mode if mode is not None else _resolve_preflight_mode()
    if mode_use == "off":
        return {"mode": "off", "skipped": True}

    checks = _path_checks_for_mode(mode_use)
    missing_required: list[str] = []
    missing_optional: list[str] = []
    present: list[str] = []

    for chk in checks:
        if chk.path.is_file():
            present.append(chk.label)
        elif chk.required:
            missing_required.append(f"{chk.label}: {chk.path}")
        else:
            missing_optional.append(f"{chk.label}: {chk.path}")

    report: dict[str, object] = {
        "mode": mode_use,
        "present_count": len(present),
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "present": present,
    }

    if missing_required:
        lines = [
            f"DEMO2 preflight failed (mode={mode_use!r}).",
            "Required fixtures missing:",
            *[f"  - {m}" for m in missing_required],
        ]
        if missing_optional:
            lines.append("Optional / recommended missing:")
            lines.extend(f"  - {m}" for m in missing_optional)
        if mode_use == "resume":
            lines.append(
                "Run once at full scale: python python_src_demo2/toolbox/DEM/DEM_AtariIII_dump_preamble.py"
            )
        raise RuntimeError("\n".join(lines))

    if missing_optional and mode_use == "native":
        print(
            "[DEMO2 preflight] native mode — optional fixtures missing (full preamble re-run each time):",
            file=sys.stderr,
        )
        for m in missing_optional:
            print(f"  - {m}", file=sys.stderr)

    print(
        f"[DEMO2 preflight] mode={mode_use!r} ok "
        f"(present={len(present)}, optional_missing={len(missing_optional)})",
        file=sys.stderr,
        flush=True,
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEMO2 fixture preflight (dump inventory gate).")
    parser.add_argument(
        "--mode",
        choices=("off", "native", "resume", "lane_b"),
        default=None,
        help="Check set (default: resume if RGMS_DEMO2_LOAD_PREAMBLE_CTX=1 else native)",
    )
    parser.add_argument("--json", action="store_true", help="Print report JSON to stdout")
    args = parser.parse_args(argv)

    try:
        report = run_demo2_preflight(mode=args.mode)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
