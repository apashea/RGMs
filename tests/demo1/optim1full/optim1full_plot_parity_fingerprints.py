"""OPTIM1FULL plot-parity fingerprint sidecars (dump-once staleness guards).

Sidecars sit next to spine artifacts:
  ``…_input.pkl.meta.json``
  ``…_oracle.mat.meta.json``

Reuse is allowed only when the sidecar exists and matches the current MATLAB-owned
fence PDP (size + mtime) and, for pkls, the active VB module file stamps.
Missing sidecar ⇒ treat as invalid (one regen mints it).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.demo1.optim1full.optim1full_paths import optim1full_repo_root

SCHEMA_SPINE_PKL = "optim1full_spine_pkl_v1"
SCHEMA_ORACLE = "optim1full_oracle_v1"

_FIDELITY_VB_REL = Path("python_src/toolbox/DEM/spm_MDP_VB_XXX.py")
_OPTIM_VB_REL = Path("python_src/optimized/toolbox/DEM/spm_MDP_VB_XXX_optim.py")
_OPTIM_INDUCTION_REL = Path("python_src/optimized/toolbox/DEM/vb_induction_optim.py")


def spine_pkl_meta_path(pkl_path: Path) -> Path:
    return Path(pkl_path).with_name(Path(pkl_path).name + ".meta.json")


def oracle_mat_meta_path(oracle_path: Path) -> Path:
    return Path(oracle_path).with_name(Path(oracle_path).name + ".meta.json")


def file_stamp(path: Path, *, repo: Path | None = None) -> dict[str, Any]:
    p = Path(path)
    st = p.stat()
    out: dict[str, Any] = {
        "name": p.name,
        "nbytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }
    if repo is not None:
        try:
            out["path_rel"] = str(p.resolve().relative_to(Path(repo).resolve())).replace("\\", "/")
        except ValueError:
            out["path_rel"] = str(p)
    return out


def _stamps_equal(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return int(a.get("nbytes", -1)) == int(b.get("nbytes", -2)) and int(
        a.get("mtime_ns", -1)
    ) == int(b.get("mtime_ns", -2))


def vb_module_stamps(*, vb_dev_optim: bool, repo: Path | None = None) -> list[dict[str, Any]]:
    root = Path(repo) if repo is not None else optim1full_repo_root()
    if vb_dev_optim:
        paths = [root / _OPTIM_VB_REL, root / _OPTIM_INDUCTION_REL]
    else:
        paths = [root / _FIDELITY_VB_REL]
    return [file_stamp(p, repo=root) for p in paths if p.is_file()]


def write_spine_pkl_meta(
    pkl_path: Path,
    *,
    site_id: str,
    boundary: str,
    matlab_pdp_mat: Path,
    ledger_protocol: Any,
    vb_dev_optim: bool,
    repo: Path | None = None,
) -> Path:
    root = Path(repo) if repo is not None else optim1full_repo_root()
    meta = {
        "schema": SCHEMA_SPINE_PKL,
        "site_id": str(site_id).strip(),
        "boundary": str(boundary).strip(),
        "matlab_pdp": file_stamp(matlab_pdp_mat, repo=root),
        "ledger_protocol": ledger_protocol,
        "vb_dev_optim": bool(vb_dev_optim),
        "vb_modules": vb_module_stamps(vb_dev_optim=bool(vb_dev_optim), repo=root),
    }
    out = spine_pkl_meta_path(pkl_path)
    out.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_oracle_mat_meta(
    oracle_path: Path,
    *,
    site_id: str,
    matlab_pdp_mat: Path,
    oracle_source: str,
    repo: Path | None = None,
) -> Path:
    root = Path(repo) if repo is not None else optim1full_repo_root()
    meta = {
        "schema": SCHEMA_ORACLE,
        "site_id": str(site_id).strip(),
        "matlab_pdp": file_stamp(matlab_pdp_mat, repo=root),
        "oracle_source": str(oracle_source),
    }
    out = oracle_mat_meta_path(oracle_path)
    out.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def load_meta_json(path: Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def spine_pkl_meta_ok(
    pkl_path: Path,
    matlab_pdp_mat: Path,
    *,
    vb_dev_optim: bool,
    repo: Path | None = None,
) -> bool:
    root = Path(repo) if repo is not None else optim1full_repo_root()
    if not Path(pkl_path).is_file() or not Path(matlab_pdp_mat).is_file():
        return False
    meta = load_meta_json(spine_pkl_meta_path(pkl_path))
    if meta is None or meta.get("schema") != SCHEMA_SPINE_PKL:
        return False
    if bool(meta.get("vb_dev_optim")) != bool(vb_dev_optim):
        return False
    if not _stamps_equal(meta.get("matlab_pdp"), file_stamp(matlab_pdp_mat, repo=root)):
        return False
    recorded = meta.get("vb_modules")
    current = vb_module_stamps(vb_dev_optim=bool(vb_dev_optim), repo=root)
    if not isinstance(recorded, list) or len(recorded) != len(current):
        return False
    for rec, cur in zip(recorded, current):
        if not isinstance(rec, dict) or not _stamps_equal(rec, cur):
            return False
    return True


def oracle_mat_meta_ok(
    oracle_path: Path,
    matlab_pdp_mat: Path,
    *,
    repo: Path | None = None,
) -> bool:
    root = Path(repo) if repo is not None else optim1full_repo_root()
    if not Path(oracle_path).is_file() or not Path(matlab_pdp_mat).is_file():
        return False
    meta = load_meta_json(oracle_mat_meta_path(oracle_path))
    if meta is None or meta.get("schema") != SCHEMA_ORACLE:
        return False
    return _stamps_equal(meta.get("matlab_pdp"), file_stamp(matlab_pdp_mat, repo=root))
