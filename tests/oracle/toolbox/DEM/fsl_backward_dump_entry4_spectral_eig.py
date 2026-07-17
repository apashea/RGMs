#!/usr/bin/env python3
"""Entry 4 — capture MATLAB ``eig(...,'nobalance')`` spectral audit on FSL boundary.

Loads ``DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl``, runs Python
``spm_faster_structure_learning`` with MATLAB ``MI`` + MATLAB ``eig`` + spectral probe.

Writes (unique filenames — see ``entry4_eig_dump_paths.py``):

- ``DEMAtariIII_fsl_backward_entry4_rgm_spectral_python_engine_probe.pkl``
- ``DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_oracle_blocks.pkl``
- ``DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_dump_manifest.json``

Report: ``matlab_custom/fsl_backward_entry4_rgm_spectral_eig_dump_output.txt``

Overwrite: ``RGMS_ENTRY4_RGM_SPECTRAL_EIG_DUMP_REFRESH=1`` only.

See ``eig.md`` §7–8. Does **not** rerun Entries 1-3 or 5-12.
"""
from __future__ import annotations

import hashlib
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    assert_can_write,
    entry4_dump_manifest_json,
    entry4_dump_report_txt,
    entry4_eig_oracle_blocks_pkl,
    entry4_matlab_eig_records_mat,
    entry4_python_engine_probe_pkl,
    fsl_mdp_pre_entry4_pkl,
    write_manifest,
)


def _sub_hash(sub: np.ndarray) -> str:
    arr = np.asarray(sub, dtype=np.float64, order="F")
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def _extract_blocks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for rec in records:
        sub = np.asarray(rec["sub_mi"], dtype=np.float64)
        key = _sub_hash(sub)
        if key in seen:
            continue
        vals = rec.get("vals_mat")
        vecs = rec.get("vecs_mat")
        if vals is None or vecs is None:
            vals = np.asarray(rec["vals_use"], dtype=np.complex128)
            vecs = np.asarray(rec["vecs_use"], dtype=np.complex128)
        seen[key] = {
            "sub_mi": sub,
            "sub_hash": key,
            "vals_mat": np.asarray(vals, dtype=np.complex128).ravel(order="F"),
            "vecs_mat": np.asarray(vecs, dtype=np.complex128, order="F"),
            "jmax_mat": int(rec["jmax_mat"] if rec.get("jmax_mat") is not None else rec["jmax_use"]),
            "order_mat": np.asarray(
                rec["order_mat"] if rec.get("order_mat") is not None else rec["order_use"],
                dtype=np.int64,
            ),
            "chosen_mat": np.asarray(
                rec["chosen_mat"] if rec.get("chosen_mat") is not None else rec["chosen_use"],
                dtype=np.int64,
            ),
            "lev_call": int(rec.get("lev_call", -1)),
            "stream_idx": int(rec.get("stream_idx", -1)),
            "iter_idx": int(rec["iter_idx"]),
        }
    return list(seen.values())


