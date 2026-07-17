#!/usr/bin/env python3
"""DIAGNOSTIC (temp) — OPTIM1FULL call4: Python vs MATLAB ``spm_RDP_MI``.

Confirmation-only comparison requested for the call4 input-parity divergence
(``PDP.F max abs diff=8.035638616871331``). This is NOT a fix and touches no
production code. It:

  1. Loads the frozen ``DEMAtariIII_optim1full_MDP_post_nr.mat`` authority.
  2. Runs Engine ``spm_RDP_sort`` on it (same helper as call3/call4 assembly),
     leaving ``rgms_mdp_sorted`` in the Engine workspace and returning the
     pulled Python sorted MDP.
  3. Runs MATLAB ``spm_RDP_MI(rgms_mdp_sorted)`` (authority output).
  4. Runs Python ``spm_RDP_MI`` on the pulled sorted MDP (call4 path).
  5. Compares field-by-field (a / b / sA / sB / sC / id / ss).
  6. Isolates ``spm_dir_reduce`` behaviour: compares the reduction matrix R and
     the information-distance matrix D (MATLAB vs Python on the SAME C blocks),
     including min ``|D - sqrt(2)|`` and threshold-mask disagreement count.

Report: ``matlab_custom/optim1full_call4_rdp_mi_diag_output.txt``.
"""
from __future__ import annotations

import copy
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "optim1full_call4_rdp_mi_diag_output.txt"


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


def _max_abs_a_b_diff(py_mdp: list[dict], mat_mdp: list[dict]) -> tuple[float, str]:
    """Max abs diff over every ``a``/``b`` tensor (independent of assert helper)."""
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _to_tensor

    worst = 0.0
    where = "none"
    nlev = min(len(py_mdp), len(mat_mdp))
    for n in range(nlev):
        p = py_mdp[n]
        m = mat_mdp[n]
        for field in ("a", "b"):
            npy = min(len(p[field]), len(m[field]))
            for g in range(npy):
                pa = np.asarray(_to_tensor(p[field][g]), dtype=np.float64)
                ma = np.asarray(_to_tensor(m[field][g]), dtype=np.float64)
                if pa.shape != ma.shape:
                    return float("inf"), f"lev={n+1} {field}[{g+1}] shape py={pa.shape} mat={ma.shape}"
                d = float(np.max(np.abs(pa - ma))) if pa.size else 0.0
                if d > worst:
                    worst = d
                    where = f"lev={n+1} {field}[{g+1}] shape={pa.shape}"
    return worst, where


def _shape_summary(py_mdp: list[dict], mat_mdp: list[dict]) -> None:
    print("--- per-level shape / count summary (py vs mat) ---")
    for n in range(max(len(py_mdp), len(mat_mdp))):
        pl = py_mdp[n] if n < len(py_mdp) else None
        ml = mat_mdp[n] if n < len(mat_mdp) else None
        if pl is None or ml is None:
            print(f"  lev={n+1}: MISSING py={pl is not None} mat={ml is not None}")
            continue
        print(
            f"  lev={n+1}: na py={len(pl['a'])} mat={len(ml['a'])} | "
            f"nb py={len(pl['b'])} mat={len(ml['b'])} | "
            f"sB py={list(pl['sB'])} mat={list(ml['sB'])}"
        )


