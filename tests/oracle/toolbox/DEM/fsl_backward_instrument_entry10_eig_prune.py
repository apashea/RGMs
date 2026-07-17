#!/usr/bin/env python3
"""FSL Entry 10 — instrument eigen + NESS prune (read-only diagnostic).

Loads ``DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl``, builds flow ``B``, compares
native eigen backends and principal-column rules vs MATLAB Engine ``eig(B,'nobalance')``.

Report (full summary, always written): ``matlab_custom/fsl_backward_instrument_entry10_eig_prune_output.txt``

Run without piping through ``Select-Object -Last N`` — that truncates the terminal
capture; the report file holds the complete summary. Progress lines go to stderr.

See ``Atari_example.md`` § FSL backward validation (Entry 11 → 1).
"""
from __future__ import annotations

import copy
import os
import pickle
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort, spm_RDP_sort_flow_B


def _progress(msg: str) -> None:
    print(f"[FSL Entry10 instrument] {msg}", file=sys.stderr, flush=True)


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_instrument_entry10_eig_prune_output.txt"


def _distinct_levels(p: np.ndarray) -> int:
    return int(np.unique(np.asarray(p, dtype=np.float64).ravel()).size)


def _p_from_wv(w: np.ndarray, V: np.ndarray, j_eig: int) -> np.ndarray:
    vec = np.abs(V[:, int(j_eig)])
    return np.asarray(
        spm_dir_norm(np.reshape(vec, (-1, 1), order="F")), dtype=np.float64
    ).ravel(order="F")


def _first_removal_index_diff(
    B: np.ndarray, p_a: np.ndarray, p_b: np.ndarray, label_a: str, label_b: str
) -> str:
    """First ascending-``p`` removal step where two masks diverge."""
    ns = int(B.shape[0])
    idx = np.arange(ns, dtype=np.int64)
    ma = np.ones(ns, dtype=bool)
    mb = np.ones(ns, dtype=bool)
    for i in np.lexsort((idx, p_a)):
        da = ma.copy()
        da[int(i)] = False
        if np.any(da) and np.all(np.any(B[np.ix_(da, da)], axis=0)):
            ma = da
        db = mb.copy()
        db[int(i)] = False
        if np.any(db) and np.all(np.any(B[np.ix_(db, db)], axis=0)):
            mb = db
        if not np.array_equal(ma, mb):
            return (
                f"first_mask_divergence at removal_order={int(i)} "
                f"({label_a} n_keep={int(np.sum(ma))} vs {label_b} n_keep={int(np.sum(mb))})"
            )
    if int(np.sum(ma)) != int(np.sum(mb)):
        return f"masks equal steps but final n_keep {label_a}={int(np.sum(ma))} {label_b}={int(np.sum(mb))}"
    return f"prune_masks_identical n_keep={int(np.sum(ma))}"


def _prune_mask(B: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, int]:
    """Replay ``spm_RDP_sort`` NESS prune; return mask and number of removals."""
    ns = int(B.shape[0])
    idx = np.arange(ns, dtype=np.int64)
    j_mask = np.ones(ns, dtype=bool)
    removals = 0
    k = np.lexsort((idx, p))
    for i in k:
        d = j_mask.copy()
        d[int(i)] = False
        if not np.any(d):
            continue
        b_dd = B[np.ix_(d, d)]
        if np.all(np.any(b_dd, axis=0)):
            j_mask = d
            removals += 1
    return j_mask, removals


def _full_sort_width(
    mdp_pre10: list[dict[str, Any]],
    eig_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None,
) -> int:
    mdp_out, j = spm_RDP_sort(copy.deepcopy(mdp_pre10), eig=eig_fn)
    a0 = mdp_out[-1]["a"][0]
    arr = np.asarray(a0[0] if isinstance(a0, list) else a0, dtype=np.float64)
    return int(arr.shape[-1]), int(np.asarray(j).size)


def _run_native_lane(
    label: str,
    B: np.ndarray,
    mdp_pre10: list[dict[str, Any]],
    eig_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None,
    principal_env: str | None,
) -> list[str]:
    _progress(f"start lane {label}")
    lines: list[str] = []
    old = os.environ.get("RGMS_SPM_RDP_SORT_PRINCIPAL")
    if principal_env is not None:
        os.environ["RGMS_SPM_RDP_SORT_PRINCIPAL"] = principal_env
    try:
        from matlab_compat import principal_eig_column_index

        w, V = (eig_fn(B) if eig_fn is not None else np.linalg.eig(B))
        j_argmax = int(np.argmax(np.real(w)))
        j_pick = principal_eig_column_index(w)
        p = _p_from_wv(w, V, j_pick)
        mask, n_rem = _prune_mask(B, p)
        n_keep = int(np.sum(mask))
        w_sort, j_len = _full_sort_width(mdp_pre10, eig_fn)
        lines.append(f"[{label}] principal_env={principal_env!r}")
        lines.append(
            f"  j_argmax={j_argmax} j_principal={j_pick} max_real_ev={float(np.max(np.real(w))):.16g}"
        )
        lines.append(f"  distinct_p={_distinct_levels(p)} prune_removals={n_rem} n_keep={n_keep}")
        lines.append(f"  full_spm_RDP_sort width={w_sort} j_out_len={j_len}")
    finally:
        if principal_env is not None:
            if old is None:
                os.environ.pop("RGMS_SPM_RDP_SORT_PRINCIPAL", None)
            else:
                os.environ["RGMS_SPM_RDP_SORT_PRINCIPAL"] = old
    _progress(f"done lane {label}")
    return lines


