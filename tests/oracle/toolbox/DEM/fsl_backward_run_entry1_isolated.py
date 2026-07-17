#!/usr/bin/env python3
"""FSL backward — run Entry 1 only (snippet constants; no ``entry_stop=1`` driver required).

Writes ``fixtures/DEMAtariIII_fsl_backward_entry1_post.pkl``.

**Default:** native constants via ``run_entry1_from_boundary``.

**Driver ledger:** ``RGMS_FSL_ENTRY1_DRIVER_REPLAY=1`` — ``run_entry1_driver_ledger_replay``.

Compare with ``fsl_backward_compare_entry1_pkl_to_mat.py``.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY1_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry1_post.pkl"


def _env_on(name: str, default: str = "0") -> bool:
    raw = str(os.getenv(name, default)).strip().lower()
    return raw not in ("0", "false", "no", "off")


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry1 import (
        run_entry1_driver_ledger_replay,
        run_entry1_from_boundary,
    )

    if _env_on("RGMS_FSL_ENTRY1_DRIVER_REPLAY"):
        print(
            "[FSL backward Entry 1 isolated] driver ledger + dem_atari_rand_buf replay (K_1)",
            file=sys.stderr,
        )
        try:
            out_payload = run_entry1_driver_ledger_replay()
        except FileNotFoundError as exc:
            print(f"[FSL backward Entry 1 isolated] {exc}", file=sys.stderr)
            return 2
    else:
        print("[FSL backward Entry 1 isolated] native snippet constants", file=sys.stderr)
        out_payload = run_entry1_from_boundary({})

    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "validation": {
                    "lane": "fsl_backward_entry1",
                    "authority_var": "entry1_Nr, entry1_Nc, entry1_Sc, entry1_Nd, entry1_C",
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 1 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
