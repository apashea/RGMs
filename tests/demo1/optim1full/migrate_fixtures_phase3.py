#!/usr/bin/env python3
"""One-shot fixture migration: optim1/fixtures -> optim1full/fixtures (Approach 2 Phase 3)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
SRC = _REPO / "tests" / "demo1" / "optim1" / "fixtures"
DST = _REPO / "tests" / "demo1" / "optim1full" / "fixtures"
RETIRED_DST = DST / "deprecated" / "retired_tier3bc"

RETIRED_RE = re.compile(r"rgms_atari_call2_g(0[2-9]|[12][0-9]|3[0-2])")

OPTIM1_ONLY = {
    "DEMAtariIII_entry12_rgms_canonical_12A.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12B.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12C.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12D.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12E.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12F.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12G.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12H.pkl",
    "DEMAtariIII_entry12_rgms_canonical_12I.pkl",
    "DEMAtariIII_optim1_entry10_matlab_eig_post.pkl",
    "DEMAtariIII_optim1_entry3_post.pkl",
    "DEMAtariIII_optim1_entry7_post.pkl",
    "DEMAtariIII_optim1_entry9_post.pkl",
}


def _is_retired(name: str) -> bool:
    return RETIRED_RE.search(name) is not None


def _is_optim1full_related(name: str) -> bool:
    if name in OPTIM1_ONLY:
        return False
    low = name.lower()
    return "optim1full" in low or "rgms_atari_call" in name or "rgms_optim1full" in name


def _rename_active_tags(name: str) -> str:
    if _is_retired(name):
        return name
    out = name.replace("rgms_optim1full_nr_g01", "rgms_atari_optim1full_nr_g01")
    if "rgms_atari_call2_g" not in out:
        out = out.replace("rgms_atari_call2", "rgms_atari_optim1full_call2")
    out = out.replace("rgms_atari_call3", "rgms_atari_optim1full_call3")
    out = out.replace("rgms_atari_call4", "rgms_atari_optim1full_call4")
    return out


def _rewrite_manifest(text: str) -> str:
    data = json.loads(text)
    if isinstance(data.get("tag"), str):
        data["tag"] = _rename_active_tags(data["tag"])
    paths = data.get("paths")
    if isinstance(paths, dict):
        for k, v in list(paths.items()):
            if isinstance(v, str):
                paths[k] = (
                    v.replace("\\tests\\demo1\\optim1\\fixtures", "\\tests\\demo1\\optim1full\\fixtures")
                    .replace("/tests/demo1/optim1/fixtures", "/tests/demo1/optim1full/fixtures")
                )
                for old_tag, new_tag in (
                    ("rgms_optim1full_nr_g01", "rgms_atari_optim1full_nr_g01"),
                    ("rgms_atari_call2_g", "rgms_atari_call2_g"),
                ):
                    pass
                paths[k] = _rename_active_tags(paths[k])
    return json.dumps(data, indent=2) + "\n"


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit(f"missing source fixtures dir: {SRC}")
    DST.mkdir(parents=True, exist_ok=True)
    RETIRED_DST.mkdir(parents=True, exist_ok=True)

    moved_active = moved_retired = skipped = 0
    for src in sorted(SRC.iterdir()):
        if not src.is_file():
            continue
        name = src.name
        if not _is_optim1full_related(name):
            skipped += 1
            continue
        new_name = _rename_active_tags(name)
        if _is_retired(name):
            dest = RETIRED_DST / new_name
            moved_retired += 1
        else:
            dest = DST / new_name
            moved_active += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        if src.suffix == ".json" and name.startswith("entry12_signoff_manifest_"):
            dest.write_text(_rewrite_manifest(src.read_text(encoding="utf-8")), encoding="utf-8")
            src.unlink()
        else:
            shutil.move(str(src), str(dest))
    print(
        f"[migrate_fixtures] active={moved_active} retired={moved_retired} "
        f"left_in_optim1={skipped} dst={DST}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
