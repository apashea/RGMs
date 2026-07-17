#!/usr/bin/env python3
"""Entry 4 — deep spectral inspection (``eig.md`` §20).

Reads canonical oracle/probe PKLs. Writes (always refresh — derived analysis):

- ``..._eig_inspection_deep.json`` — per-block deep packets (failures full; passes summary)
- ``..._eig_failure_index.json`` — compact failing-hash index
- ``..._eig_failure_replay.pkl`` — replay corpus for layout / nobalance research

Appends report lines to ``matlab_custom/fsl_backward_entry4_rgm_spectral_eig_dump_output.txt``.
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance, geevx_available, resolve_backend
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import STAGE_OK, sub_hash
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_dump_report_txt,
    entry4_eig_failure_index_json,
    entry4_eig_failure_replay_pkl,
    entry4_eig_inspection_deep_json,
    entry4_eig_oracle_blocks_pkl,
    entry4_python_engine_probe_pkl,
    write_manifest,
)
from tests.oracle.toolbox.DEM.entry4_eig_inspection import (
    build_failure_index,
    build_failure_replay_bundle,
    deep_block_inspection,
)


def _append_report(lines: list[str]) -> None:
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def _index_probe_by_hash(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rec in records:
        h = sub_hash(np.asarray(rec["sub_mi"], dtype=np.float64))
        out[h] = rec
    return out


def _summarize_passing(insp: dict[str, Any]) -> dict[str, Any]:
    return {
        "sub_hash": insp["sub_hash"],
        "n": insp["n"],
        "stage": STAGE_OK,
        "order_ok": (insp.get("granular_summary") or {}).get("order_ok"),
    }


def main() -> int:
    probe_path = entry4_python_engine_probe_pkl()
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not probe_path.is_file() or not blocks_path.is_file():
        print(
            "[entry4 deep inspection] missing dump PKLs — run fsl_backward_dump_entry4_spectral_eig.py first",
            file=sys.stderr,
        )
        return 2

    with probe_path.open("rb") as f:
        probe = pickle.load(f)
    with blocks_path.open("rb") as f:
        blocks_payload = pickle.load(f)
    blocks: list[dict] = blocks_payload["blocks"]
    probe_by_hash = _index_probe_by_hash(probe["records"])

    inspections: list[dict[str, Any]] = []
    for blk in blocks:
        h = blk.get("sub_hash") or sub_hash(np.asarray(blk["sub_mi"], dtype=np.float64))
        insp = deep_block_inspection(blk, probe_by_hash.get(h), lane_fn=eig_nobalance)
        inspections.append(insp)

    failure_index = build_failure_index(inspections)
    replay = build_failure_replay_bundle(blocks, inspections)

    deep_records: list[dict[str, Any]] = []
    for insp in inspections:
        if insp.get("stage") == STAGE_OK:
            deep_records.append(_summarize_passing(insp))
        else:
            deep_records.append(insp)

    utc = datetime.now(timezone.utc).isoformat()
    meta = {
        "utc": utc,
        "backend": resolve_backend(),
        "geevx_available": geevx_available(),
        "lane_primary": "eig_nobalance",
        "n_blocks": len(blocks),
    }

    deep_path = entry4_eig_inspection_deep_json()
    with deep_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"meta": meta, "failure_index": failure_index, "blocks": deep_records},
            f,
            indent=2,
            default=str,
        )
        f.write("\n")

    index_path = entry4_eig_failure_index_json()
    with index_path.open("w", encoding="utf-8") as f:
        json.dump({"meta": meta, **failure_index}, f, indent=2, default=str)
        f.write("\n")

    replay_path = entry4_eig_failure_replay_pkl()
    with replay_path.open("wb") as f:
        pickle.dump({**meta, **replay}, f, protocol=pickle.HIGHEST_PROTOCOL)

    write_manifest(
        extra={
            "deep_inspection_utc": utc,
            "n_fail": failure_index["n_fail"],
            "inspection_deep_json": str(deep_path),
            "failure_index_json": str(index_path),
            "failure_replay_pkl": str(replay_path),
        }
    )

    lines = [
        f"=== Entry 4 deep inspection {utc} ===",
        f"backend={meta['backend']} geevx={meta['geevx_available']}",
        f"n_fail={failure_index['n_fail']}/{failure_index['n_total']} "
        f"by_stage={failure_index.get('by_stage_hashes')}",
        f"wrote_deep={deep_path}",
        f"wrote_index={index_path}",
        f"wrote_replay={replay_path} n_entries={replay['n_entries']}",
    ]
    for row in failure_index.get("failing_rows", [])[:12]:
        lines.append(
            f"  fail {row['sub_hash']} n={row['n']} stage={row['stage']} "
            f"lev={row.get('lev_call')} iter={row.get('iter_idx')} "
            f"jmax {row.get('jmax_ref')}->{row.get('jmax_got')} "
            f"max_w_diff={row.get('max_abs_w_diff')} "
            f"greedy_match={row.get('greedy_max_pair_w_diff')} "
            f"cyclic_best_shift={row.get('best_cyclic_shift')} "
            f"order_mismatch_ranks={row.get('order_rank_mismatch_count')}"
        )
    _append_report(lines)
    for ln in lines:
        print(f"[entry4 deep inspection] {ln}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
