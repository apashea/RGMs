"""Entry 12 Atari VB call-site registry (``DEM_AtariIII.m`` four ``spm_MDP_VB_XXX`` invocations).

Authoritative script map, artifact paths, and RNG interconnections:
``Atari_example.md`` § **Entry 12 — primary scripts, wiring, and RNG interconnections**.

This module resolves ``tag`` → fixture paths, oracle flags, and ``K``/``vb_rand_buf`` coherence checks
used by scripts **1a**, **3**, and **4**.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    rgms_repo_root,
)

# Phase 1a oracle (call 1, ~line 217, RDP.T=64 after FSL 1–11 ledger).
ENTRY12_ATARI_CALL1_TAG = "rgms_canonical"
# Pre-checkX ``RDP`` saved by script **1b** (``entry12_xxx12_rdp_mat_``); same file script **4** uses.
ENTRY12_ATARI_CALL1_RDP_MAT = "DEMAtariIII_XXX_12_rdp.mat"

# Phase 1b — call 2 game 1 (~line 268, spm_mdp2rdp(...,0,1/NS), T=fix(NT/Ne)).
ENTRY12_ATARI_CALL2_TAG = "rgms_atari_call2"
ENTRY12_ATARI_CALL2_RDP_MAT = "DEMAtariIII_XXX_12_rgms_atari_call2_rdp.mat"

# Call 3 — post NR-loop, spm_RDP_sort, T=128 (~line 340).
ENTRY12_ATARI_CALL3_TAG = "rgms_atari_call3"
ENTRY12_ATARI_CALL3_RDP_MAT = "DEMAtariIII_XXX_12_rgms_atari_call3_rdp.mat"

# Call 4 — post NR-loop, spm_RDP_sort + spm_RDP_MI, T=128 (~line 390).
ENTRY12_ATARI_CALL4_TAG = "rgms_atari_call4"
ENTRY12_ATARI_CALL4_RDP_MAT = "DEMAtariIII_XXX_12_rgms_atari_call4_rdp.mat"

# Registered Atari VB oracle tags (multi-tag regression gate).
ENTRY12_ATARI_VB_TAGS: tuple[str, ...] = (
    ENTRY12_ATARI_CALL1_TAG,
    ENTRY12_ATARI_CALL2_TAG,
    ENTRY12_ATARI_CALL3_TAG,
    ENTRY12_ATARI_CALL4_TAG,
)

# Dump bands **12A**–**12I** (script **1b** ``.mat`` + script **3** ``.pkl`` pairs).
ENTRY12_SUBENTRY_BAND_CODES: tuple[str, ...] = tuple(f"12{c}" for c in "ABCDEFGHI")

ENTRY12_SIGNOFF_MANIFEST_SCHEMA = 2


def entry12_fixtures_dir() -> Path:
    raw = str(os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return rgms_repo_root() / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"


def entry12_atari_call_rdp_mat_path(tag: str) -> Path:
    """Absolute path to input ``RDP`` ``.mat`` for a registered call ``tag``."""
    if tag in (ENTRY12_ATARI_CALL1_TAG, ENTRY12_CANONICAL_RUN_TAG):
        name = ENTRY12_ATARI_CALL1_RDP_MAT
    elif tag == ENTRY12_ATARI_CALL2_TAG:
        name = ENTRY12_ATARI_CALL2_RDP_MAT
    elif tag == ENTRY12_ATARI_CALL3_TAG:
        name = ENTRY12_ATARI_CALL3_RDP_MAT
    elif tag == ENTRY12_ATARI_CALL4_TAG:
        name = ENTRY12_ATARI_CALL4_RDP_MAT
    else:
        raise KeyError(f"unknown Entry 12 Atari call tag: {tag!r}")
    return entry12_fixtures_dir() / name


def entry12_atari_call_pdp_artifact_paths(tag: str) -> dict[str, Path]:
    """Paired ``.mat`` / ``.pkl`` paths for script **3** / **4** (tag-specific PDP)."""
    fix = entry12_fixtures_dir()
    if tag in (ENTRY12_ATARI_CALL1_TAG, ENTRY12_CANONICAL_RUN_TAG):
        return {
            "rdp_mat": fix / "DEMAtariIII_XXX_12_rdp.mat",
            "rdp_pkl": fix / "DEMAtariIII_XXX_12_rdp.pkl",
            "pdp_mat": fix / "DEMAtariIII_XXX_12_pdp.mat",
            "pdp_pkl": fix / "DEMAtariIII_XXX_12_pdp.pkl",
            "rand_buf": fix / "DEMAtariIII_entry12_vb_matlab_rand_buf.mat",
        }
    if tag in (
        ENTRY12_ATARI_CALL2_TAG,
        ENTRY12_ATARI_CALL3_TAG,
        ENTRY12_ATARI_CALL4_TAG,
    ):
        return {
            "rdp_mat": fix / entry12_atari_call_rdp_mat_path(tag).name,
            "rdp_pkl": fix / f"DEMAtariIII_XXX_12_{tag}_rdp.pkl",
            "pdp_mat": fix / f"DEMAtariIII_XXX_12_{tag}_pdp.mat",
            "pdp_pkl": fix / f"DEMAtariIII_XXX_12_{tag}_pdp.pkl",
            "rand_buf": fix / f"DEMAtariIII_entry12_vb_matlab_rand_buf_{tag}.mat",
        }
    raise KeyError(f"unknown Entry 12 Atari call tag: {tag!r}")


def entry12_resolve_run_tag() -> str:
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_capture_run_tag

    return entry12_capture_run_tag()


def entry12_vb_oracle_flags(*, reuse_matlab_draws: bool) -> dict[str, Any]:
    """
    Shared ``spm_MDP_VB_XXX`` keyword flags for Entry 12 oracle scripts.

    Call **1** (``rgms_canonical``) and call **2** (``rgms_atari_call2``) use the same
    contract (``Atari_example.md`` § Phase 1 oracle RNG): script **1a** counts with
    ``reuse_matlab_draws=False``; scripts **3** and draw audit replay ``vb_rand_buf``.
    """
    return {
        "monitoring": False,
        "dump_subentries": True,
        "reuse_matlab_draws": bool(reuse_matlab_draws),
    }


def entry12_signoff_artifact_paths(tag: str | None = None) -> dict[str, Path]:
    """
    Canonical paired paths for scripts **1a/1b → 3 → 4** on ``tag``.

    ``rdp_mat`` is the **pre-checkX** ``RDP`` saved by script **1b** (VB input snapshot).
    Script **3** loads it, runs ``entry12_rdp_for_vb_from_mat_nested`` (checkX), then
    ``spm_MDP_VB_XXX`` (checkX again on copy). Script **4** compares input ``RDP`` pickle
    vs this ``.mat`` through the validation lane (checkX + transform align).
    """
    tag_use = (tag or entry12_resolve_run_tag()).strip()
    from python_src.toolbox.DEM.entry12_matlab_capture import default_entry12_vb_rand_k_mat_path

    base = entry12_atari_call_pdp_artifact_paths(tag_use)
    base["rand_k"] = default_entry12_vb_rand_k_mat_path(tag_use)
    base["manifest"] = entry12_signoff_manifest_path(tag_use)
    base["_tag"] = tag_use  # metadata for logging; not a filesystem path
    return base


def entry12_signoff_manifest_path(tag: str | None = None) -> Path:
    """Path to per-tag sign-off manifest written by MATLAB script **1b**."""
    tag_use = (tag or entry12_resolve_run_tag()).strip()
    return entry12_fixtures_dir() / f"entry12_signoff_manifest_{tag_use}.json"


def _sha256_file_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def entry12_quick_digest(path: Path, *, prefix_hex: int = 12) -> str:
    """Short digest token for logs."""
    return _sha256_file_hex(path)[: int(prefix_hex)]


def entry12_subentry_pkl_path(tag: str, code: str, *, out_dir: Path | str | None = None) -> Path:
    """``DEMAtariIII_entry12_<tag>_12X.pkl`` (script **3** subentry workspace)."""
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_subentry_mat_filename

    fix = Path(out_dir).expanduser().resolve() if out_dir is not None else entry12_fixtures_dir()
    name = entry12_subentry_mat_filename(tag, code).replace(".mat", ".pkl")
    return fix / name


def _manifest_subentry_dict(checksums: dict[str, Any], key: str) -> dict[str, str]:
    block = checksums.get(key, {})
    if block is None:
        return {}
    if not isinstance(block, dict):
        raise TypeError(f"manifest checksums[{key!r}] must be an object")
    out: dict[str, str] = {}
    for code, hex_val in block.items():
        if not isinstance(hex_val, str) or not hex_val:
            raise TypeError(f"manifest {key}[{code!r}] must be a non-empty sha256 hex string")
        out[str(code)] = hex_val
    return out


def _assert_manifest_file_checksum(path: Path, expected_hex: str, *, label: str, tag: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"manifest expects {label} at {path} for tag {tag!r} but file is missing. "
            "Re-run 1a→1b→3 on this tag."
        )
    got = _sha256_file_hex(path)
    if got != expected_hex:
        raise ValueError(
            f"manifest checksum mismatch for {label} on tag {tag!r} "
            f"(got {got[:12]}… expected {expected_hex[:12]}…). "
            "Artifacts are stale/mixed; re-run 1a→1b→3 on this tag."
        )


def entry12_write_signoff_manifest(manifest: dict[str, Any], tag: str | None = None) -> Path:
    """Persist manifest JSON (atomic replace)."""
    tag_use = (tag or str(manifest.get("tag", ""))).strip()
    path = entry12_signoff_manifest_path(tag_use)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def entry12_upgrade_manifest_schema2_mat_only(tag: str | None = None) -> Path:
    """
    Upgrade an existing manifest to schema **2** by hashing on-disk **12A–12I** ``.mat`` files.

    Use when **1b** mats are current but the manifest predates ``subentry_mat`` checksums
  (no MATLAB re-run). Does not add script **3** pickle checksums.
    """
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_subentry_mat_path

    paths = entry12_signoff_artifact_paths(tag)
    tag_s = str(paths["_tag"])
    try:
        manifest = entry12_load_signoff_manifest(tag_s)
    except FileNotFoundError:
        manifest = {
            "tag": tag_s,
            "capture_mode": "upgrade_from_disk",
            "checksums": {},
        }
    checksums = manifest.get("checksums")
    if not isinstance(checksums, dict):
        checksums = {}
    if paths["rand_k"].is_file():
        manifest["K"] = entry12_load_k_from_mat(tag_s)
    if paths["rand_buf"].is_file():
        manifest["vb_rand_buf_len"] = int(entry12_load_vb_rand_buf_for_tag(tag_s).size)

    sub_mat: dict[str, str] = {}
    for code in ENTRY12_SUBENTRY_BAND_CODES:
        mat_p = entry12_subentry_mat_path(tag_s, code)
        if mat_p.is_file():
            sub_mat[code] = _sha256_file_hex(mat_p)

    checksums["rdp_mat_sha256"] = _sha256_file_hex(paths["rdp_mat"])
    checksums["pdp_mat_sha256"] = _sha256_file_hex(paths["pdp_mat"])
    checksums["rand_buf_mat_sha256"] = _sha256_file_hex(paths["rand_buf"])
    checksums["subentry_mat"] = sub_mat
    manifest["checksums"] = checksums
    manifest["manifest_schema"] = ENTRY12_SIGNOFF_MANIFEST_SCHEMA
    out = entry12_write_signoff_manifest(manifest, tag_s)
    print(
        f"[entry12 signoff] upgraded manifest schema2 mat checksums "
        f"({len(sub_mat)} subentries): {out}",
        flush=True,
    )
    return out


def entry12_assert_draw_audit_summary(
    summary_path: Path | str | None = None,
) -> None:
    """Fail if ``entry12_draw_index_audit.py`` did not report coherent replay."""
    from python_src.toolbox.DEM.entry12_matlab_capture import rgms_repo_root

    path = (
        Path(summary_path).expanduser().resolve()
        if summary_path is not None
        else rgms_repo_root() / "matlab_custom" / "entry12_draw_index_audit_results.json"
    )
    if not path.is_file():
        raise FileNotFoundError(
            f"missing draw audit summary: {path}. Run matlab_custom/entry12_draw_index_audit.py."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    coh = raw.get("coherence", {})
    if not coh.get("unused_draws_ok"):
        raise ValueError(
            f"draw audit unused_draws not ok (see {path}). Fix RNG replay before script 4."
        )
    if not coh.get("sample_calls_match"):
        raise ValueError(
            f"draw audit sample_calls_match false (see {path}). Fix RNG replay before script 4."
        )


def entry12_refresh_manifest_script3_checksums(tag: str | None = None) -> Path:
    """
    After script **3**, record SHA-256 for ``rdp``/``pdp`` pickles and **12A–12I** ``.pkl`` files.

    Preserves MATLAB **1b** ``subentry_mat`` checksums; adds ``subentry_pkl`` and top-level pkl hashes.
    """
    paths = entry12_signoff_artifact_paths(tag)
    tag_s = str(paths["_tag"])
    manifest = entry12_load_signoff_manifest(tag_s)
    checksums = manifest.get("checksums")
    if not isinstance(checksums, dict):
        raise TypeError("manifest checksums must be an object")

    sub_pkl: dict[str, str] = {}
    for code in ENTRY12_SUBENTRY_BAND_CODES:
        pkl_p = entry12_subentry_pkl_path(tag_s, code)
        if pkl_p.is_file():
            sub_pkl[code] = _sha256_file_hex(pkl_p)
    checksums["subentry_pkl"] = sub_pkl
    checksums["rdp_pkl_sha256"] = _sha256_file_hex(paths["rdp_pkl"])
    checksums["pdp_pkl_sha256"] = _sha256_file_hex(paths["pdp_pkl"])
    manifest["checksums"] = checksums
    manifest["script3"] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    manifest["manifest_schema"] = ENTRY12_SIGNOFF_MANIFEST_SCHEMA
    out = entry12_write_signoff_manifest(manifest, tag_s)
    print(
        f"[entry12 signoff] refreshed manifest script3 checksums ({len(sub_pkl)} subentry pkls): {out}",
        flush=True,
    )
    return out


def entry12_load_signoff_manifest(tag: str | None = None) -> dict[str, Any]:
    """Load per-tag sign-off manifest JSON written by script **1b**."""
    tag_use = (tag or entry12_resolve_run_tag()).strip()
    p = entry12_signoff_manifest_path(tag_use)
    if not p.is_file():
        raise FileNotFoundError(
            f"missing sign-off manifest for tag {tag_use!r}: {p}. "
            "Run script 1b for this tag to refresh fixtures."
        )
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"manifest must be JSON object: {p}")
    return raw


def entry12_assert_manifest_coherent(
    tag: str | None = None,
    *,
    require_script3_pkls: bool = True,
) -> None:
    """Verify manifest matches current paired artifacts (tag, K, lengths, checksums)."""
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_subentry_mat_path

    paths = entry12_signoff_artifact_paths(tag)
    tag_s = str(paths["_tag"])
    m = entry12_load_signoff_manifest(tag_s)

    tag_m = str(m.get("tag", "")).strip()
    if tag_m != tag_s:
        raise ValueError(f"manifest tag mismatch: manifest={tag_m!r} expected={tag_s!r}")

    schema = int(m.get("manifest_schema", 1))
    if schema < ENTRY12_SIGNOFF_MANIFEST_SCHEMA:
        raise ValueError(
            f"manifest for tag {tag_s!r} is schema {schema} (need {ENTRY12_SIGNOFF_MANIFEST_SCHEMA} "
            "with subentry_mat checksums). Re-run script 1b on this tag."
        )

    checksums = m.get("checksums", {})
    if not isinstance(checksums, dict):
        raise TypeError("manifest checksums must be an object")
    for key in ("rdp_mat_sha256", "pdp_mat_sha256", "rand_buf_mat_sha256"):
        if not isinstance(checksums.get(key), str) or not checksums[key]:
            raise KeyError(f"manifest missing checksum key {key!r}")

    sub_mat = _manifest_subentry_dict(checksums, "subentry_mat")
    if not sub_mat:
        raise KeyError(
            f"manifest missing checksums.subentry_mat for tag {tag_s!r}. Re-run script 1b."
        )

    k_pref = entry12_load_k_from_mat(tag_s)
    k_man = int(m.get("K", -1))
    if k_pref != k_man:
        raise ValueError(
            f"manifest K mismatch for tag {tag_s!r}: manifest={k_man} preflight={k_pref}. "
            "Re-run 1a→1b on this tag."
        )

    k_buf = int(entry12_load_vb_rand_buf_for_tag(tag_s).size)
    k_buf_man = int(m.get("vb_rand_buf_len", -1))
    if k_buf != k_buf_man:
        raise ValueError(
            f"manifest vb_rand_buf_len mismatch for tag {tag_s!r}: "
            f"manifest={k_buf_man} actual={k_buf}. Re-run 1b on this tag."
        )

    _assert_manifest_file_checksum(
        paths["rdp_mat"], checksums["rdp_mat_sha256"], label="rdp_mat", tag=tag_s
    )
    _assert_manifest_file_checksum(
        paths["pdp_mat"], checksums["pdp_mat_sha256"], label="pdp_mat", tag=tag_s
    )
    _assert_manifest_file_checksum(
        paths["rand_buf"], checksums["rand_buf_mat_sha256"], label="rand_buf_mat", tag=tag_s
    )

    for code, expected in sorted(sub_mat.items()):
        mat_p = entry12_subentry_mat_path(tag_s, code)
        _assert_manifest_file_checksum(
            mat_p, expected, label=f"subentry_mat[{code}]", tag=tag_s
        )

    if not require_script3_pkls:
        return

    for key in ("rdp_pkl_sha256", "pdp_pkl_sha256"):
        if not isinstance(checksums.get(key), str) or not checksums[key]:
            raise KeyError(
                f"manifest missing {key!r} for tag {tag_s!r}. "
                "Run script 3 then entry12_refresh_manifest_script3_checksums."
            )

    sub_pkl = _manifest_subentry_dict(checksums, "subentry_pkl")
    if not sub_pkl:
        raise KeyError(
            f"manifest missing checksums.subentry_pkl for tag {tag_s!r}. Run script 3."
        )

    _assert_manifest_file_checksum(
        paths["rdp_pkl"], checksums["rdp_pkl_sha256"], label="rdp_pkl", tag=tag_s
    )
    _assert_manifest_file_checksum(
        paths["pdp_pkl"], checksums["pdp_pkl_sha256"], label="pdp_pkl", tag=tag_s
    )
    for code, expected in sorted(sub_pkl.items()):
        pkl_p = entry12_subentry_pkl_path(tag_s, code)
        _assert_manifest_file_checksum(
            pkl_p, expected, label=f"subentry_pkl[{code}]", tag=tag_s
        )


def entry12_assert_signoff_chain_ready(
    tag: str | None = None,
    *,
    require_rand_buf: bool = True,
    require_k: bool = True,
    require_manifest: bool = True,
    require_script3_pkls: bool = True,
) -> dict[str, Path]:
    """
    Fail fast before script **3** / **4** if env ``tag`` and on-disk fixtures disagree.

    Raises ``FileNotFoundError`` with the missing paths listed. Does not run VB.
    """
    paths = entry12_signoff_artifact_paths(tag)
    tag_s = str(paths["_tag"])
    need: list[Path] = [paths["rdp_mat"], paths["pdp_mat"]]
    if require_k:
        need.append(paths["rand_k"])
    if require_rand_buf:
        need.append(paths["rand_buf"])
    missing = [p for p in need if not p.is_file()]
    if missing:
        names = "\n  ".join(str(p) for p in missing)
        raise FileNotFoundError(
            f"Entry 12 sign-off chain incomplete for tag {tag_s!r}.\n"
            f"Missing:\n  {names}\n"
            "Run 1a → 1b on this tag before script 3/4. "
            "Set RGMS_ENTRY12_CAPTURE_RUN_TAG consistently on 1a, 3, and 4."
        )
    if require_manifest:
        entry12_assert_manifest_coherent(
            tag_s, require_script3_pkls=require_script3_pkls
        )
    return paths


def entry12_log_signoff_chain(tag: str | None = None, *, stream: Any = None) -> dict[str, Path]:
    """Emit resolved sign-off paths to ``stderr`` (script **3** / **4** audit trail)."""
    import sys

    out = stream if stream is not None else sys.stderr
    paths = entry12_signoff_artifact_paths(tag)
    tag_s = str(paths["_tag"])
    print(f"[entry12 signoff] tag={tag_s!r}", file=out, flush=True)
    for key in ("rdp_mat", "rdp_pkl", "pdp_mat", "pdp_pkl", "rand_k", "rand_buf", "manifest"):
        p = paths[key]
        print(f"[entry12 signoff] {key}: {p} ({'ok' if p.is_file() else 'MISSING'})", file=out, flush=True)
    return paths


def entry12_load_k_from_mat(tag: str | None = None) -> int:
    """Load preflight ``K`` scalar from ``entry12_vb_rand_K[_<tag>].mat`` (script **1a**)."""
    from scipy.io import loadmat

    k_path = entry12_signoff_artifact_paths(tag)["rand_k"]
    if not k_path.is_file():
        raise FileNotFoundError(f"missing K mat: {k_path}")
    raw = loadmat(str(k_path))
    if "K" not in raw:
        raise KeyError(f"expected K in {k_path}")
    return int(np.asarray(raw["K"], dtype=np.float64).reshape(-1)[0])


def entry12_load_vb_rand_buf_for_tag(tag: str | None = None) -> np.ndarray:
    """Load MATLAB ``vb_rand_buf`` for replay (script **1b** preamble-rewind lane)."""
    from scipy.io import loadmat

    buf_path = entry12_signoff_artifact_paths(tag)["rand_buf"]
    if not buf_path.is_file():
        raise FileNotFoundError(f"missing vb_rand_buf: {buf_path}")
    raw = loadmat(str(buf_path))
    if "vb_rand_buf" not in raw:
        keys = sorted(k for k in raw if not k.startswith("__"))
        raise KeyError(f"expected vb_rand_buf in {buf_path}, got keys={keys}")
    return np.asarray(raw["vb_rand_buf"], dtype=np.float64).ravel(order="F")


def entry12_assert_buf_k_coherent(tag: str | None = None) -> None:
    """``vb_rand_buf`` length must match ``K`` in the paired preflight mat (same tag)."""
    paths = entry12_signoff_artifact_paths(tag)
    if not paths["rand_k"].is_file() or not paths["rand_buf"].is_file():
        return
    k_pref = entry12_load_k_from_mat(tag)
    k_buf = int(entry12_load_vb_rand_buf_for_tag(tag).size)
    if k_pref != k_buf:
        raise ValueError(
            f"Entry 12 tag {paths['_tag']!r}: K preflight ({k_pref}) != vb_rand_buf length ({k_buf}). "
            "Re-run 1a → 1b together; do not mix tags or stale buffers."
        )
    from scipy.io import loadmat

    raw = loadmat(str(paths["rand_buf"]))
    if "K" in raw:
        k_meta = int(np.asarray(raw["K"], dtype=np.float64).reshape(-1)[0])
        if k_meta != k_pref:
            raise ValueError(
                f"Entry 12 tag {paths['_tag']!r}: rand_buf mat K metadata ({k_meta}) "
                f"!= preflight K ({k_pref}). Refresh 1b after 1a."
            )


def count_vb_rand_draws_on_rdp(rdp: dict[str, Any]) -> int:
    """
    Script **1a**: count scalar ``numpy.random.rand()`` draws on **this tag's** ``RDP``.

    Same flags as script **3** except ``reuse_matlab_draws=False`` (native count, not replay).
    """
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    ctr = [0]
    real_rand = np.random.rand

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("count_vb_rand_draws: only scalar np.random.rand() supported")
        ctr[0] += 1
        return float(real_rand())

    from unittest.mock import patch

    flags = entry12_vb_oracle_flags(reuse_matlab_draws=False)
    with patch("numpy.random.rand", side_effect=shim):
        spm_MDP_VB_XXX(copy.deepcopy(rdp), {}, **flags)
    return int(ctr[0])


def entry12_write_preflight_k(tag: str | None = None) -> tuple[int, Path]:
    """Run script **1a** for ``tag``: count draws, write ``entry12_vb_rand_K[_<tag>].mat``."""
    from scipy.io import savemat

    tag_use = (tag or entry12_resolve_run_tag()).strip()
    rdp = load_entry12_rdp_for_tag(tag_use)
    k = count_vb_rand_draws_on_rdp(rdp)
    out = entry12_signoff_artifact_paths(tag_use)["rand_k"]
    out.parent.mkdir(parents=True, exist_ok=True)
    savemat(str(out), {"K": np.array([[float(k)]], dtype=np.float64)})
    return k, out


def load_entry12_rdp_for_tag(tag: str) -> dict[str, Any]:
    """Load ``RDP`` for VB from the call-specific ``.mat`` (checkX-only lane)."""
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import load_entry12_rdp_mat_nested_for_tag

    mat_p = entry12_atari_call_rdp_mat_path(tag)
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing RDP mat for tag {tag!r}: {mat_p}")
    nested = load_entry12_rdp_mat_nested_for_tag(tag, mat_p)
    return entry12_rdp_for_vb_from_mat_nested(nested)
