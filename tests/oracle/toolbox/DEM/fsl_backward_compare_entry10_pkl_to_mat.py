#!/usr/bin/env python3
"""FSL backward — Entry 10: compare Python post-Entry-10 ``MDP`` vs MATLAB authority.

**Authority:** ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry11.mat`` variable
``MDP_pre_entry11`` (post Entry 10, pre Entry 11 — same ledger as Entry 12 Call 1).

**Python:** ``fixtures/DEMAtariIII_fsl_backward_entry10_post.pkl`` field ``mdp``.

**Report:** ``matlab_custom/fsl_backward_compare_entry10_output.txt``

**Sign-off contract:** PKL must be built with **MATLAB ``eig(B,'nobalance')`` injected**
(``validation.eig_source == "matlab_engine"`` in the post-Entry-10 pickle). That proves
Python **non-eig** Entry 10 code (``spm_dir_norm``, NESS prune, ``spm_RDP_compress``,
``spm_set_goals``, paths-to-hits ``P``) against ``MDP_pre_entry11`` authority. Native-only
``spm_RDP_sort`` is **not** FSL sign-off on this boundary — see ``Atari_example.md`` §
**Entry 10 — eigen limitation (project-critical)**.

Diagnostic native compare: set ``RGMS_FSL_BACKWARD_ENTRY10_ALLOW_NATIVE_EIG=1``.

See ``Atari_example.md`` § **FSL backward validation (Entry 11 → 1)**.
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import traceback
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_compare_entry10_output.txt"


def _default_post_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY10_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry10_post.pkl"


def _default_authority_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY10_AUTHORITY_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat"
    )


class _TeeIO:
    __slots__ = ("_streams",)

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            s = str(s)
        for st in self._streams:
            st.write(s)
        return len(s)

    def flush(self) -> None:
        for st in self._streams:
            st.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._streams[0], "isatty", lambda: False)())


def _load_py_blob(pkl_path: Path) -> dict[str, Any]:
    with pkl_path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "mdp" not in blob:
        raise KeyError(f"expected dict with mdp in {pkl_path}")
    return blob


def _assert_matlab_eig_provenance(blob: dict[str, Any], pkl_path: Path) -> None:
    """FSL Entry 10 sign-off requires MATLAB-injected sort eigenpairs (split validation)."""
    allow = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY10_ALLOW_NATIVE_EIG", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    val = blob.get("validation")
    if not isinstance(val, dict):
        if allow:
            print(
                f"[FSL backward Entry 10] WARNING: {pkl_path} has no validation block "
                "(legacy PKL); compare proceeds under RGMS_FSL_BACKWARD_ENTRY10_ALLOW_NATIVE_EIG",
                file=sys.stderr,
            )
            return
        raise ValueError(
            f"{pkl_path}: missing validation metadata — rebuild with "
            "fsl_backward_run_entry10_isolated.py (default MATLAB eig). "
            "Or set RGMS_FSL_BACKWARD_ENTRY10_ALLOW_NATIVE_EIG=1 for diagnostic native PKL."
        )
    eig_src = str(val.get("eig_source", "")).strip()
    if eig_src == "matlab_engine" or bool(val.get("matlab_eig_injected")):
        return
    if allow:
        print(
            f"[FSL backward Entry 10] WARNING: PKL eig_source={eig_src!r} — "
            "diagnostic compare only (not FSL sign-off)",
            file=sys.stderr,
        )
        return
    raise ValueError(
        f"{pkl_path}: eig_source={eig_src!r} — FSL Entry 10 sign-off requires "
        "MATLAB eig injection (default RGMS_FSL_RDP_SORT_MATLAB_EIG=1 in isolated runner). "
        "Rebuild PKL or set RGMS_FSL_BACKWARD_ENTRY10_ALLOW_NATIVE_EIG=1 for diagnostic."
    )


def _load_py_mdp(pkl_path: Path) -> list[dict[str, Any]]:
    blob = _load_py_blob(pkl_path)
    mdp = blob["mdp"]
    if not isinstance(mdp, list):
        raise TypeError(f"mdp must be list in {pkl_path}")
    return mdp


def _load_mat_mdp(mat_path: Path) -> list[dict[str, Any]]:
    import matlab.engine

    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    repo = _REPO
    eng = matlab.engine.start_matlab()
    try:
        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

        dem_path = configure_dem_matlab_engine(eng, repo)
        eng.eval(f"load('{str(mat_path.resolve()).replace(chr(92), '/')}');", nargout=0)
        return _pull_mdp_from_matlab(eng, "MDP_pre_entry11")
    finally:
        eng.quit()


def _execute(args: argparse.Namespace) -> int:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pkl_path = args.pkl.resolve()
    mat_path = args.mat.resolve()
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing PKL: {pkl_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(
            f"missing authority mat: {mat_path}\n"
            "Run dump_MDP_pre_entry11.m (or refresh pre_entry11 fixture)."
        )

    blob = _load_py_blob(pkl_path)
    _assert_matlab_eig_provenance(blob, pkl_path)
    py_mdp = blob["mdp"]
    if not isinstance(py_mdp, list):
        raise TypeError(f"mdp must be list in {pkl_path}")
    mat_mdp = _load_mat_mdp(mat_path)

    print(f"[FSL backward Entry 10] PKL post-Entry-10={pkl_path}", file=sys.stderr)
    print(f"[FSL backward Entry 10] MAT authority (MDP_pre_entry11)={mat_path}", file=sys.stderr)
    print(
        f"[FSL backward Entry 10] levels py={len(py_mdp)} mat={len(mat_mdp)}",
        file=sys.stderr,
    )

    _assert_mdp_full_equal(py_mdp, mat_mdp, k=10)
    print("OK: MDP parity (FSL backward Entry 10)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSL backward Entry 10 MDP compare")
    p.add_argument("--pkl", type=Path, default=None, help="Python post-Entry-10 PKL")
    p.add_argument("--mat", type=Path, default=None, help="MATLAB authority .mat")
    args = p.parse_args(argv)
    if args.pkl is None:
        args.pkl = _default_post_pkl()
    if args.mat is None:
        args.mat = _default_authority_mat()

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "FSL backward — Entry 10: compare Python post-Entry-10 ``MDP`` vs "
        "``MDP_pre_entry11`` authority.\n\n"
        f"**Report:** ``{report}``\n\n"
    )
    with report.open("w", encoding="utf-8") as rf:
        rf.write(header)
        tee_out = sys.stdout
        tee_err = sys.stderr
        sys.stdout = _TeeIO(tee_out, rf)
        sys.stderr = _TeeIO(tee_err, rf)
        try:
            return _execute(args)
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout = tee_out
            sys.stderr = tee_err


if __name__ == "__main__":
    raise SystemExit(main())
