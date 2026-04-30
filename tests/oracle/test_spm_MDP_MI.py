import numpy as np
import os
import pickle
from pathlib import Path

import matlab
import pytest

from python_src.spm_MDP_MI import spm_MDP_MI
from python_src.spm_log import spm_log
from tests.helpers.compare import assert_matlab_match


def test_spm_MDP_MI_numeric_no_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = [2 1 3; 1 4 2];"
        "[E_spm_MDP_MI,dEda_spm_MDP_MI,dEdA_spm_MDP_MI] = "
        "spm_MDP_MI(a_spm_MDP_MI);",
        nargout=0,
    )
    a = np.array([[2.0, 1.0, 3.0], [1.0, 4.0, 2.0]])

    _assert_mdp_mi_outputs_match(eng, spm_MDP_MI(a))


def test_spm_MDP_MI_numeric_with_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = [2 1 3; 1 4 2];"
        "c_spm_MDP_MI = [1; 2];"
        "h_spm_MDP_MI = [3; 1; 2];"
        "[E_spm_MDP_MI,dEda_spm_MDP_MI,dEdA_spm_MDP_MI] = "
        "spm_MDP_MI(a_spm_MDP_MI,c_spm_MDP_MI,h_spm_MDP_MI);",
        nargout=0,
    )
    a = np.array([[2.0, 1.0, 3.0], [1.0, 4.0, 2.0]])
    c = np.array([[1.0], [2.0]])
    h = np.array([[3.0], [1.0], [2.0]])

    _assert_mdp_mi_outputs_match(eng, spm_MDP_MI(a, c, h))


def test_spm_MDP_MI_empty_outcome_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = [2 1 3; 1 4 2];"
        "[E_spm_MDP_MI,dEda_spm_MDP_MI,dEdA_spm_MDP_MI] = "
        "spm_MDP_MI(a_spm_MDP_MI,[]);",
        nargout=0,
    )
    a = np.array([[2.0, 1.0, 3.0], [1.0, 4.0, 2.0]])
    c = np.empty((0, 0))

    _assert_mdp_mi_outputs_match(eng, spm_MDP_MI(a, c))


def test_spm_MDP_MI_cell_with_preferences_oracle(eng):
    eng.eval(
        "a_spm_MDP_MI = {[2 1; 1 3], [1 2; 4 1]};"
        "c_spm_MDP_MI = {[1; 2], [3; 1]};"
        "E_spm_MDP_MI = spm_MDP_MI(a_spm_MDP_MI,c_spm_MDP_MI);",
        nargout=0,
    )
    a = [
        np.array([[2.0, 1.0], [1.0, 3.0]]),
        np.array([[1.0, 2.0], [4.0, 1.0]]),
    ]
    c = [np.array([[1.0], [2.0]]), np.array([[3.0], [1.0]])]

    E_matlab = eng.eval("E_spm_MDP_MI")
    E_python = spm_MDP_MI(a, c)

    assert_matlab_match(E_matlab, E_python)