def _reconstruct_matlab_C_R_D(eng: Any) -> bool:
    """Replay ``spm_RDP_MI.m`` lines 29-88 on ``rgms_mdp_sorted`` to expose C/R/D.

    Uses only existing MATLAB functions (spm_dir_norm / spm_information_distance /
    spm_dir_reduce); does NOT edit MATLAB source. Returns True on success.
    """
    script = (
        "rgms_mi_ok = false; "
        "try, "
        "  MDPmi = rgms_mdp_sorted; o = 1; n = numel(MDPmi); "
        "  try, A = MDPmi{n}.a; catch, A = MDPmi{n}.A; end; "
        "  try, B = MDPmi{n}.b{1}; catch, B = MDPmi{n}.B{1}; end; "
        "  Ns = size(B,2); Nu = size(B,3); "
        "  for u = 1:Nu, for s = 1:Ns, "
        "    if ~any(B(:,s,u)), [jj,ii] = max(max(squeeze(B(:,s,:)),[],2)); B(ii,s,u) = jj; end; "
        "  end; end; "
        "  A = spm_dir_norm(A); B = spm_dir_norm(B); C = {}; "
        "  for s = 2:max(MDPmi{1}.sB), "
        "    pD = MDPmi{n-1}.id.D{MDPmi{n-1}.sB == s}; "
        "    pE = MDPmi{n-1}.id.E{MDPmi{n-1}.sB == s}; "
        "    ps = find(ismember([MDPmi{n}.id.A{:}], find(MDPmi{n}.sB == 1,1,'first'))); "
        "    pD = intersect(ps,pD); pE = intersect(ps,pE); "
        "    if numel(pD), for p = 0:o, for u = 1:Nu, "
        "      C{end+1,1} = A{pD}*(B(:,:,u)^p); C{end+1,1} = A{pE}*(B(:,:,u)^p); "
        "    end; end; end; "
        "  end; "
        "  rgms_mi_C = C; rgms_mi_Cn = numel(C); "
        "  rgms_mi_D = spm_information_distance(C); "
        "  rgms_mi_R = full(spm_dir_reduce(C)); "
        "  rgms_mi_ok = true; "
        "catch rgms_mi_err, rgms_mi_ok = false; rgms_mi_msg = getReport(rgms_mi_err); end"
    )
    eng.eval(script, nargout=0)
    ok = bool(int(np.asarray(eng.eval("double(rgms_mi_ok)"), dtype=np.int64).reshape(-1)[0]))
    if not ok:
        try:
            msg = eng.eval("rgms_mi_msg")
        except Exception:
            msg = "(no message)"
        print(f"[MATLAB C/R/D reconstruction FAILED] {msg}")
    return ok


def _pull_matlab_C_cells(eng: Any) -> list[list[np.ndarray]]:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _mat_full_numeric, _mat_int

    cn = _mat_int(eng, "numel(rgms_mi_C)")
    out: list[list[np.ndarray]] = []
    for k in range(1, cn + 1):
        blk = np.asarray(_mat_full_numeric(eng, f"rgms_mi_C{{{k}}}"), dtype=np.float64)
        if blk.ndim == 1:
            blk = blk.reshape((-1, 1), order="F")
        out.append([blk])
    return out


