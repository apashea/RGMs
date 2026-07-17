#!/usr/bin/env python3
"""Write vendor/MANIFEST.txt (sha256) after B1 extract."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "--vendor",
        default="lapack-3.12.0-dgeevx",
        help="subdir under vendor/ (default: lapack-3.12.0-dgeevx)",
    )
    args = p.parse_args()
    vendor = ROOT / "vendor" / args.vendor
    if not vendor.is_dir():
        print(f"missing {vendor} — run fetch_lapack_dgeevx.ps1 first", file=sys.stderr)
        return 2
    return _write_manifest(vendor)


def _write_manifest(vendor: Path) -> int:
    lines: list[str] = []
    for path in sorted(vendor.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".f", ".f90"):
            h = hashlib.sha256(path.read_bytes()).hexdigest()
            rel = path.relative_to(vendor).as_posix()
            lines.append(f"{h}  {rel}")
    out = vendor / "MANIFEST.txt"
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"wrote {out} ({len(lines)} Fortran files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
