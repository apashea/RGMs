#!/usr/bin/env python3
"""OPTIM1FULL tier **2** — ``spm_RDP_sort`` split diagnostic (A → B → C).

Read-only: locates first divergence on authority ``DEMAtariIII_optim1full_MDP_post_nr.mat``.
Uses **hook-only** MATLAB ``eig`` inject (``matlab_eig_callable``) — **not** Product B sign-off.
Product B tier **2** uses Engine ``spm_RDP_sort`` via ``optim1full_matlab_sort.py``.

**Report:** ``matlab_custom/optim1full_diagnose_call3_sort_split_output.txt``
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
    return _REPO / "matlab_custom" / "optim1full_diagnose_call3_sort_split_output.txt"


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


def _max_abs_diff(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    pa = np.asarray(a, dtype=np.float64).ravel(order="F")
    pb = np.asarray(b, dtype=np.float64).ravel(order="F")
    if pa.size != pb.size:
        return float("nan"), -1
    d = np.abs(pa - pb)
    if d.size == 0:
        return 0.0, -1
    i = int(np.argmax(d))
    return float(d[i]), i


def _distinct_levels(x: np.ndarray) -> int:
    return len({float(v) for v in np.asarray(x, dtype=np.float64).ravel(order="F")})


def _execute() -> int:
    import matlab.engine
    from matlab import double as ml_double
    from scipy.io import loadmat

    from matlab_compat import principal_eig_column_index
    from python_src.spm_dir_norm import spm_dir_norm
    from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort, spm_RDP_sort_flow_B
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat
    from tests.demo1.optim1full.optim1full_replay import matlab_eig_callable
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
    from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig

    mat_path = optim1full_mdp_post_nr_mat()
    if not mat_path.is_file():
        print(f"[OPTIM1FULL sort split] missing mat: {mat_path}", file=sys.stderr)
        return 2

    print(f"[OPTIM1FULL sort split] MAT={mat_path}", file=sys.stderr)
    mdp = load_mdp_from_mat(mat_path, "MDP_post_nr")
    nm = len(mdp)
    print(f"[OPTIM1FULL sort split] Nm={nm}", file=sys.stderr)

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)

        # --- Stage A: flow matrix B ---
        eng.eval("B_mat = spm_dir_norm(sum(MDP_post_nr{end}.b{1},3) > 0);", nargout=0)
        tmp = _REPO / "matlab_custom" / "_optim1full_sort_split_B.mat"
        tmp_posix = str(tmp.resolve()).replace("\\", "/")
        eng.eval(f"save('{tmp_posix}','B_mat');", nargout=0)
        b_mat = np.asarray(mat_nested_to_py(loadmat(str(tmp))["B_mat"]), dtype=np.float64)
        b_py = spm_RDP_sort_flow_B(copy.deepcopy(mdp))
        b_diff, b_idx = _max_abs_diff(b_py, b_mat)
        b_ok = bool(np.allclose(b_py, b_mat, rtol=0.0, atol=1e-12))
        print(f"[A] flow B: shape py={b_py.shape} mat={b_mat.shape} max_abs_diff={b_diff} PASS={b_ok}")
        if not b_ok and b_idx >= 0:
            flat = np.asarray(b_py, dtype=np.float64).ravel(order="F")
            flat_m = np.asarray(b_mat, dtype=np.float64).ravel(order="F")
            print(f"    worst idx {b_idx}: py={flat[b_idx]} mat={flat_m[b_idx]}")

        # --- Stage B: MATLAB eig inject lane (tier 2 policy) ---
        matlab_eig = _make_matlab_spm_RDP_sort_eig(eng)
        w_py, v_py = matlab_eig(b_py)
        eng.workspace["B_py_ws"] = ml_double(np.asarray(b_py, dtype=np.float64).tolist())
        eng.eval("[e_mat,v_mat]=eig(B_py_ws,'nobalance');", nargout=0)
        eng.eval("w_mat_diag = diag(v_mat); [~,jj_mat]=max(real(w_mat_diag));", nargout=0)
        eng.eval("p_mat = spm_dir_norm(abs(e_mat(:,jj_mat)))';", nargout=0)
        eng.eval("[MDP_sort_mat,j_sort_mat]=spm_RDP_sort(MDP_post_nr);", nargout=0)
        tmp2 = _REPO / "matlab_custom" / "_optim1full_sort_split_stageB.mat"
        tmp2_posix = str(tmp2.resolve()).replace("\\", "/")
        eng.eval(
            f"save('{tmp2_posix}','e_mat','v_mat','w_mat_diag','jj_mat','p_mat','j_sort_mat');",
            nargout=0,
        )
        raw_b = loadmat(str(tmp2))
        p_mat = np.asarray(raw_b["p_mat"], dtype=np.float64).ravel(order="F")
        j_sort_mat = np.asarray(raw_b["j_sort_mat"], dtype=np.int64).ravel(order="F")
        jj_mat = int(np.asarray(raw_b["jj_mat"], dtype=np.int64).reshape(-1)[0]) - 1

        j_eig_py = principal_eig_column_index(w_py)
        vec_py = np.abs(v_py[:, j_eig_py])
        p_py = np.asarray(
            spm_dir_norm(np.reshape(vec_py, (-1, 1), order="F")), dtype=np.float64
        ).ravel(order="F")

        jj_ok = j_eig_py == jj_mat
        w_mat_diag = np.asarray(raw_b.get("w_mat_diag", raw_b.get("w_mat")), dtype=np.complex128).ravel(
            order="F"
        )
        w_diff = (
            float(np.max(np.abs(w_py - w_mat_diag)))
            if w_mat_diag.size == w_py.size
            else float("nan")
        )
        w_ok = bool(np.allclose(w_py, w_mat_diag, rtol=0.0, atol=1e-12))
        p_diff, p_idx = _max_abs_diff(p_py, p_mat)
        p_ok = bool(np.allclose(p_py, p_mat, rtol=0.0, atol=1e-12))
        print(
            f"[B1] eigenvalues w: max_abs_diff={w_diff} PASS={w_ok}"
        )
        print(
            f"[B2] principal column: py={j_eig_py} mat={jj_mat} (0-based) PASS={jj_ok}"
        )
        print(
            f"[B3] NESS p: len={p_py.size} distinct py={_distinct_levels(p_py)} "
            f"mat={_distinct_levels(p_mat)} max_abs_diff={p_diff} PASS={p_ok}"
        )

        mdp_py, j_sort_py = spm_RDP_sort(copy.deepcopy(mdp), eig=matlab_eig)
        j_sort_py = np.asarray(j_sort_py, dtype=np.int64).ravel(order="F")
        j_ok = bool(np.array_equal(j_sort_py, j_sort_mat))
        print(
            f"[B4] full spm_RDP_sort j: len py={j_sort_py.size} mat={j_sort_mat.size} "
            f"PASS={j_ok}"
        )
        if not j_ok:
            bad = np.where(j_sort_py != j_sort_mat)[0][:8]
            for i in bad:
                print(f"    j[{int(i)}]: py={int(j_sort_py[i])} mat={int(j_sort_mat[i])}")

        # --- Stage C: compress output (only if B ok; report either way) ---
        eng.eval(
            f"save('{tmp2_posix}','MDP_sort_mat','-append');",
            nargout=0,
        )
        raw_b = loadmat(str(tmp2))
        mdp_sort_mat = mat_nested_to_py(raw_b["MDP_sort_mat"])
        from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

        c_ok = True
        c_err = ""
        try:
            _assert_mdp_full_equal(mdp_py, mdp_sort_mat, 1)
        except (AssertionError, TypeError, ValueError) as exc:
            c_ok = False
            c_err = str(exc)
        print(f"[C] compressed MDP after sort: PASS={c_ok}")
        if not c_ok:
            print(f"    first assert: {c_err}")

        # Summary gate for tier-2 interpretation
        print("--- summary ---")
        if not b_ok:
            print("FIRST_RED: stage A (flow B build from MDP_post_nr pull)")
        elif not w_ok or not p_ok or not jj_ok:
            print("FIRST_RED: stage B (eig w / NESS p / principal column despite MATLAB eig inject)")
        elif not j_ok:
            print("FIRST_RED: stage B4 (prune / sort j loop; eig and p matched)")
        elif not c_ok:
            print("FIRST_RED: stage C (spm_RDP_compress / post-sort MDP)")
        else:
            print("ALL_STAGES_PASS on MDP_post_nr sort split (tier 2 divergence is downstream of sort)")

        return 0 if (b_ok and w_ok and p_ok and jj_ok and j_ok and c_ok) else 1
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
            return _execute()
        except Exception:
            traceback.print_exc()
            return 1
        finally:
            sys.stdout, sys.stderr = old_out, old_err


if __name__ == "__main__":
    raise SystemExit(main())
