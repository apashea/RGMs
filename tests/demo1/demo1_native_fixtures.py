"""DEMO1 Product A — native authority fixtures (seed **2**; read-only for OPTIM1).

One DEMO1 native run dumps ``ctx`` at ladder entries **3, 7, 9, 12** under
``tests/demo1/python_native/fixtures/``. OPTIM1 Product A compares against these
files — **do not** re-run fidelity ``run_dem_atariiii`` during OPTIM1 verification.
"""

from __future__ import annotations

import json
import pickle
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.demo1.demo1_native_rng import DEMO1_NATIVE_RNG_SEED_DEFAULT
from tests.demo1.demo1_paths import demo1_python_native_dir, demo1_repo_root

# Ladder nodes used by ``optim1_native_gate.py --entry-stop``.
DEMO1_NATIVE_LADDER_ENTRY_STOPS: tuple[int, ...] = (3, 7, 9, 12)

DEMO1_NATIVE_CAPTURE_TAG = "demo1_native_authority"

_MANIFEST_NAME = "DEMO1_native_manifest.json"


def demo1_native_fixtures_dir() -> Path:
    return demo1_python_native_dir() / "fixtures"


def demo1_native_entry_ctx_path(entry_stop: int) -> Path:
    n = int(entry_stop)
    if n not in DEMO1_NATIVE_LADDER_ENTRY_STOPS:
        raise ValueError(
            f"entry_stop={n}: native authority fixtures exist for "
            f"{DEMO1_NATIVE_LADDER_ENTRY_STOPS} only"
        )
    return demo1_native_fixtures_dir() / f"DEMO1_native_entry{n:02d}_ctx.pkl"


def demo1_native_manifest_path() -> Path:
    return demo1_native_fixtures_dir() / _MANIFEST_NAME


def _oracle_capture_dir() -> Path:
    return demo1_repo_root() / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"


def _capture_source_path(entry_stop: int, *, tag: str = DEMO1_NATIVE_CAPTURE_TAG) -> Path:
    return _oracle_capture_dir() / f"dem_atari_entry{int(entry_stop)}_post_{tag}.pkl"


def save_demo1_native_entry_ctx(entry_stop: int, ctx: dict[str, Any]) -> Path:
    out = demo1_native_entry_ctx_path(entry_stop)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(ctx, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def load_demo1_native_entry_ctx(entry_stop: int) -> dict[str, Any]:
    path = demo1_native_entry_ctx_path(entry_stop)
    if not path.is_file():
        raise FileNotFoundError(
            f"missing DEMO1 native authority fixture: {path}\n"
            "Run once: python tests/demo1/demo1_native_dump.py "
            "(or DEM_AtariIII_demo1_python.py --save-artifacts --no-plot)"
        )
    with path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {path}")
    return blob


def missing_demo1_native_entry_stops() -> list[int]:
    return [n for n in DEMO1_NATIVE_LADDER_ENTRY_STOPS if not demo1_native_entry_ctx_path(n).is_file()]


def assert_demo1_native_fixtures_present() -> None:
    missing = missing_demo1_native_entry_stops()
    if missing:
        raise FileNotFoundError(
            f"DEMO1 native authority incomplete — missing entry stops {missing}. "
            "Run: python tests/demo1/demo1_native_dump.py"
        )


def write_demo1_native_manifest(*, rng_seed: int | None, entry_stops: tuple[int, ...]) -> Path:
    path = demo1_native_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "rng_seed": rng_seed,
        "capture_tag": DEMO1_NATIVE_CAPTURE_TAG,
        "entry_stops": list(entry_stops),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": "tests/demo1/demo1_native_dump.py",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def collect_driver_captures_to_fixtures(*, tag: str = DEMO1_NATIVE_CAPTURE_TAG) -> dict[int, Path]:
    """Copy oracle driver post-entry captures into ``python_native/fixtures/``."""
    written: dict[int, Path] = {}
    for n in DEMO1_NATIVE_LADDER_ENTRY_STOPS:
        src = _capture_source_path(n, tag=tag)
        if not src.is_file():
            raise FileNotFoundError(
                f"missing driver capture after native dump run: {src}\n"
                f"(expected RGMS_ATARI_CAPTURE_ENTRY{n}_POST=1 and RGMS_ATARI_TAG={tag!r})"
            )
        dst = demo1_native_entry_ctx_path(n)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written[n] = dst
    return written


def capture_env_for_native_dump(*, tag: str = DEMO1_NATIVE_CAPTURE_TAG) -> dict[str, str]:
    env: dict[str, str] = {}
    for n in DEMO1_NATIVE_LADDER_ENTRY_STOPS:
        env[f"RGMS_ATARI_CAPTURE_ENTRY{n}_POST"] = "1"
    env["RGMS_ATARI_TAG"] = tag
    return env
