#!/usr/bin/env python3
"""Preflight: count scalar ``numpy.random.rand()`` draws for Entry 12 VB oracle.

Writes ``fixtures/entry12_vb_rand_K[_<tag>].mat`` (variable ``K``) for
``DEMAtariIII_entry12_dump_all_subentries.m`` (script **1a** of the four-script lane).

**Validation coherence:** ``K`` and ``vb_rand_buf`` are only meaningful when the full
chain runs together: **1a** (this script) → **1b** (MATLAB dump driver + fork) → **3**
(XXX 12) → **4** (Validation 12). Do not pair ``K`` from one preflight with ``.mat``/``.pkl``
from another run, tag, or capture script.

Uses ``entry12_atari_calls.entry12_write_preflight_k`` (same VB flags as script **3**,
``reuse_matlab_draws=False``). Set ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` for call **2**
(``rgms_atari_call2``); default tag is call **1** (``rgms_canonical``).

Run from repo root with ``conda activate rgms`` before script **1b**.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_src.toolbox.DEM.entry12_atari_calls import (
    entry12_atari_call_rdp_mat_path,
    entry12_assert_buf_k_coherent,
    entry12_log_signoff_chain,
    entry12_quick_digest,
    entry12_resolve_run_tag,
    entry12_write_preflight_k,
)


def main() -> int:
    tag = entry12_resolve_run_tag()
    entry12_log_signoff_chain(tag, stream=sys.stderr)
    rdp_mat = entry12_atari_call_rdp_mat_path(tag)
    if not rdp_mat.is_file():
        raise FileNotFoundError(f"missing RDP mat for preflight tag {tag!r}: {rdp_mat}")
    print(
        f"[entry12 preflight] provenance tag={tag!r} rdp_mat={rdp_mat} "
        f"sha256_12={entry12_quick_digest(rdp_mat)}",
        file=sys.stderr,
    )
    k, out = entry12_write_preflight_k(tag)
    print(f"[entry12 preflight] tag={tag!r} K={k}", file=sys.stderr)
    print(f"[entry12 preflight] wrote {out}", file=sys.stderr)
    try:
        entry12_assert_buf_k_coherent(tag)
        print("[entry12 preflight] buf/K coherence ok (1b already present)", file=sys.stderr)
    except ValueError as exc:
        print(f"[entry12 preflight] note: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
