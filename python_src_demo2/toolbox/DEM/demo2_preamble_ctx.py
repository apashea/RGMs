"""DEMO2 preamble boundary — save/load full ``run_dem_atariiii(entry_stop=12)`` ``ctx``.

See ``Atari_example.md`` § **ENTRY DEMO2 FULL ATARI** — **Preamble boundary dumps**.
"""

from __future__ import annotations

import copy
import json
import os
import pickle
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np

DEMO2_PREAMBLE_CTX_SCHEMA = "demo2_preamble_ctx_v1"
DEMO2_PREAMBLE_MANIFEST_SCHEMA = "demo2_preamble_manifest_v1"
DEMO2_PREAMBLE_ENTRY_STOP = 12

_NATIVE_RAND_PATCH_TARGETS = (
    "numpy.random.rand",
    "python_src.toolbox.DEM.spm_MDP_generate.np.random.rand",
    "python_src.toolbox.DEM.spm_MDP_pong.np.random.rand",
)

# Full driver ``ctx`` is dumped (no field stripping). These keys must be present on load.
_DEMO2_PREAMBLE_REQUIRED_CTX_KEYS: tuple[str, ...] = (
    "MDP",
    "GDP",
    "C",
    "Ne",
    "Nm",
    "RGB",
    "S",
    "RDP",
    "PDP",
)