def _run_matlab_lane(B: np.ndarray, mdp_pre10: list[dict[str, Any]]) -> list[str]:
    _progress("start lane MATLAB (Engine startup + eig + full sort)")
    import matlab.engine
    from matlab import double as ml_double

    from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    lines: list[str] = []
    eng = matlab.engine.start_matlab()
    try:
        for p in (
            str(_REPO),
            str(_REPO / "matlab_src"),
            str(_REPO / "matlab_src" / "toolbox" / "DEM"),
        ):
            eng.addpath(p, nargout=0)
        eng.workspace["rgms_B"] = ml_double(B.tolist())
        eng.eval(
            "[e,v]=eig(rgms_B,'nobalance'); [~,jj]=max(real(diag(v))); "
            "p=spm_dir_norm(abs(e(:,jj)))';",
            nargout=0,
        )
        p_m = np.asarray(eng.eval("double(p(:))"), dtype=np.float64).ravel()
        jj = int(eng.eval("jj"))
        lines.append("[MATLAB eig nobalance]")
        lines.append(f"  jj={jj} distinct_p={_distinct_levels(p_m)}")
        mask, n_rem = _prune_mask(B, p_m)
        lines.append(f"  prune_removals={n_rem} n_keep={int(np.sum(mask))}")
        mat_p = _REPO / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry11.mat"
        eng.eval(f"load('{str(mat_p.resolve()).replace(chr(92), '/')}');", nargout=0)
        mat11 = _pull_mdp_from_matlab(eng, "MDP_pre_entry11")
        auth_w = int(np.asarray(mat11[-1]["a"][0]).shape[-1])
        lines.append(f"  authority_MDP_pre_entry11_width={auth_w}")
        w_chk, V_chk = np.linalg.eig(B)
        p_col0 = _p_from_wv(w_chk, V_chk, 0)
        lines.append(
            "  MATLAB p vs numpy p(column0): "
            + _first_removal_index_diff(B, p_m, p_col0, "MATLAB", "numpy_col0")
        )
        w_n, V_n = np.linalg.eig(B)
        from matlab_compat import principal_eig_column_index

        old_pr = os.environ.get("RGMS_SPM_RDP_SORT_PRINCIPAL")
        try:
            for rule in ("min_tie", "closest_unity", "argmax"):
                os.environ["RGMS_SPM_RDP_SORT_PRINCIPAL"] = rule
                j_r = principal_eig_column_index(w_n)
                p_r = _p_from_wv(w_n, V_n, j_r)
                lines.append(
                    f"  vs native principal={rule!r} (j={j_r}): "
                    + _first_removal_index_diff(B, p_m, p_r, "MATLAB", rule)
                )
        finally:
            if old_pr is None:
                os.environ.pop("RGMS_SPM_RDP_SORT_PRINCIPAL", None)
            else:
                os.environ["RGMS_SPM_RDP_SORT_PRINCIPAL"] = old_pr
        meig = _make_matlab_spm_RDP_sort_eig(eng)
        w_sort, j_len = _full_sort_width(mdp_pre10, meig)
        lines.append(f"  full_spm_RDP_sort(Engine eig) width={w_sort} j_out_len={j_len}")
    finally:
        eng.quit()
    _progress("done lane MATLAB")
    return lines


def main() -> int:
    from matlab_compat import (
        _eig_lapack_dgeev_real,
        eig_matlab_nobalance,
        geevx_available,
    )

    pre_pkl = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    )
    if not pre_pkl.is_file():
        print(f"missing {pre_pkl}", file=sys.stderr)
        return 2

    _progress("loading pre_entry10 + building B")
    mdp_pre10 = pickle.load(pre_pkl.open("rb"))["mdp"]
    B = spm_RDP_sort_flow_B(copy.deepcopy(mdp_pre10))
    lines: list[str] = [
        "FSL Entry 10 eigen/prune instrument",
        f"B shape={B.shape}",
        f"geevx_available={geevx_available()}",
        "NOTE: summary only (not per-step prune log); see stderr progress per lane.",
        "",
    ]

    lines.extend(_run_matlab_lane(B, mdp_pre10))
    lines.append("")

    lines.extend(
        _run_native_lane("numpy@col0", B, mdp_pre10, np.linalg.eig, "column0")
    )
    lines.append("")

    lines.extend(
        _run_native_lane("numpy", B, mdp_pre10, np.linalg.eig, "argmax")
    )
    lines.extend(
        _run_native_lane("numpy+min_tie", B, mdp_pre10, np.linalg.eig, "min_tie")
    )
    lines.extend(
        _run_native_lane("numpy+closest_unity", B, mdp_pre10, np.linalg.eig, "closest_unity")
    )
    lines.extend(
        _run_native_lane("eig_matlab_nobalance", B, mdp_pre10, eig_matlab_nobalance, "argmax")
    )
    lines.extend(
        _run_native_lane(
            "eig_matlab_nobalance+min_tie", B, mdp_pre10, eig_matlab_nobalance, "min_tie"
        )
    )
    lines.extend(
        _run_native_lane("lapack_dgeev(exp)", B, mdp_pre10, _eig_lapack_dgeev_real, "argmax")
    )

    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    report.write_text(text, encoding="utf-8")
    print(text, end="", flush=True)
    _progress(f"complete — full summary written ({len(lines)} lines) to {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