def _append_report(lines: list[str]) -> None:
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def main() -> int:
    from python_src.toolbox.DEM.spm_faster_structure_learning import spm_faster_structure_learning
    from tests.oracle.toolbox.DEM.test_spm_faster_structure_learning import (
        _make_matlab_rgm_eig_pair,
        _make_rgm_mi_override_fn_matlab,
    )

    pre = fsl_mdp_pre_entry4_pkl()
    out_probe = entry4_python_engine_probe_pkl()
    out_blocks = entry4_eig_oracle_blocks_pkl()

    if not pre.is_file():
        print(
            f"[entry4 spectral dump] missing {pre}\n"
            "Run: python fsl_backward_materialize_mdp_pre_entry4_pkl.py",
            file=sys.stderr,
        )
        return 2

    try:
        assert_can_write(out_probe, label="python_engine_probe")
        assert_can_write(out_blocks, label="eig_oracle_blocks")
    except FileExistsError as exc:
        print(f"[entry4 spectral dump] {exc}", file=sys.stderr)
        return 3

    records: list[dict[str, Any]] = []

    def _probe(rec: dict) -> None:
        records.append(
            {
                "iter_idx": int(rec["iter_idx"]),
                "lev_call": int(rec["lev_call"]),
                "stream_idx": int(rec["stream_idx"]),
                "m": int(rec["m"]),
                "dx": int(rec["dx"]),
                "u_thresh": float(rec["u_thresh"]),
                "active_before": np.asarray(rec["active_before"], dtype=np.int64, copy=True),
                "sub_mi": np.asarray(rec["sub_mi"], dtype=np.float64, copy=True),
                "eig_source": str(rec["eig_source"]),
                "vals_py": np.asarray(rec["vals_py"], dtype=np.complex128, copy=True),
                "vecs_py": np.asarray(rec["vecs_py"], dtype=np.complex128, copy=True),
                "jmax_py": int(rec["jmax_py"]),
                "order_py": np.asarray(rec["order_py"], dtype=np.int64, copy=True),
                "chosen_py": np.asarray(rec["chosen_py"], dtype=np.int64, copy=True),
                "vals_mat": None
                if rec["vals_mat"] is None
                else np.asarray(rec["vals_mat"], dtype=np.complex128, copy=True),
                "vecs_mat": None
                if rec["vecs_mat"] is None
                else np.asarray(rec["vecs_mat"], dtype=np.complex128, copy=True),
                "jmax_mat": None if rec["jmax_mat"] is None else int(rec["jmax_mat"]),
                "order_mat": None
                if rec["order_mat"] is None
                else np.asarray(rec["order_mat"], dtype=np.int64, copy=True),
                "chosen_mat": None
                if rec["chosen_mat"] is None
                else np.asarray(rec["chosen_mat"], dtype=np.int64, copy=True),
                "vals_use": np.asarray(rec["vals_use"], dtype=np.complex128, copy=True),
                "vecs_use": np.asarray(rec["vecs_use"], dtype=np.complex128, copy=True),
                "jmax_use": int(rec["jmax_use"]),
                "order_use": np.asarray(rec["order_use"], dtype=np.int64, copy=True),
                "chosen_use": np.asarray(rec["chosen_use"], dtype=np.int64, copy=True),
            }
        )

    import matlab.engine

    dem_path = _REPO / "matlab_src" / "toolbox" / "DEM"
    eng = matlab.engine.start_matlab()
    try:
        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

        dem_path = configure_dem_matlab_engine(eng, _REPO)
        hooks = {
            "rgm_eig_pair": _make_matlab_rgm_eig_pair(eng),
            "rgm_mi_override_fn": _make_rgm_mi_override_fn_matlab(eng),
        }
        with pre.open("rb") as f:
            boundary = pickle.load(f)
        print(f"[entry4 spectral dump] input {pre}", file=sys.stderr, flush=True)
        mdp = spm_faster_structure_learning(
            boundary["pdp_o_sl"],
            np.asarray(boundary["S"], dtype=np.float64),
            int(boundary["Sc"]),
            rgm_eig_pair=hooks["rgm_eig_pair"],
            rgm_mi_override_fn=hooks["rgm_mi_override_fn"],
            rgm_spectral_probe_fn=_probe,
        )
        nm = len(mdp)
    finally:
        eng.quit()

    out_probe.parent.mkdir(parents=True, exist_ok=True)
    blocks = _extract_blocks(records)
    meta = {
        "source": "fsl_backward_dump_entry4_spectral_eig.py",
        "artifact_id": "DEMAtariIII_fsl_backward_entry4_rgm_spectral_python_engine_probe",
        "pre4_pkl": str(pre),
        "n_records": len(records),
        "n_blocks": len(blocks),
        "nm": int(nm),
        "matlab_mi": True,
        "matlab_eig": True,
        "utc": datetime.now(timezone.utc).isoformat(),
    }
    with out_probe.open("wb") as f:
        pickle.dump({"meta": meta, "records": records}, f, protocol=pickle.HIGHEST_PROTOCOL)
    blocks_meta = {**meta, "artifact_id": "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_oracle_blocks"}
    with out_blocks.open("wb") as f:
        pickle.dump({"meta": blocks_meta, "blocks": blocks}, f, protocol=pickle.HIGHEST_PROTOCOL)

    mat_path = entry4_matlab_eig_records_mat()
    report_lines = [
        f"=== Python engine probe dump {meta['utc']} ===",
        f"records={len(records)} blocks={len(blocks)} Nm={nm}",
        f"wrote_probe={out_probe}",
        f"wrote_blocks={out_blocks}",
        f"matlab_records_mat_present={mat_path.is_file()} path={mat_path}",
    ]
    _append_report(report_lines)
    manifest_path = write_manifest(
        extra={
            "last_python_dump_utc": meta["utc"],
            "n_records": len(records),
            "n_blocks": len(blocks),
        }
    )

    print(f"[entry4 spectral dump] records={len(records)} blocks={len(blocks)}", file=sys.stderr)
    print(f"[entry4 spectral dump] wrote {out_probe}", file=sys.stderr)
    print(f"[entry4 spectral dump] wrote {out_blocks}", file=sys.stderr)
    print(f"[entry4 spectral dump] manifest {manifest_path}", file=sys.stderr)
    if not mat_path.is_file():
        print(
            "[entry4 spectral dump] optional cross-check: run MATLAB dump_entry4_rgm_spectral_eig.m",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