def _run() -> int:
    import matlab.engine

    from python_src.toolbox.DEM.spm_RDP_MI import _build_mi_causal_snap, spm_RDP_MI
    from python_src.toolbox.DEM.spm_information_distance import spm_information_distance
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_matlab_sort import run_spm_RDP_sort_matlab
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_mdp_full_equal,
        _pull_mdp_from_matlab,
    )

    mat_path = optim1full_mdp_post_nr_mat()
    print(f"[call4 RDP_MI diag] MDP_post_nr authority = {mat_path}")
    if not mat_path.is_file():
        print("[call4 RDP_MI diag] MISSING authority mat")
        return 2

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)

        # (1)+(2) Engine spm_RDP_sort on frozen MDP_post_nr -> sorted MDP (py + workspace).
        sorted_mdp, j = run_spm_RDP_sort_matlab(eng, [], mat_path=mat_path)
        print(f"[call4 RDP_MI diag] spm_RDP_sort done; levels={len(sorted_mdp)} j(len)={j.size}")

        # (3) MATLAB spm_RDP_MI on the SAME engine sorted MDP (authority output).
        eng.eval("rgms_mdp_mi_out = spm_RDP_MI(rgms_mdp_sorted);", nargout=0)
        mdp_mat = _pull_mdp_from_matlab(eng, "rgms_mdp_mi_out")

        # (4) Python spm_RDP_MI on the pulled sorted MDP (call4 path).
        mdp_py = spm_RDP_MI(copy.deepcopy(sorted_mdp))

        # (5) field-by-field comparison
        print("\n==================== RDP OUTPUT COMPARISON ====================")
        _shape_summary(mdp_py, mdp_mat)
        worst, where = _max_abs_a_b_diff(mdp_py, mdp_mat)
        print(f"[a/b tensor scan] max abs diff = {worst!r} at {where}")
        equal = False
        first_diff = None
        try:
            _assert_mdp_full_equal(mdp_py, mdp_mat, 4)
            equal = True
            print("[full compare] EQUAL — Python spm_RDP_MI output == MATLAB spm_RDP_MI output")
        except AssertionError as exc:
            first_diff = str(exc)
            print(f"[full compare] FIRST MATERIAL DIFF: {first_diff}")

        # (6) spm_dir_reduce isolation: R + D (threshold) diagnostics.
        print("\n==================== spm_dir_reduce ISOLATION ====================")
        snap = _build_mi_causal_snap(copy.deepcopy(sorted_mdp), 1)
        R_py = np.asarray(snap.R, dtype=np.float64)
        print(f"[python] C_n={snap.C_n}  R.shape={R_py.shape}  R.nnz={int(np.count_nonzero(R_py))}")

        if _reconstruct_matlab_C_R_D(eng):
            R_mat = np.asarray(eng.eval("rgms_mi_R"), dtype=np.float64)
            if R_mat.ndim == 1:
                R_mat = R_mat.reshape((R_py.shape[0] if R_py.size else -1, -1), order="F")
            c_n_mat = int(np.asarray(eng.eval("double(rgms_mi_Cn)"), dtype=np.int64).reshape(-1)[0])
            print(f"[matlab] C_n={c_n_mat}  R.shape={R_mat.shape}  R.nnz={int(np.count_nonzero(R_mat))}")

            if R_py.shape == R_mat.shape:
                r_diff = float(np.max(np.abs(R_py - R_mat)))
                print(f"[R compare] shapes match; max abs diff = {r_diff!r}; "
                      f"identical={bool(np.array_equal(R_py, R_mat))}")
            else:
                print(f"[R compare] SHAPE MISMATCH py={R_py.shape} mat={R_mat.shape} "
                      f"-> partition (column count) differs => threshold flip candidate")

            # D on the SAME MATLAB-computed C blocks (isolates distance-value drift).
            D_mat = np.asarray(eng.eval("rgms_mi_D"), dtype=np.float64)
            C_cells = _pull_matlab_C_cells(eng)
            D_py, _corr = spm_information_distance(C_cells)
            D_py = np.asarray(D_py, dtype=np.float64)
            sqrt2 = float(np.sqrt(2.0))
            print(f"\n[D matrix] shape py={D_py.shape} mat={D_mat.shape}  sqrt(2)={sqrt2!r}")
            if D_py.shape == D_mat.shape and D_py.size:
                d_diff = float(np.max(np.abs(D_py - D_mat)))
                print(f"[D compare] max abs diff (same C input) = {d_diff!r}")
                for lbl, D in (("matlab", D_mat), ("python", D_py)):
                    dist = np.abs(D - sqrt2)
                    off = ~np.eye(D.shape[0], dtype=bool) if D.shape[0] == D.shape[1] else np.ones_like(D, bool)
                    near = int(np.count_nonzero((dist < 1e-6) & off))
                    near_tol = int(np.count_nonzero((dist < 1e-3) & off))
                    dmin = float(np.min(dist[off])) if np.any(off) else float("nan")
                    print(f"  [{lbl}] min|D-sqrt2|={dmin!r}  #(|D-sqrt2|<1e-6)={near}  #(<1e-3)={near_tol}")
                mask_py = D_py < sqrt2
                mask_mat = D_mat < sqrt2
                disagree = int(np.count_nonzero(mask_py != mask_mat))
                print(f"[threshold mask] #(D<sqrt2) py={int(mask_py.sum())} mat={int(mask_mat.sum())} "
                      f"disagreeing entries={disagree}")
            else:
                print("[D compare] shape mismatch or empty; skipping value compare")
        else:
            print("[spm_dir_reduce isolation] MATLAB reconstruction unavailable; "
                  "R/D compare skipped (Python R printed above)")

        print("\n==================== VERDICT ====================")
        print(f"Python spm_RDP_MI output == MATLAB spm_RDP_MI output : {'YES' if equal else 'NO'}")
        if not equal:
            print(f"First material differing field: {first_diff}")
            print(f"Max abs diff over a/b tensors: {worst!r} at {where}")
        return 0 if equal else 3
    finally:
        eng.quit()


def main() -> int:
    report = _report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8") as rf:
        tee = _TeeIO(sys.stdout, rf)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = tee  # type: ignore[assignment]
        sys.stderr = tee  # type: ignore[assignment]
        try:
            return _run()
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = old_out, old_err


if __name__ == "__main__":
    raise SystemExit(main())