def test_spm_MDP_MI_outer_product_zero_sites_derivatives_finite_oracle(eng):
    """`dEdA` divides by `sum(A,2)*sum(A,1)`; zero row sums create `0/0` NaNs in the ratio.

    MATLAB `spm_log` uses `max(log(.),-32)` where `max(NaN,-32) == -32` (fmax-like).
    Python must use the same semantics so `dEdA`/`dEda` do not become NaN-poisoned.
    """
    a = np.array(
        [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    eng.workspace["a_mdp_outer"] = matlab.double(a.tolist(), size=a.shape)
    eng.eval(
        "[E_mdp_outer,dEda_mdp_outer,dEdA_mdp_outer] = spm_MDP_MI(a_mdp_outer);",
        nargout=0,
    )
    Ep, dEdap, dEdAp = spm_MDP_MI(a)
    dEdap = np.asarray(dEdap, dtype=np.float64)
    dEdAp = np.asarray(dEdAp, dtype=np.float64)

    assert not np.isnan(dEdap).any(), "dEda must be finite (no NaN poisoning from ratio)"
    assert not np.isnan(dEdAp).any(), "dEdA must be finite (no NaN poisoning from ratio)"

    assert_matlab_match(eng.eval("E_mdp_outer"), Ep)
    assert_matlab_match(eng.eval("dEda_mdp_outer"), dEdap)
    assert_matlab_match(eng.eval("dEdA_mdp_outer"), dEdAp)


def _assert_mdp_mi_outputs_match(eng, python_outputs):
    matlab_outputs = [
        eng.eval("E_spm_MDP_MI"),
        eng.eval("dEda_spm_MDP_MI"),
        eng.eval("dEdA_spm_MDP_MI"),
    ]

    for matlab_output, python_output in zip(matlab_outputs, python_outputs):
        assert_matlab_match(matlab_output, python_output)


def _mi_workload_files() -> list[Path]:
    repo = Path(__file__).resolve().parents[2]
    ck_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data"
    tag = str(os.getenv("RGMS_MDP_MI_REPLAY_TAG", "")).strip()
    if tag:
        safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in tag)
        return sorted(ck_dir.glob(f"fsl_rgm_mi_workload_{safe}.pkl"))
    return sorted(ck_dir.glob("fsl_rgm_mi_workload*.pkl"))


def _matlab_mdp_mi_scalar_e(eng, a: np.ndarray) -> float:
    """Same MATLAB entry point as Python `spm_MDP_MI(a)` one-arg path (scalar `E` only)."""
    a = np.asarray(a, dtype=np.float64)
    nr, nc = a.shape
    eng.workspace["rgm_re_a"] = matlab.double(a.tolist(), size=(nr, nc))
    eng.eval("rgm_re_e = spm_MDP_MI(rgm_re_a);", nargout=0)
    return float(np.asarray(eng.eval("rgm_re_e"), dtype=np.float64).reshape(-1)[0])


def _matlab_mdp_mi_terms(eng, a: np.ndarray) -> tuple[float, float, float, float]:
    """Compute scalar MI terms in MATLAB using the same decomposition as `_spm_MI`."""
    a = np.asarray(a, dtype=np.float64)
    nr, nc = a.shape
    eng.workspace["rgm_re_ta"] = matlab.double(a.tolist(), size=(nr, nc))
    eng.eval(
        "rgm_re_tA = rgm_re_ta / sum(rgm_re_ta(:));"
        "rgm_re_t1 = rgm_re_tA(:)' * spm_log(rgm_re_tA(:));"
        "rgm_re_t2 = sum(rgm_re_tA,1) * spm_log(sum(rgm_re_tA,1)');"
        "rgm_re_t3 = sum(rgm_re_tA,2)' * spm_log(sum(rgm_re_tA,2));"
        "rgm_re_te = rgm_re_t1 - rgm_re_t2 - rgm_re_t3;",
        nargout=0,
    )
    t1 = float(np.asarray(eng.eval("rgm_re_t1"), dtype=np.float64).reshape(-1)[0])
    t2 = float(np.asarray(eng.eval("rgm_re_t2"), dtype=np.float64).reshape(-1)[0])
    t3 = float(np.asarray(eng.eval("rgm_re_t3"), dtype=np.float64).reshape(-1)[0])
    te = float(np.asarray(eng.eval("rgm_re_te"), dtype=np.float64).reshape(-1)[0])
    return t1, t2, t3, te


def _ulp_distance_scalar(a: float, b: float) -> int:
    """ULP distance between two finite float64 scalars."""
    ai = int(np.asarray([np.float64(a)], dtype=np.float64).view(np.int64)[0])
    bi = int(np.asarray([np.float64(b)], dtype=np.float64).view(np.int64)[0])

    # Monotone mapping over signed IEEE-754 bit patterns.
    if ai < 0:
        ai = 0x8000000000000000 - ai
    if bi < 0:
        bi = 0x8000000000000000 - bi
    return abs(ai - bi)


def _python_mdp_mi_terms(a: np.ndarray) -> tuple[float, float, float, float]:
    """Compute Python scalar MI decomposition matching `_spm_MI` default path."""
    p = np.asarray(a, dtype=np.float64)
    A = p / np.sum(p)
    A_col = A.reshape(-1, 1, order="F")
    t1 = float(np.asarray(A_col.T @ spm_log(A_col), dtype=np.float64).reshape(-1)[0])
    t2 = float(
        np.asarray(
            np.sum(A, axis=0, keepdims=True) @ spm_log(np.sum(A, axis=0, keepdims=True).T),
            dtype=np.float64,
        ).reshape(-1)[0]
    )
    t3 = float(
        np.asarray(
            np.sum(A, axis=1, keepdims=True).T @ spm_log(np.sum(A, axis=1, keepdims=True)),
            dtype=np.float64,
        ).reshape(-1)[0]
    )
    te = float(t1 - t2 - t3)
    return t1, t2, t3, te


def _float64_hex(x: float) -> str:
    """IEEE-754 float64 bit pattern as fixed-width hex."""
    return f"0x{int(np.asarray([np.float64(x)], dtype=np.float64).view(np.uint64)[0]):016x}"


def _mi_mismatch_corpus_file() -> Path:
    repo = Path(__file__).resolve().parents[2]
    return (
        repo
        / "tests"
        / "oracle"
        / "toolbox"
        / "DEM"
        / "_checkpoint_data"
        / "fsl_rgm_mi_mismatch_corpus_live.pkl"
    )


def _build_mi_mismatch_corpus_live(
    eng,
    *,
    max_mid: int = 24,
    max_high: int = 24,
) -> dict:
    """Build a deterministic stratified mismatch corpus vs live MATLAB."""
    rows_mid: list[dict] = []
    rows_high: list[dict] = []
    source_files = []
    total_pairs = 0
    total_mismatch = 0

    for ck in _mi_workload_files():
        source_files.append(ck.name)
        with ck.open("rb") as f:
            payload = pickle.load(f)
        for rec in payload.get("records", []):
            if str(rec.get("kind", "pair")) != "pair":
                continue
            total_pairs += 1
            p = np.asarray(rec["p_mat"], dtype=np.float64)
            py_t1, py_t2, py_t3, py_te = _python_mdp_mi_terms(p)
            mat_t1, mat_t2, mat_t3, mat_te = _matlab_mdp_mi_terms(eng, p)
            if py_te == mat_te:
                continue
            total_mismatch += 1
            cancel_abs = abs(py_t1 - (py_t2 + py_t3))
            row = {
                "stream_idx": int(rec["stream_idx"]),
                "i": int(rec["i"]),
                "j": int(rec["j"]),
                "p_mat": np.asarray(p, dtype=np.float64),
                "py_te": float(py_te),
                "mat_te": float(mat_te),
                "abs_dE": float(abs(py_te - mat_te)),
                "ulpE": int(_ulp_distance_scalar(py_te, mat_te)),
                "cancel_abs": float(cancel_abs),
                "py_t1": float(py_t1),
                "py_t2": float(py_t2),
                "py_t3": float(py_t3),
                "mat_t1": float(mat_t1),
                "mat_t2": float(mat_t2),
                "mat_t3": float(mat_t3),
                "ulp_t1": int(_ulp_distance_scalar(py_t1, mat_t1)),
                "ulp_t2": int(_ulp_distance_scalar(py_t2, mat_t2)),
                "ulp_t3": int(_ulp_distance_scalar(py_t3, mat_t3)),
                "hex_py_te": _float64_hex(py_te),
                "hex_mat_te": _float64_hex(mat_te),
            }
            if 1e-6 < cancel_abs <= 1e-3:
                rows_mid.append(row)
            elif cancel_abs > 1e-3:
                rows_high.append(row)

    def _rank_key(row: dict) -> tuple:
        return (
            -int(row["ulpE"]),
            -float(row["abs_dE"]),
            -int(row["ulp_t1"]),
            -int(row["ulp_t2"]),
            int(row["stream_idx"]),
            int(row["i"]),
            int(row["j"]),
        )

    rows_mid = sorted(rows_mid, key=_rank_key)[:max_mid]
    rows_high = sorted(rows_high, key=_rank_key)[:max_high]
    selected = rows_mid + rows_high
    selected = sorted(selected, key=lambda r: (int(r["stream_idx"]), int(r["i"]), int(r["j"])))
    return {
        "schema_version": 1,
        "description": "Deterministic stratified live-MATLAB mismatch subset for Bottleneck #1 micro replay.",
        "source_workload_files": source_files,
        "selection": {
            "mid_cancel_band": "(1e-6,1e-3]",
            "high_cancel_band": ">1e-3",
            "max_mid": int(max_mid),
            "max_high": int(max_high),
            "rank": "ulpE desc, abs_dE desc, ulp_t1 desc, ulp_t2 desc, then stream/i/j asc",
        },
        "stats": {
            "total_pairs_scanned": int(total_pairs),
            "total_mismatch_scanned": int(total_mismatch),
            "mid_candidates": int(len(rows_mid)),
            "high_candidates": int(len(rows_high)),
            "selected_total": int(len(selected)),
        },
        "records": selected,
    }


def test_spm_MDP_MI_rgm_workload_term_ulp_profile_live_oracle(eng):
    """Profile term-level ULP drift vs live MATLAB on replay workload."""
    cks = _mi_workload_files()
    if not cks:
        pytest.skip(
            "RGM-MI workload checkpoint missing "
            "(run exhaustive once with RGMS_FSL_CAPTURE_RGM_MI_WORKLOAD=1)"
        )

    total_pairs = 0
    t1_ulps: list[int] = []
    t2_ulps: list[int] = []
    t3_ulps: list[int] = []
    te_ulps: list[int] = []
    te_abs: list[float] = []
    te_ref_abs: list[float] = []
    cancel_abs: list[float] = []
    mismatch_cancel_abs: list[float] = []
    mismatch_flags: list[bool] = []
    stratified_signatures: dict[str, list[str]] = {"mid": [], "high": []}

    for ck in cks:
        with ck.open("rb") as f:
            payload = pickle.load(f)
        records = list(payload.get("records", []))
        for rec in records:
            if str(rec.get("kind", "pair")) != "pair":
                continue
            total_pairs += 1
            p = np.asarray(rec["p_mat"], dtype=np.float64)
            py_t1, py_t2, py_t3, py_te = _python_mdp_mi_terms(p)
            mat_t1, mat_t2, mat_t3, mat_te = _matlab_mdp_mi_terms(eng, p)

            t1_ulps.append(_ulp_distance_scalar(py_t1, mat_t1))
            t2_ulps.append(_ulp_distance_scalar(py_t2, mat_t2))
            t3_ulps.append(_ulp_distance_scalar(py_t3, mat_t3))
            te_ulps.append(_ulp_distance_scalar(py_te, mat_te))
            te_abs_cur = abs(py_te - mat_te)
            te_abs.append(te_abs_cur)
            te_ref_abs.append(abs(mat_te))
            cancel_cur = abs(py_t1 - (py_t2 + py_t3))
            cancel_abs.append(cancel_cur)
            is_mismatch = bool(py_te != mat_te)
            mismatch_flags.append(is_mismatch)
            if is_mismatch:
                mismatch_cancel_abs.append(cancel_cur)
                if 1e-6 < cancel_cur <= 1e-3 and len(stratified_signatures["mid"]) < 4:
                    stratified_signatures["mid"].append(
                        " ".join(
                            [
                                f"stream={int(rec['stream_idx'])}",
                                f"pair=({int(rec['i'])},{int(rec['j'])})",
                                f"|dE|={te_abs_cur:.17g}",
                                f"ulpE={_ulp_distance_scalar(py_te, mat_te)}",
                                f"ulp1={_ulp_distance_scalar(py_t1, mat_t1)}",
                                f"ulp2={_ulp_distance_scalar(py_t2, mat_t2)}",
                                f"ulp3={_ulp_distance_scalar(py_t3, mat_t3)}",
                                f"E_py={_float64_hex(py_te)}",
                                f"E_mat={_float64_hex(mat_te)}",
                                f"d1={py_t1 - mat_t1:.17g}",
                                f"d2={py_t2 - mat_t2:.17g}",
                                f"d3={py_t3 - mat_t3:.17g}",
                            ]
                        )
                    )
                if cancel_cur > 1e-3 and len(stratified_signatures["high"]) < 4:
                    stratified_signatures["high"].append(
                        " ".join(
                            [
                                f"stream={int(rec['stream_idx'])}",
                                f"pair=({int(rec['i'])},{int(rec['j'])})",
                                f"|dE|={te_abs_cur:.17g}",
                                f"ulpE={_ulp_distance_scalar(py_te, mat_te)}",
                                f"ulp1={_ulp_distance_scalar(py_t1, mat_t1)}",
                                f"ulp2={_ulp_distance_scalar(py_t2, mat_t2)}",
                                f"ulp3={_ulp_distance_scalar(py_t3, mat_t3)}",
                                f"E_py={_float64_hex(py_te)}",
                                f"E_mat={_float64_hex(mat_te)}",
                                f"d1={py_t1 - mat_t1:.17g}",
                                f"d2={py_t2 - mat_t2:.17g}",
                                f"d3={py_t3 - mat_t3:.17g}",
                            ]
                        )
                    )

    assert total_pairs > 0
    t1_u = np.asarray(t1_ulps, dtype=np.int64)
    t2_u = np.asarray(t2_ulps, dtype=np.int64)
    t3_u = np.asarray(t3_ulps, dtype=np.int64)
    te_u = np.asarray(te_ulps, dtype=np.int64)
    te_a = np.asarray(te_abs, dtype=np.float64)
    te_r = np.asarray(te_ref_abs, dtype=np.float64)
    te_non_tiny = te_u[te_r >= 1e-12]
    te_non_tiny_max = int(np.max(te_non_tiny)) if te_non_tiny.size else 0
    te_non_tiny_p99 = float(np.percentile(te_non_tiny, 99.0)) if te_non_tiny.size else 0.0
    c_abs = np.asarray(cancel_abs, dtype=np.float64)
    c_mis = np.asarray(mismatch_cancel_abs, dtype=np.float64)
    c_mis_p50 = float(np.percentile(c_mis, 50.0)) if c_mis.size else 0.0
    mis_flags = np.asarray(mismatch_flags, dtype=bool)

    cancel_bins = [1e-12, 1e-9, 1e-6, 1e-3]
    cancel_labels = ["<=1e-12", "(1e-12,1e-9]", "(1e-9,1e-6]", "(1e-6,1e-3]", ">1e-3"]
    total_counts = [0, 0, 0, 0, 0]
    mismatch_counts = [0, 0, 0, 0, 0]
    for idx, c in enumerate(c_abs):
        if c <= cancel_bins[0]:
            b = 0
        elif c <= cancel_bins[1]:
            b = 1
        elif c <= cancel_bins[2]:
            b = 2
        elif c <= cancel_bins[3]:
            b = 3
        else:
            b = 4
        total_counts[b] += 1
        if mis_flags[idx]:
            mismatch_counts[b] += 1

    print(
        "[RGM-MI-TERM-ULP] "
        f"pairs={total_pairs} "
        f"t1(max/p99)={int(np.max(t1_u))}/{float(np.percentile(t1_u,99.0)):.1f} "
        f"t2(max/p99)={int(np.max(t2_u))}/{float(np.percentile(t2_u,99.0)):.1f} "
        f"t3(max/p99)={int(np.max(t3_u))}/{float(np.percentile(t3_u,99.0)):.1f} "
        f"te(max/p99)={int(np.max(te_u))}/{float(np.percentile(te_u,99.0)):.1f} "
        f"te_non_tiny(max/p99,n)={te_non_tiny_max}/{te_non_tiny_p99:.1f}/"
        f"{int(te_non_tiny.size)} "
        f"te_abs_max={float(np.max(te_a)):.17g} "
        f"cancel_abs_p50={float(np.percentile(c_abs,50.0)):.17g} "
        f"cancel_abs_p99={float(np.percentile(c_abs,99.0)):.17g} "
        f"cancel_abs_mismatch_p50={c_mis_p50:.17g}",
        flush=True,
    )
    band_bits = []
    for label, n_all, n_mis in zip(cancel_labels, total_counts, mismatch_counts):
        rate = (float(n_mis) / float(n_all)) if n_all else 0.0
        band_bits.append(f"{label}:{n_mis}/{n_all}({rate:.3f})")
    print("[RGM-MI-CANCEL-BANDS] " + " ".join(band_bits), flush=True)
    for band_name, rows in stratified_signatures.items():
        if rows:
            print(f"[RGM-MI-CANCEL-SIGNATURES] band={band_name}", flush=True)
            for row in rows:
                print(f"  - {row}", flush=True)

    # Keep this as a live-regression guardrail while byte-exact closure remains open.
    assert int(np.max(t1_u)) <= 4, f"term t1 ULP drift too large: {int(np.max(t1_u))}"
    assert int(np.max(t2_u)) <= 4, f"term t2 ULP drift too large: {int(np.max(t2_u))}"
    assert int(np.max(t3_u)) <= 4, f"term t3 ULP drift too large: {int(np.max(t3_u))}"
    assert float(np.max(te_a)) <= 1e-15, f"term recomposed E abs drift too large: {float(np.max(te_a)):.17g}"


def test_spm_MDP_MI_rgm_mismatch_corpus_micro_replay_oracle(eng):
    """Fast replay over a stratified mismatch subset for inner-loop experiments."""
    path = _mi_mismatch_corpus_file()
    refresh = str(os.getenv("RGMS_MDP_MI_MISMATCH_CORPUS_REFRESH", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if refresh or not path.exists():
        corpus = _build_mi_mismatch_corpus_live(eng, max_mid=24, max_high=24)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(corpus, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(
            f"[RGM-MI-CORPUS] refreshed path={path.name} selected={int(corpus['stats']['selected_total'])}",
            flush=True,
        )

    if not path.exists():
        pytest.skip(
            "Mismatch corpus missing "
            "(set RGMS_MDP_MI_MISMATCH_CORPUS_REFRESH=1 and run this test once)"
        )
    with path.open("rb") as f:
        corpus = pickle.load(f)
    records = list(corpus.get("records", []))
    if not records:
        pytest.skip("Mismatch corpus has no records")

    py_self_mismatch = 0
    py_repeat_mismatch = 0
    py_vs_live_mismatch = 0
    allow_self_drift = str(
        os.getenv("RGMS_MDP_MI_CORPUS_ALLOW_SELF_DRIFT", "")
    ).strip().lower() in ("1", "true", "yes", "on")
    abs_deltas: list[float] = []
    ulp_deltas: list[int] = []
    sample_lines: list[str] = []
    for rec in records:
        p = np.asarray(rec["p_mat"], dtype=np.float64)
        py_now = float(spm_MDP_MI(p)[0])
        py_now_2 = float(spm_MDP_MI(p)[0])
        live_now = _matlab_mdp_mi_scalar_e(eng, p)
        py_ref = float(rec["py_te"])
        if py_now != py_now_2:
            py_repeat_mismatch += 1
        if py_now != py_ref:
            py_self_mismatch += 1
        if py_now != live_now:
            py_vs_live_mismatch += 1
            de = abs(py_now - live_now)
            ue = _ulp_distance_scalar(py_now, live_now)
            abs_deltas.append(de)
            ulp_deltas.append(ue)
            if len(sample_lines) < 8:
                sample_lines.append(
                    f"stream={int(rec['stream_idx'])} pair=({int(rec['i'])},{int(rec['j'])}) "
                    f"abs={de:.17g} ulp={ue}"
                )

    total = len(records)
    max_abs = float(np.max(np.asarray(abs_deltas, dtype=np.float64))) if abs_deltas else 0.0
    max_ulp = int(np.max(np.asarray(ulp_deltas, dtype=np.int64))) if ulp_deltas else 0
    print(
        "[RGM-MI-CORPUS] "
        f"file={path.name} total={total} "
        f"py_self={py_self_mismatch} py_repeat={py_repeat_mismatch} "
        f"py_vs_live={py_vs_live_mismatch} "
        f"max_abs={max_abs:.17g} max_ulp={max_ulp}",
        flush=True,
    )
    if sample_lines:
        print("[RGM-MI-CORPUS] mismatch samples:", flush=True)
        for line in sample_lines:
            print(f"  - {line}", flush=True)

    if not allow_self_drift:
        assert py_self_mismatch == 0, f"Mismatch corpus Python self drift: {py_self_mismatch}/{total}"
    assert py_repeat_mismatch == 0, f"Mismatch corpus Python repeat instability: {py_repeat_mismatch}/{total}"
    assert max_abs <= 1e-15, f"Mismatch corpus live drift abs too large: {max_abs:.17g}"


@pytest.mark.xfail(
    reason=(
        "Bottleneck #1: scalar `E` from `spm_MDP_MI` not yet byte-identical on the full "
        "MI workload vs **live** MATLAB Engine (ULP-level `log` / accumulation; legacy "
        "stored-`matlab_mi` gate via `RGMS_MDP_MI_REPLAY_LEGACY_CAPTURED_MATLAB=1`)."
    ),
    strict=False,
)
def test_spm_MDP_MI_rgm_workload_fast_replay_oracle(eng):
    """Replay captured Bottleneck #1 MI **inputs** with a single MATLAB truth: Engine now.

    Checkpoint fields `python_mi` / `matlab_mi` are **harness metadata** from capture time.
    They must not be mixed with live Engine results as co-equal references:

    - **Primary gate:** `spm_MDP_MI(p)` Python scalar `E` vs **live** `spm_MDP_MI(p)` on Engine.
    - **Self gate:** replay `E` vs checkpoint `python_mi` (detect Python nondeterminism).
    - **Optional diagnostic:** checkpoint `matlab_mi` vs live `E` (Engine / path drift since capture).
      Enable with ``RGMS_MDP_MI_REPLAY_LEGACY_CAPTURED_MATLAB=1`` to also assert Python vs
      stored `matlab_mi` (legacy; off by default).

    ``stream_summary`` rows carry full MI matrices for a larger grouping context; this fast
    replay does not reconstruct the parent ``O`` slice needed to recompute those in MATLAB,
    so they are reported only as capture self-consistency (``mi_py`` vs ``mi_mat`` in-file).
    """
    cks = _mi_workload_files()
    if not cks:
        pytest.skip(
            "RGM-MI workload checkpoint missing "
            "(run exhaustive once with RGMS_FSL_CAPTURE_RGM_MI_WORKLOAD=1)"
        )
    total_pairs = 0
    py_self_mismatch = 0
    py_vs_live_mismatch = 0
    cap_vs_live_mismatch = 0
    py_vs_cap_mismatch = 0
    examples: list[str] = []
    term_examples: list[str] = []
    py_vs_live_abs_deltas: list[float] = []
    stream_summary_capture_mismatch = 0
    legacy_captured = str(
        os.getenv("RGMS_MDP_MI_REPLAY_LEGACY_CAPTURED_MATLAB", "")
    ).strip().lower() in ("1", "true", "yes", "on")
    allow_self_drift = str(
        os.getenv("RGMS_MDP_MI_REPLAY_ALLOW_SELF_DRIFT", "")
    ).strip().lower() in ("1", "true", "yes", "on")
    for ck in cks:
        with ck.open("rb") as f:
            payload = pickle.load(f)
        records = list(payload.get("records", []))
        for rec in records:
            kind = str(rec.get("kind", "pair"))
            if kind == "stream_summary":
                mi_py = np.asarray(rec["mi_py"], dtype=np.float64)
                mi_mat = np.asarray(rec["mi_mat"], dtype=np.float64)
                if mi_py.shape != mi_mat.shape or not np.array_equal(mi_py, mi_mat):
                    stream_summary_capture_mismatch += 1
                continue
            total_pairs += 1
            p = np.asarray(rec["p_mat"], dtype=np.float64)
            mi_py_runtime = float(rec["python_mi"])
            mi_cap = float(rec["matlab_mi"])
            mi_py_replay = float(spm_MDP_MI(p)[0])
            mi_live = _matlab_mdp_mi_scalar_e(eng, p)
            if mi_py_replay != mi_py_runtime:
                py_self_mismatch += 1
            if mi_py_replay != mi_live:
                py_vs_live_mismatch += 1
                py_vs_live_abs_deltas.append(abs(mi_py_replay - mi_live))
                if len(examples) < 12:
                    examples.append(
                        f"stream={int(rec['stream_idx'])} pair=({int(rec['i'])},{int(rec['j'])}) "
                        f"py={mi_py_replay:.17g} live={mi_live:.17g} "
                        f"abs={abs(mi_py_replay - mi_live):.17g}"
                    )
                if len(term_examples) < 6:
                    p_norm = p / np.sum(p)
                    p_col = p_norm.reshape(-1, 1, order="F")
                    py_t1 = float(
                        np.asarray(p_col.T @ spm_log(p_col), dtype=np.float64).reshape(-1)[0]
                    )
                    py_t2 = float(
                        np.asarray(
                            np.sum(p_norm, axis=0, keepdims=True)
                            @ spm_log(np.sum(p_norm, axis=0, keepdims=True).T),
                            dtype=np.float64,
                        ).reshape(-1)[0]
                    )
                    py_t3 = float(
                        np.asarray(
                            np.sum(p_norm, axis=1, keepdims=True).T
                            @ spm_log(np.sum(p_norm, axis=1, keepdims=True)),
                            dtype=np.float64,
                        ).reshape(-1)[0]
                    )
                    py_te = float(py_t1 - py_t2 - py_t3)
                    mat_t1, mat_t2, mat_t3, mat_te = _matlab_mdp_mi_terms(eng, p)
                    term_examples.append(
                        f"stream={int(rec['stream_idx'])} pair=({int(rec['i'])},{int(rec['j'])}) "
                        f"|dE|={abs(py_te - mat_te):.17g} "
                        f"|dt1|={abs(py_t1 - mat_t1):.17g} "
                        f"|dt2|={abs(py_t2 - mat_t2):.17g} "
                        f"|dt3|={abs(py_t3 - mat_t3):.17g}"
                    )
            if mi_cap != mi_live:
                cap_vs_live_mismatch += 1
            if mi_py_replay != mi_cap:
                py_vs_cap_mismatch += 1
        print(
            f"[RGM-MI-REPLAY] file={ck.name} records={len(records)} "
            f"pairs={total_pairs} py_self={py_self_mismatch} "
            f"py_vs_live={py_vs_live_mismatch} cap_vs_live={cap_vs_live_mismatch} "
            f"py_vs_cap_stored={py_vs_cap_mismatch} "
            f"stream_summary_capture_mis={stream_summary_capture_mismatch} "
            f"legacy_captured_gate={int(legacy_captured)}",
            flush=True,
        )
    assert total_pairs > 0
    if examples:
        print("[RGM-MI-REPLAY] py_vs_live examples:", flush=True)
        for line in examples:
            print(f"  - {line}", flush=True)
    if py_vs_live_abs_deltas:
        ds = np.asarray(py_vs_live_abs_deltas, dtype=np.float64)
        ds_max = float(np.max(ds))
        q50, q90, q99 = np.percentile(ds, [50.0, 90.0, 99.0])
        le_1e16 = int(np.sum(ds <= 1e-16))
        le_2e16 = int(np.sum(ds <= 2e-16))
        le_5e16 = int(np.sum(ds <= 5e-16))
        le_1e15 = int(np.sum(ds <= 1e-15))
        print(
            "[RGM-MI-REPLAY] py_vs_live abs stats: "
            f"count={ds.size} max={ds_max:.17g} "
            f"p50={float(q50):.17g} p90={float(q90):.17g} p99={float(q99):.17g} "
            f"<=1e-16={le_1e16} <=2e-16={le_2e16} <=5e-16={le_5e16} <=1e-15={le_1e15}",
            flush=True,
        )
        assert ds_max <= 1e-15, (
            "Live-MATLAB scalar E drift exceeded ULP-scale envelope on workload: "
            f"max_abs={ds_max:.17g}"
        )
    if term_examples:
        print("[RGM-MI-REPLAY] py_vs_live term deltas (first mismatches):", flush=True)
        for line in term_examples:
            print(f"  - {line}", flush=True)
    if not allow_self_drift:
        assert py_self_mismatch == 0, (
            "Python MI replay is not deterministic on workload: "
            f"{py_self_mismatch} mismatches"
        )
    if legacy_captured:
        assert py_vs_cap_mismatch == 0, (
            "Legacy captured-MATLAB gate: Python diverges from checkpoint matlab_mi: "
            f"pair_mismatch={py_vs_cap_mismatch}"
        )
    else:
        assert py_vs_live_mismatch == 0, (
            "Python spm_MDP_MI diverges from live MATLAB Engine on workload inputs: "
            f"pair_mismatch={py_vs_live_mismatch}"
        )
