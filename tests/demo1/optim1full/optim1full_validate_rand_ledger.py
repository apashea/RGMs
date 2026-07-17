#!/usr/bin/env python3
"""OPTIM1FULL — validate Model B ledger + manifest after capture (§ **11.7.2**)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        optim1full_rand_ledger_mat,
        optim1full_rand_manifest_json,
    )

    buf, manifest = load_validated_optim1full_ledger()
    if manifest.k_total < 4096:
        print(
            f"[optim1full_validate_rand_ledger] WARN: K_total={manifest.k_total} < 4096",
            file=sys.stderr,
        )
    entries_seg = manifest.segment("entries_1_11")
    nr32 = manifest.segment("nr_game_32")
    print(
        f"[optim1full_validate_rand_ledger] OK K_total={manifest.k_total} "
        f"entries_1_11_k={entries_seg.k} nr_through={nr32.end} "
        f"mat={optim1full_rand_ledger_mat().name}",
        file=sys.stderr,
    )

    # Optional cross-check vs DEMO1 FSL preamble buffer when present.
    fsl11 = _REPO / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures" / "dem_atari_rand_buf_through_entry11.mat"
    if fsl11.is_file():
        from scipy.io import loadmat

        raw = loadmat(str(fsl11))
        k11 = int(raw.get("K_11", [[0]])[0][0])
        ref = raw["dem_atari_rand_buf"].ravel()
        if k11 == entries_seg.k and ref.size >= k11:
            delta = float(abs(buf[:k11] - ref[:k11]).max())
            print(
                f"[optim1full_validate_rand_ledger] entries_1_11 vs FSL K_11={k11} max_abs_delta={delta}",
                file=sys.stderr,
            )
            if delta > 1e-12:
                print(
                    "[optim1full_validate_rand_ledger] WARN: entries_1_11 slice differs from FSL fixture",
                    file=sys.stderr,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
