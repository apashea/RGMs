import numpy as np
import os
import pickle
from pathlib import Path

import matlab
import pytest

from python_src.spm_MDP_MI import spm_MDP_MI
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


@pytest.mark.xfail(
    reason=(
        "Bottleneck #1: scalar MI vs captured MATLAB references not yet byte-identical "
        "(ULP-level `log`); replay remains an explicit progress oracle."
    ),
    strict=False,
)
def test_spm_MDP_MI_rgm_workload_fast_replay_oracle():
    """Replay captured Bottleneck #1 MI workload against MATLAB references."""
    cks = _mi_workload_files()
    if not cks:
        pytest.skip(
            "RGM-MI workload checkpoint missing "
            "(run exhaustive once with RGMS_FSL_CAPTURE_RGM_MI_WORKLOAD=1)"
        )
    total_pairs = 0
    py_self_mismatch = 0
    py_vs_mat_mismatch = 0
    examples: list[str] = []
    stream_summary_mismatch = 0
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
                    stream_summary_mismatch += 1
                continue
            total_pairs += 1
            p = np.asarray(rec["p_mat"], dtype=np.float64)
            mi_py_runtime = float(rec["python_mi"])
            mi_mat = float(rec["matlab_mi"])
            mi_py_replay = float(spm_MDP_MI(p)[0])
            if mi_py_replay != mi_py_runtime:
                py_self_mismatch += 1
            if mi_py_replay != mi_mat:
                py_vs_mat_mismatch += 1
                if len(examples) < 12:
                    examples.append(
                        f"stream={int(rec['stream_idx'])} pair=({int(rec['i'])},{int(rec['j'])}) "
                        f"py={mi_py_replay:.17g} mat={mi_mat:.17g} "
                        f"abs={abs(mi_py_replay - mi_mat):.17g}"
                    )
        print(
            f"[RGM-MI-REPLAY] file={ck.name} records={len(records)} "
            f"pairs={total_pairs} py_self={py_self_mismatch} py_vs_mat={py_vs_mat_mismatch} "
            f"summary_mis={stream_summary_mismatch}",
            flush=True,
        )
    assert total_pairs > 0
    if examples:
        print("[RGM-MI-REPLAY] mismatch examples:", flush=True)
        for line in examples:
            print(f"  - {line}", flush=True)
    if not allow_self_drift:
        assert py_self_mismatch == 0, (
            "Python MI replay is not deterministic on workload: "
            f"{py_self_mismatch} mismatches"
        )
    assert py_vs_mat_mismatch == 0 and stream_summary_mismatch == 0, (
        "Python spm_MDP_MI diverges from captured MATLAB MI workload: "
        f"pair_mismatch={py_vs_mat_mismatch}, summary_mismatch={stream_summary_mismatch}"
    )