# Documented for audit; not enforced on load (may vary by driver version).
_DEMO2_PREAMBLE_OPTIONAL_CTX_KEYS: tuple[str, ...] = (
    "hid",
    "cid",
    "con",
    "P",
    "entry6_windows",
    "entry8_NT",
    "entry8_outer",
    "entry10_j",
    "entry10_Nt",
    "NS",
    "NU",
    "NA",
    "NO",
    "NH",
    "r",
    "c",
    "_entry12_use_partial_vb",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_demo2_preamble_manifest_json_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_demo2_preamble_manifest.json"


def default_demo2_preamble_native_rand_mat_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_demo2_preamble_native_rand.mat"


def _fixtures_dir() -> Path:
    return _repo_root() / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"


def _rel_fixture(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return str(path)


def build_demo2_preamble_companion_manifest(
    *,
    primary_ctx_pkl: Path,
    native_rand_mat: Path | None = None,
    k_native: int | None = None,
) -> dict[str, Any]:
    """
    Registry of companion artifacts for DEMO2 preamble validation (RNG + structure learning).

    Written alongside the primary ctx PKL so lane B / oracle work does not re-derive paths ad hoc.
    """
    fix = _fixtures_dir()
    manifest: dict[str, Any] = {
        "schema": DEMO2_PREAMBLE_MANIFEST_SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ledger_boundary": (
            "run_dem_atariiii(entry_stop=12) — DEM_AtariIII.m after first illustrate VB; "
            "before Active inference (GDP attach)"
        ),
        "primary_ctx_pkl": _rel_fixture(primary_ctx_pkl),
        "native_python_rng": {
            "path": _rel_fixture(native_rand_mat) if native_rand_mat else None,
            "K_py": k_native,
            "producer": "demo2_preamble_ctx.capture_native_scalar_rand during preamble dump",
            "role": (
                "Scalar np.random.rand() log for native lane-A preamble — audit / future replay; "
                "not Entry 12 vb_rand_buf"
            ),
            "patch_targets": list(_NATIVE_RAND_PATCH_TARGETS),
        },
        "rng_matlab_ledger": {
            "dem_atari_through_entry11": {
                "path": _rel_fixture(fix / "dem_atari_rand_buf_through_entry11.mat"),
                "producer": "matlab_custom/fsl_backward/capture_dem_atari_rand_buf_through_entry11.m",
                "fields": ["dem_atari_rand_buf", "K_11", "RDP_reference", "meta"],
                "role": "MATLAB rng(2) scalar rand() through Entry 11 — FSL backward replay",
                "replay_code": "tests/oracle/toolbox/DEM/fsl_backward_rand.py",
                "replay_env": "RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS=1",
            },
            "dem_atari_through_entry12": {
                "path": _rel_fixture(fix / "dem_atari_rand_buf_through_entry12.mat"),
                "producer": "matlab_custom/fsl_backward/capture_dem_atari_rand_buf_through_entry12.m",
                "status": "lane_b_run_matlab_producer_before_signoff",
                "role": (
                    "FSL dem_atari_rand_buf through Entry 12 preamble (ends before call-1 VB); "
                    "distinct from vb_rand_buf"
                ),
            },
            "entry12_vb_call1_rgms_canonical": {
                "K_mat": _rel_fixture(fix / "entry12_vb_rand_K.mat"),
                "buf_mat": _rel_fixture(fix / "DEMAtariIII_entry12_vb_matlab_rand_buf.mat"),
                "rdp_mat": _rel_fixture(fix / "DEMAtariIII_XXX_12_rdp.mat"),
                "pdp_mat": _rel_fixture(fix / "DEMAtariIII_XXX_12_pdp.mat"),
                "producer_1a": "tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py",
                "producer_1b": "matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m",
                "tag": "rgms_canonical",
                "role": "Entry 12 first VB — vb_rand_buf replay (not dem_atari_rand_buf)",
                "replay_code": "python_src/toolbox/DEM/entry12_atari_calls.py + spm_MDP_VB_XXX reuse_matlab_draws",
                "compare_script": "tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py",
            },
        },
        "structure_learning_entry4": {
            "matlab_authority_mat": _rel_fixture(
                fix / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
            ),
            "producer": "matlab_custom/fsl_backward/dump_MDP_pre_entry10.m",
            "key_fields": [
                "MDP_pre_entry5",
                "PDP_O",
                "PDP_o",
                "GDP_id_reward",
                "GDP_id_contraint",
                "C",
                "Ne",
                "Nm",
                "meta",
            ],
            "ledger_line": "MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);",
            "python_module": "python_src/toolbox/DEM/spm_faster_structure_learning.py",
            "python_ledger": "python_src/toolbox/DEM/dem_atariiii_entry4.py",
            "oracle_tests": [
                "tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py",
                "tests/oracle/toolbox/DEM/fsl_backward_compare_entry4_pkl_to_mat.py",
            ],
            "ctx_keys_carrying_inputs": ["PDP", "GDP", "S", "MDP"],
            "note": (
                "Primary ctx PKL holds post-preamble MDP; Entry 4 authority mat holds "
                "PDP.O columns + MDP_pre_entry5 on rng(2) ledger for paired oracle"
            ),
        },
        "structure_learning_merge_loops": {
            "matlab_authority_mat": _rel_fixture(
                fix / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
            ),
            "fields": ["MDP_pre_entry7", "MDP_pre_entry9", "MDP_pre_entry10", "PDP_O", "PDP_o"],
            "matlab_lines": "DEM_AtariIII.m 131 (Entry 7), 153 (Entry 8/9 basin loop)",
            "python_merge": "python_src/toolbox/DEM/spm_merge_structure_learning.py",
            "oracle": "tests/oracle/toolbox/DEM/test_spm_merge_structure_learning.py",
        },
        "structure_learning_entry10_sort": {
            "matlab_authority_mat": _rel_fixture(
                fix / "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat"
            ),
            "producer": "matlab_custom/fsl_backward/dump_MDP_pre_entry11.m",
            "field": "MDP_pre_entry11",
            "matlab_line": "DEM_AtariIII.m 181 spm_RDP_sort",
            "note": "Entry 10 NESS sort boundary before call 1 assembly",
        },
        "structure_learning_post12_nr_loop": {
            "matlab_lines": "DEM_AtariIII.m 303 — spm_merge_structure_learning(O(:,t+s),MDP) per NR game",
            "input_source": "PDP.Q.O{1} from each spm_MDP_VB_XXX in NR loop — not training PDP.O",
            "planned_authority_mat": _rel_fixture(
                fix / "DEMAtariIII_demo2_MDP_pre_call3_post_nr.mat"
            ),
            "planned_producer": "matlab_custom/demo2/dump_MDP_pre_call3_post_nr.m",
            "status": "lane_b_run_matlab_producer_before_signoff",
            "partial_oracle": "tests/oracle/toolbox/DEM/test_demo2_post_nr_rdp_assembly.py (NR=1 smoke)",
            "entry12_inline_nr": (
                "DEMAtariIII_entry12_dump_all_subentries capture_call3/call4 runs full NR=32 "
                "in one rng(2) session before call 3/4 VB capture"
            ),
        },
        "rng_whole_script_policy": {
            "matlab_seed_line": "DEM_AtariIII.m line 53 rng(2) — single seed for entire script",
            "dem_atari_lane": "FSL rand.m shadow — essentially spm_MDP_generate (line 86); no re-seed post-12",
            "vb_lane": "entry12 rand.m shadow — per script-level VB tag; NR games 2-32 VB not individually buffered",
            "structure_learning_uses_rand": False,
        },
        "demo2_full_script_gaps": [
            "MATLAB: dump_MDP_pre_post_preamble.m → DEMAtariIII_demo2_MDP_pre_post_preamble.mat",
            "MATLAB: dump_MDP_post_gdp_attach.m → DEMAtariIII_demo2_MDP_post_gdp_attach.mat",
            "MATLAB: dump_MDP_post_nr_game1.m → DEMAtariIII_demo2_MDP_post_nr_game1.mat",
            "Python: demo2_lane_b_preflight_rand_k_preamble.py",
            "Python: demo2_lane_b_run_preamble_isolated.py + demo2_lane_b_compare_preamble_pkl_to_mat.py",
            "Python: demo2_lane_b_run_gdp_attach_isolated.py + demo2_lane_b_compare_gdp_attach_pkl_to_mat.py",
            "Python: demo2_lane_b_run_nr1_isolated.py + demo2_lane_b_compare_nr1_mdp_pkl_to_mat.py",
        ],
        "demo2_post12_vb_tags": {
            "call2": "rgms_atari_call2",
            "call3": "rgms_atari_call3",
            "call4": "rgms_atari_call4",
            "registry": "python_src/toolbox/DEM/entry12_atari_calls.py",
            "note": "Each tag has its own entry12_vb_rand_K_<tag>.mat + vb_matlab_rand_buf_<tag>.mat after 1b",
        },
        "policy": (
            "Dump full ctx + native rand log + this manifest in one bundle after every verified "
            "full-scale preamble run. Do not rely on ctx alone for MATLAB paired DEMO2 validation."
        ),
    }
    return manifest


@contextmanager
def capture_native_scalar_rand() -> Iterator[list[float]]:
    """Record scalar ``np.random.rand()`` draws during native preamble (lane A audit buffer)."""
    from unittest.mock import patch

    buf: list[float] = []
    real_rand = np.random.rand

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError(
                "DEMO2 native rand capture: only scalar np.random.rand() supported"
            )
        v = float(real_rand())
        buf.append(v)
        return v

    patches = [patch(t, side_effect=shim) for t in _NATIVE_RAND_PATCH_TARGETS]
    try:
        for p in patches:
            p.start()
        yield buf
    finally:
        for p in reversed(patches):
            p.stop()


def dump_demo2_preamble_native_rand_mat(buf: list[float], *, path: Path | None = None) -> Path:
    from scipy.io import savemat

    out = path or default_demo2_preamble_native_rand_mat_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(buf, dtype=np.float64).ravel()
    k_py = int(arr.size)
    savemat(
        str(out),
        {
            "native_rand_buf": arr.reshape(-1, 1),
            "K_py": np.asarray([[k_py]], dtype=np.float64),
            "meta": {
                "schema": "demo2_preamble_native_rand_v1",
                "note": "Python native scalar rand log — not MATLAB dem_atari_rand_buf or vb_rand_buf",
            },
        },
    )
    print(
        f"[DEMO2 preamble] wrote native rand mat {out} (K_py={k_py})",
        file=sys.stderr,
        flush=True,
    )
    return out


def dump_demo2_preamble_manifest(
    manifest: dict[str, Any], *, path: Path | None = None
) -> Path:
    out = path or default_demo2_preamble_manifest_json_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[DEMO2 preamble] wrote manifest {out}", file=sys.stderr, flush=True)
    return out


def dump_demo2_preamble_bundle(
    ctx: dict[str, Any],
    *,
    source: str,
    native_rand_buf: list[float] | None = None,
    ctx_path: Path | None = None,
) -> dict[str, Path]:
    """Write ctx PKL + native rand mat + companion manifest (full preamble bundle)."""
    pkl = dump_demo2_preamble_ctx(ctx, source=source, path=ctx_path)
    native_path: Path | None = None
    k_native: int | None = None
    if native_rand_buf is not None:
        native_path = dump_demo2_preamble_native_rand_mat(native_rand_buf)
        k_native = len(native_rand_buf)
    manifest = build_demo2_preamble_companion_manifest(
        primary_ctx_pkl=pkl,
        native_rand_mat=native_path,
        k_native=k_native,
    )
    manifest_path = dump_demo2_preamble_manifest(manifest)
    return {"ctx_pkl": pkl, "native_rand_mat": native_path, "manifest_json": manifest_path}


def default_demo2_preamble_ctx_pkl_path() -> Path:
    return _fixtures_dir() / "DEMAtariIII_demo2_preamble_ctx.pkl"


def resolve_demo2_preamble_ctx_pkl_path() -> Path:
    raw = str(os.getenv("RGMS_DEMO2_PREAMBLE_CTX_PKL", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return default_demo2_preamble_ctx_pkl_path()


def demo2_preamble_ctx_load_enabled() -> bool:
    return str(os.getenv("RGMS_DEMO2_LOAD_PREAMBLE_CTX", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def demo2_preamble_ctx_dump_enabled() -> bool:
    return str(os.getenv("RGMS_DEMO2_DUMP_PREAMBLE_CTX", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _env_snapshot_for_meta() -> dict[str, str]:
    keys = (
        "RGMS_ATARI_TRAINING_T",
        "RGMS_ATARI_ENTRY8_OUTER",
        "RGMS_ATARI_TAG",
        "RGMS_ATARI_NR",
        "RGMS_ATARI_NT",
        "RGMS_ATARI_NS",
    )
    return {k: str(os.getenv(k, "")).strip() for k in keys}


def build_demo2_preamble_blob(ctx: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Wrap full driver ``ctx`` with provenance metadata (no compute fields removed)."""
    ctx_copy = copy.deepcopy(ctx)
    return {
        "schema": DEMO2_PREAMBLE_CTX_SCHEMA,
        "entry_stop": DEMO2_PREAMBLE_ENTRY_STOP,
        "source": str(source),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "driver_module": "python_src.toolbox.DEM.DEM_AtariIII.run_dem_atariiii",
        "matlab_boundary": "DEM_AtariIII.m after first illustrate VB; before Active inference (GDP attach)",
        "env": _env_snapshot_for_meta(),
        "ctx_top_level_keys": sorted(ctx_copy.keys(), key=str),
        "ctx": ctx_copy,
    }


def validate_demo2_preamble_blob(blob: dict[str, Any]) -> dict[str, Any]:
    """Return ``ctx`` after schema/required-key checks."""
    if not isinstance(blob, dict):
        raise TypeError(f"DEMO2 preamble blob must be dict, got {type(blob)}")
    if "ctx" in blob and blob.get("schema") == DEMO2_PREAMBLE_CTX_SCHEMA:
        ctx = blob["ctx"]
    elif "MDP" in blob and "GDP" in blob:
        # Raw ``run_dem_atariiii`` checkpoint (e.g. ``RGMS_ATARI_CAPTURE_ENTRY12_POST``).
        ctx = blob
    else:
        schema = blob.get("schema")
        raise ValueError(
            f"DEMO2 preamble unloadable: expected schema {DEMO2_PREAMBLE_CTX_SCHEMA!r} "
            f"with ctx, or raw driver ctx; got schema={schema!r}, top keys={sorted(blob.keys())}"
        )
    if not isinstance(ctx, dict):
        raise TypeError("DEMO2 preamble ctx must be dict")
    missing = [k for k in _DEMO2_PREAMBLE_REQUIRED_CTX_KEYS if k not in ctx]
    if missing:
        raise KeyError(f"DEMO2 preamble ctx missing required keys: {missing}")
    return ctx


def dump_demo2_preamble_ctx(
    ctx: dict[str, Any],
    *,
    source: str,
    path: Path | None = None,
) -> Path:
    """Write full preamble ``ctx`` + metadata to PKL (default or ``RGMS_DEMO2_PREAMBLE_CTX_PKL``)."""
    out = path or resolve_demo2_preamble_ctx_pkl_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = build_demo2_preamble_blob(ctx, source=source)
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(
        f"[DEMO2 preamble] wrote {out} "
        f"(schema={DEMO2_PREAMBLE_CTX_SCHEMA}, keys={len(blob['ctx'])})",
        file=sys.stderr,
        flush=True,
    )
    return out


def load_demo2_preamble_ctx(*, path: Path | None = None) -> dict[str, Any]:
    """Load preamble ``ctx`` from PKL; validates schema and required keys."""
    p = path or resolve_demo2_preamble_ctx_pkl_path()
    if not p.is_file():
        raise FileNotFoundError(f"DEMO2 preamble ctx PKL not found: {p}")
    with p.open("rb") as f:
        blob = pickle.load(f)
    ctx = validate_demo2_preamble_blob(blob)
    provenance = (
        blob.get("source")
        if blob.get("schema") == DEMO2_PREAMBLE_CTX_SCHEMA
        else "raw_driver_ctx_checkpoint"
    )
    print(
        f"[DEMO2 preamble] loaded {p} (provenance={provenance!r}, "
        f"created_utc={blob.get('created_utc')!r})",
        file=sys.stderr,
        flush=True,
    )
    return ctx


def acquire_demo2_preamble_ctx(*, source: str) -> tuple[dict[str, Any], bool]:
    """
    Load preamble from PKL when ``RGMS_DEMO2_LOAD_PREAMBLE_CTX=1``, else run ``entry_stop=12``.

    Returns ``(ctx, resumed)`` where ``resumed`` is True when loaded from disk.
    """
    if demo2_preamble_ctx_load_enabled():
        from python_src_demo2.toolbox.DEM.demo2_preflight import run_demo2_preflight

        run_demo2_preflight(mode="resume")
        return load_demo2_preamble_ctx(), True

    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii

    capture_buf: list[float] | None = None
    if demo2_preamble_ctx_dump_enabled():
        with capture_native_scalar_rand() as buf:
            ctx = run_dem_atariiii(entry_stop=DEMO2_PREAMBLE_ENTRY_STOP)
            capture_buf = list(buf)
    else:
        ctx = run_dem_atariiii(entry_stop=DEMO2_PREAMBLE_ENTRY_STOP)

    if demo2_preamble_ctx_dump_enabled():
        dump_demo2_preamble_bundle(
            ctx,
            source=source,
            native_rand_buf=capture_buf,
        )
    return ctx, False
