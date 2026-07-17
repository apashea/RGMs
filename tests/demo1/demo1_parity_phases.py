"""DEMO1 parity phase runners (invoked by ``DEM_AtariIII_demo1_parity.py``)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.demo1.demo1_checkpoint_resume import (
    checkpoint_present,
    log_checkpoint_skip,
    phase_b_units,
    phase_c_skip_script3,
    phase_c_skip_script4,
    phase_d_skip,
)
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root, demo1_shipped_parity_png

_REPO = demo1_repo_root()
_ORACLE_DEM = _REPO / "tests" / "oracle" / "toolbox" / "DEM"
_MATLAB_DEMO1 = _REPO / "matlab_custom" / "demo1"
_MATLAB_ENTRY12 = _REPO / "matlab_custom" / "entry12"

# FSL backward 1→11 lane (DEMO1.md §6).
_PHASE_B_SCRIPTS: tuple[str, ...] = (
    "fsl_backward_preflight_rand_k_entry1.py",
    "fsl_backward_materialize_mdp_pre_entry1_pkl.py",
    "fsl_backward_run_entry1_isolated.py",
    "fsl_backward_compare_entry1_pkl_to_mat.py",
    "fsl_backward_preflight_rand_k_entry2.py",
    "fsl_backward_materialize_mdp_pre_entry2_pkl.py",
    "fsl_backward_run_entry2_isolated.py",
    "fsl_backward_compare_entry2_pkl_to_mat.py",
    "fsl_backward_preflight_rand_k_entry3.py",
    "fsl_backward_materialize_mdp_pre_entry3_pkl.py",
    "fsl_backward_run_entry3_isolated.py",
    "fsl_backward_compare_entry3_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry4_pkl.py",
    "fsl_backward_run_entry4_isolated.py",
    "fsl_backward_compare_entry4_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry5_pkl.py",
    "fsl_backward_run_entry5_isolated.py",
    "fsl_backward_compare_entry5_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry6_pkl.py",
    "fsl_backward_run_entry6_isolated.py",
    "fsl_backward_compare_entry6_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry7_pkl.py",
    "fsl_backward_run_entry7_isolated.py",
    "fsl_backward_compare_entry7_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry9_pkl.py",
    "fsl_backward_run_entry9_isolated.py",
    "fsl_backward_compare_entry9_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry10_pkl.py",
    "fsl_backward_run_entry10_isolated.py",
    "fsl_backward_compare_entry10_pkl_to_mat.py",
    "fsl_backward_materialize_mdp_pre_entry11_pkl.py",
    "fsl_backward_run_entry11_isolated.py",
    "fsl_backward_compare_entry11_pkl_to_mat.py",
    "fsl_backward_validate_entry11_through_entry12.py",
)


def _env_base() -> dict[str, str]:
    env = os.environ.copy()
    fix = str(demo1_fixtures_dir())
    env["RGMS_DEMO1_FIXTURES_DIR"] = fix
    env["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = fix
    env["RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS"] = "1"
    return env


def _run_matlab_batch(func: str, *, mdir: Path | None = None, extra_env: dict[str, str] | None = None) -> None:
    cwd = mdir or _MATLAB_DEMO1
    env = _env_base()
    if extra_env:
        env.update(extra_env)
    batch = f"cd('{cwd.as_posix()}'); {func}; exit(0);"
    cmd = ["matlab", "-batch", batch]
    print(f"[DEMO1 parity] matlab -batch {func}", file=sys.stderr)
    proc = subprocess.run(cmd, cwd=str(_REPO), env=env, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, file=sys.stderr, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)


def _run_python(
    script: Path,
    extra_env: dict[str, str] | None = None,
    *,
    extra_argv: list[str] | None = None,
) -> None:
    env = _env_base()
    if extra_env:
        env.update(extra_env)
    argv = [sys.executable, str(script)]
    if extra_argv:
        argv.extend(extra_argv)
    print(f"[DEMO1 parity] python {script.relative_to(_REPO)}", file=sys.stderr)
    subprocess.run(argv, cwd=str(_REPO), env=env, check=True)


def _run_pytest(target: str, extra_env: dict[str, str] | None = None) -> None:
    env = _env_base()
    if extra_env:
        env.update(extra_env)
    print(f"[DEMO1 parity] pytest {target}", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "pytest", target, "-q"],
        cwd=str(_REPO),
        env=env,
        check=True,
    )


def _fsl_fixtures() -> Path:
    return demo1_fixtures_dir()


def phase_a_fsl_targets_missing() -> bool:
    fix = _fsl_fixtures()
    names = (
        "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat",
        "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat",
        "dem_atari_rand_buf_through_entry11.mat",
        "DEMAtariIII_fsl_1_11_plot_ctx.mat",
        "DEMAtariIII_XXX_12_rdp.mat",
    )
    return any(not (fix / n).is_file() for n in names)


def _entry12_capture_missing() -> bool:
    fix = _fsl_fixtures()
    return not (fix / "DEMAtariIII_entry12_rgms_canonical_12A.mat").is_file() or not (
        fix / "DEMAtariIII_XXX_12_pdp.mat"
    ).is_file()


def _entry12_plot_mat_missing() -> bool:
    return not (_fsl_fixtures() / "DEMAtariIII_entry12_rgms_canonical_12PLOT.mat").is_file()


def run_phase_a() -> None:
    """Singular FSL dump + Entry 12 legacy capture + 12PLOT mat (one FSL ledger)."""
    if phase_a_fsl_targets_missing():
        _run_matlab_batch("DEMO1_dump_all_fixtures", mdir=_MATLAB_DEMO1)

    fix = _fsl_fixtures()
    rdp = fix / "DEMAtariIII_XXX_12_rdp.mat"
    k_mat = fix / "entry12_vb_rand_K.mat"

    if _entry12_capture_missing():
        if not rdp.is_file():
            raise FileNotFoundError(f"missing Entry 12 RDP mat after singular dump: {rdp}")
        if not k_mat.is_file():
            _run_python(_ORACLE_DEM / "entry12_preflight_vb_rand_k.py")
        _run_matlab_batch(
            "DEMAtariIII_entry12_dump_all_subentries",
            mdir=_MATLAB_ENTRY12,
            extra_env={
                "RGMS_ENTRY12_CAPTURE_LEGACY_LOAD": "1",
                "RGMS_ENTRY12_CAPTURE_SKIP_CALL2": "1",
                "RGMS_ENTRY12_CAPTURE_RDP_MAT": str(rdp),
                "RGMS_ENTRY12_CAPTURE_RUN_TAG": "rgms_canonical",
            },
        )

    if _entry12_plot_mat_missing():
        _run_matlab_batch(
            "DEMAtariIII_entry12_12plot_capture",
            mdir=_MATLAB_ENTRY12,
            extra_env={"RGMS_ENTRY12_CAPTURE_RUN_TAG": "rgms_canonical"},
        )


def run_phase_b() -> None:
    """FSL backward 1→11 compares + Entry 11→12 gate."""
    fix = _fsl_fixtures()
    for unit in phase_b_units():
        if checkpoint_present(unit.artifact_id, fix):
            log_checkpoint_skip(unit.label, artifact_id=unit.artifact_id)
            continue
        for name in unit.scripts:
            path = _ORACLE_DEM / name
            if not path.is_file():
                raise FileNotFoundError(f"missing Phase B script: {path}")
            if name == "fsl_backward_validate_entry11_through_entry12.py":
                _run_python(path, extra_argv=["--vb-only"])
            else:
                _run_python(path)


def run_phase_c() -> None:
    """Entry 12 script 3 + draw audit + script 4."""
    fix = _fsl_fixtures()
    k_mat = fix / "entry12_vb_rand_K.mat"
    if not k_mat.is_file():
        _run_python(_ORACLE_DEM / "entry12_preflight_vb_rand_k.py")

    if phase_c_skip_script3(fix) and phase_c_skip_script4(fix):
        log_checkpoint_skip("Phase C (script 3, audit, script 4)", artifact_id="C4_compare")
        return

    ran_script3 = False
    if phase_c_skip_script3(fix):
        log_checkpoint_skip("Entry 12 script 3", artifact_id="C3_pdp")
    else:
        _run_pytest(
            str(_ORACLE_DEM / "test_DEM_AtariIII_XXX_12.py::test_xxx_12_fsl_rdp_to_pdp_pkl"),
            extra_env={"RGMS_ATARI_RUN_XXX_12": "1"},
        )
        ran_script3 = True

    _run_python(_REPO / "matlab_custom" / "entry12_draw_index_audit.py")
    if ran_script3 or not phase_c_skip_script4(fix):
        _run_python(
            _ORACLE_DEM / "XXX_12_compare_pdp_pkl_to_mat.py",
            extra_env={},
            extra_argv=["--coerce-sparse-to-dense-for-compare"],
        )
    else:
        log_checkpoint_skip("Entry 12 script 4", artifact_id="C4_compare")


def run_phase_d() -> None:
    """12PLOT pytest + shipped parity PNG."""
    fix = _fsl_fixtures()
    if phase_d_skip(fix):
        log_checkpoint_skip("Phase D visual", artifact_id="D3_png")
        return
    _run_pytest(str(_ORACLE_DEM / "test_spm_show_RGB_entry12plot.py"))
    # Fresh subprocess avoids MATLAB Engine DLL clash with matplotlib/pyexpat in parity parent.
    script = (
        "from pathlib import Path\n"
        "import shutil\n"
        "from tests.demo1.demo1_paths import demo1_repo_root, demo1_shipped_parity_png\n"
        "from python_src.toolbox.DEM.entry12_plot import run_entry12plot_phase_b_visual_review\n"
        "root = demo1_repo_root()\n"
        "_, _, _, _, compare = run_entry12plot_phase_b_visual_review(repo_root=root)\n"
        "if compare is None or not compare.is_file():\n"
        "    raise SystemExit('missing 12PLOT compare PNG')\n"
        "shipped = demo1_shipped_parity_png()\n"
        "shipped.parent.mkdir(parents=True, exist_ok=True)\n"
        "shutil.copy2(compare, shipped)\n"
        "print(f'[DEMO1 parity] shipped PNG {shipped}')\n"
    )
    env = _env_base()
    print("[DEMO1 parity] python (subprocess) entry12plot phase B visual review", file=sys.stderr)
    subprocess.run([sys.executable, "-c", script], cwd=str(_REPO), env=env, check=True)


def run_full_parity() -> None:
    run_phase_a()
    run_phase_b()
    run_phase_c()
    run_phase_d()
