#!/usr/bin/env python3
"""OPTIM1FULL Product B consolidated parity gate.

See ``optim1full_parity_contract.py`` for lane discipline and ladder definitions.

Tier **1** — MI isolated boundaries (causal + final, both sites).
Tier **2** — call **3** RDP assembly from ``MDP_post_nr`` (Engine ``spm_RDP_sort``; ``RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1``).
Tier **3a** — Entry **12** call-2 game **1** VB (script **3** + audit + **4**).
Tier **3e** / **3f** — Entry **12** call-3 / call-4 VB (needs ``capture_optim1full_parity``).
Tier **3b** / **3c** — *(retired)* — superseded by Model **B** ledger (§ **11.7.2**).
Tier **3g** — full ``MDP_post_nr`` rebuild from frozen ``MDP_pre.mat`` (ledger NR segments).
**pairing-audit** — live Entries **1–11** vs authority ``MDP_pre.mat`` (incl. VB call **1**).
**full-replay-integration** (step **4a**) — *(RETIRED 2026-07-13)* — compute-redundant with
``--pairing-audit`` + ``--tier3g`` (same ``MDP_post_nr`` compare/authority); now exits **2**.
**full-replay** (step **4b**) — *optional completion smoke* — full driver + VB calls **3**/**4**;
``MDP_post_nr`` compare at NR boundary. Not a mandatory parity gate.

Same isolated-then-orchestrated discipline as OPTIM1 ``optim1_parity_gate.py`` (§ **2**).

Usage::

    python tests/demo1/optim1full/optim1full_parity_gate.py --check-authority
    python tests/demo1/optim1full/optim1full_parity_gate.py --tier1
    python tests/demo1/optim1full/optim1full_parity_gate.py --tier2
    python tests/demo1/optim1full/optim1full_parity_gate.py --tier3a
    python tests/demo1/optim1full/optim1full_parity_gate.py --tier3e
    python tests/demo1/optim1full/optim1full_parity_gate.py --tier3f
    python tests/demo1/optim1full/optim1full_parity_gate.py --tier3g
    python tests/demo1/optim1full/optim1full_parity_gate.py --pairing-audit
    python tests/demo1/optim1full/optim1full_parity_gate.py --full-replay   # optional smoke
    python tests/demo1/optim1full/optim1full_parity_gate.py --plot-oracle
    python tests/demo1/optim1full/optim1full_parity_gate.py --vb-optim-tier3a
    python tests/demo1/optim1full/optim1full_parity_gate.py --vb-optim-tier3e
    python tests/demo1/optim1full/optim1full_parity_gate.py --vb-optim-tier3f
    python tests/demo1/optim1full/optim1full_parity_gate.py --vb-optim-nr-g01

W2 ``--vb-optim-tier3*`` / ``--vb-optim-nr-g01``: optim vs frozen MATLAB PDP
(``optim1full_vb_optim_matlab_equivalence.py``); not fidelity-vs-optim.

**Integrated optim adoption** (CLOSED 2026-07-13): witnessed by ``--pairing-audit`` +
``--tier3g`` under the optim lane (now the dispatch default). Both compare the live driver
``MDP_post_nr`` / ``MDP_pre`` to the frozen MATLAB-lineage authority mats.
Fast ledger check: ``optim1full_vb_dev_adoption_smoke.py`` (optim ledger slice vs MATLAB).

W1-B full-flow plot witness: set ``RGMS_OPTIM1FULL_PLOT=1`` before ``--full-replay``
(or ``optim1full_run_full_replay_isolated.py --plot-witness``).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_TIER1_SCRIPTS = (
    "tests/demo1/optim1full/optim1full_compare_mi382_causal.py",
    "tests/demo1/optim1full/optim1full_compare_mi382_pkl_to_mat.py",
    "tests/demo1/optim1full/optim1full_compare_mi429_causal.py",
    "tests/demo1/optim1full/optim1full_compare_mi429_pkl_to_mat.py",
)

_TIER2_RUN = "tests/demo1/optim1full/optim1full_run_call3_assembly_isolated.py"
_TIER2_COMPARE = "tests/demo1/optim1full/optim1full_compare_call3_rdp_pkl_to_mat.py"

_TIER3G_RUN = "tests/demo1/optim1full/optim1full_run_post_nr_isolated.py"
_TIER3G_COMPARE = "tests/demo1/optim1full/optim1full_compare_post_nr_pkl_to_mat.py"

_PAIRING_RUN = "tests/demo1/optim1full/optim1full_run_optim1_segment_isolated.py"
_PAIRING_COMPARE = "tests/demo1/optim1full/optim1full_compare_mdp_pre_pkl_to_mat.py"

_FULL_REPLAY_RUN = "tests/demo1/optim1full/optim1full_run_full_replay_isolated.py"
_FULL_REPLAY_COMPARE = "tests/demo1/optim1full/optim1full_compare_post_nr_pkl_to_mat.py"

_PLOT_ORACLE_TEST = "tests/demo1/optim1full/test_optim1full_plot.py"


def _run_script(rel: str, *extra_args: str) -> int:
    cmd = [sys.executable, str(_REPO / rel), *extra_args]
    print(f"[optim1full_parity_gate] RUN {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=str(_REPO))


def _run_pytest(rel: str, *extra_args: str) -> int:
    cmd = [sys.executable, "-m", "pytest", str(_REPO / rel), "-v", *extra_args]
    print(f"[optim1full_parity_gate] RUN {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=str(_REPO))


def _run_vb_optim_matlab_equivalence_tag(
    tag: str,
    *,
    gate_label: str,
    deadline_minutes: str,
) -> int:
    print(
        f"[optim1full_parity_gate] W2 {gate_label}: optim vs frozen MATLAB PDP on tag {tag!r}",
        file=sys.stderr,
        flush=True,
    )
    return _run_script(
        "tests/demo1/optim1full/optim1full_vb_optim_matlab_equivalence.py",
        "--tag",
        tag,
        "--deadline-minutes",
        deadline_minutes,
    )


def _full_replay_runner_argv(args: argparse.Namespace, *, stop_after_nr: bool = False) -> list[str]:
    argv: list[str] = ["--deadline-minutes", str(args.deadline_minutes)]
    if stop_after_nr:
        argv.insert(0, "--stop-after-nr")
    if bool(getattr(args, "vb_dev_optim", False)):
        argv.append("--vb-dev-optim")
    # W1-E: honor env or explicit future flag — pass --plot-witness when PLOT=1.
    plot_env = os.getenv("RGMS_OPTIM1FULL_PLOT", "").strip().lower() in ("1", "true", "yes")
    if plot_env or bool(getattr(args, "plot_witness", False)):
        argv.append("--plot-witness")
    return argv


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.optim1full.optim1full_authority import assert_optim1full_authority_present

    p = argparse.ArgumentParser(description="OPTIM1FULL Product B parity gate")
    p.add_argument("--check-authority", action="store_true")
    p.add_argument("--tier1", action="store_true", help="MI boundaries")
    p.add_argument("--tier2", action="store_true", help="call-3 RDP assembly from MDP_post_nr")
    p.add_argument("--tier3a", action="store_true", help="call-2 game 1 VB (Entry 12 lane)")
    p.add_argument("--tier3e", action="store_true", help="call-3 VB (Entry 12 lane)")
    p.add_argument("--tier3f", action="store_true", help="call-4 VB (Entry 12 lane)")
    p.add_argument("--tier3b", action="store_true", help="call-2 NR games 2-16 VB (Entry 12 lane)")
    p.add_argument("--tier3c", action="store_true", help="call-2 NR games 17-32 VB (Entry 12 lane)")
    p.add_argument(
        "--tier3g",
        action="store_true",
        help="full MDP_post_nr rebuild (ledger replay + compare)",
    )
    p.add_argument(
        "--tier3",
        action="store_true",
        help="alias for --tier3g (deprecated; prefer --tier3a/3e/3f ladder)",
    )
    p.add_argument(
        "--persistence-audit",
        action="store_true",
        help="B2: staging mdp_pre vs authority MDP_pre.mat (no live driver)",
    )
    p.add_argument(
        "--pairing-audit",
        action="store_true",
        help="live Entries 1–11 MDP_pre (incl. VB call 1) vs authority mat",
    )
    p.add_argument(
        "--full-replay-integration",
        action="store_true",
        help="RETIRED (exits 2): compute-redundant with --pairing-audit + --tier3g",
    )
    p.add_argument(
        "--integration-compare-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--full-replay",
        action="store_true",
        help="step 4b (optional completion smoke): full driver + MDP_post_nr compare",
    )
    p.add_argument(
        "--plot-oracle",
        action="store_true",
        help="W1-C: pytest fixture-first plot oracles (no VB; ~1 min)",
    )
    p.add_argument(
        "--plot-parity",
        action="store_true",
        help=(
            "W1: plot-fn parity (Python vs MATLAB plot code on MATLAB-owned fence PDP). "
            "Default dump-once: reuse existing spine input.pkl and oracle.mat when present "
            "and fingerprint sidecars match; always compare + pytest. Heavy export/Engine only "
            "if artifacts/sidecars missing/stale or --force-export / --force-refresh-oracle. "
            "Use --plot-parity-check-only first."
        ),
    )
    p.add_argument(
        "--plot-parity-check-only",
        action="store_true",
        help="verify plot-parity wiring + MATLAB-owned authority presence only (no heavy runs)",
    )
    p.add_argument(
        "--plot-parity-site",
        default=None,
        help=(
            "restrict --plot-parity to one site_id (RGB or registered non-RGB "
            "e.g. dem_gameplay; default: all four RGB)"
        ),
    )
    p.add_argument(
        "--force-export",
        action="store_true",
        help=(
            "with --plot-parity: re-export spine input.pkl even when present "
            "(after compute change; prefer --plot-parity-site for one fence)"
        ),
    )
    p.add_argument(
        "--force-refresh-oracle",
        action="store_true",
        help=(
            "with --plot-parity: re-run MATLAB plot oracle even when oracle.mat present "
            "(rgb_jkh=12PLOT; gameplay_o2rgb=frame_rgb+control; after plot.m or authority change)"
        ),
    )
    p.add_argument(
        "--vb-optim-tier3a",
        action="store_true",
        help="W2: optim vs frozen MATLAB PDP on tier 3a tag (call2)",
    )
    p.add_argument(
        "--vb-optim-tier3e",
        action="store_true",
        help="W2: optim vs frozen MATLAB PDP on tier 3e tag (call3)",
    )
    p.add_argument(
        "--vb-optim-tier3f",
        action="store_true",
        help="W2: optim vs frozen MATLAB PDP on tier 3f tag (call4)",
    )
    p.add_argument(
        "--vb-optim-nr-g01",
        action="store_true",
        help="W2: optim vs frozen MATLAB PDP on NR game 1 tag (rgms_atari_optim1full_nr_g01)",
    )
    p.add_argument(
        "--deadline-minutes",
        default="240",
        help="wall-clock budget for --full-replay isolated runner (default 240)",
    )
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        add_vb_dev_optim_cli_argument,
        configure_vb_dev_optim,
    )

    add_vb_dev_optim_cli_argument(p)
    args = p.parse_args(argv)

    # OPTIM1FULL go-forward compute = optim lane (2026-07-13). The dispatch-driven gates
    # (pairing-audit / tier3g / full-replay) resolve to optim by default and propagate
    # RGMS_OPTIM1FULL_VB_DEV_OPTIM=1 to their subprocess drivers. --vb-fidelity forces the
    # historical fidelity oracle on the dispatch surface for diagnostics only. W2
    # --vb-optim-* gates use an explicit ``optim`` lane and are unaffected either way; the
    # fidelity Entry-12 tier gates (--tier3a/3e/3f) call spm_MDP_VB_XXX directly (no dispatch).
    vb_fidelity = bool(getattr(args, "vb_fidelity", False))
    _dispatch_driver_gate = bool(args.pairing_audit or args.tier3g or args.tier3 or args.full_replay)
    if vb_fidelity:
        configure_vb_dev_optim(False)
    elif _dispatch_driver_gate:
        configure_vb_dev_optim(True)

    tier3g = bool(args.tier3g or args.tier3)
    persistence_audit = bool(args.persistence_audit)
    pairing_audit = bool(args.pairing_audit)
    full_replay_integration = bool(args.full_replay_integration)
    full_replay = bool(args.full_replay)
    plot_oracle = bool(args.plot_oracle)
    plot_parity = bool(args.plot_parity or args.plot_parity_check_only)
    vb_optim_tier3a = bool(args.vb_optim_tier3a)
    vb_optim_tier3e = bool(args.vb_optim_tier3e)
    vb_optim_tier3f = bool(args.vb_optim_tier3f)
    vb_optim_nr_g01 = bool(args.vb_optim_nr_g01)
    vb_optim_any = vb_optim_tier3a or vb_optim_tier3e or vb_optim_tier3f or vb_optim_nr_g01
    compute_tier = bool(
        args.tier1
        or args.tier2
        or args.tier3a
        or args.tier3b
        or args.tier3c
        or args.tier3e
        or args.tier3f
        or tier3g
        or persistence_audit
        or pairing_audit
        or full_replay_integration
        or full_replay
    )
    any_action = compute_tier or plot_oracle or plot_parity or vb_optim_any

    if full_replay_integration:
        # RETIRED 2026-07-13 (hard): 4a's live pre-NR path + NR (stop_after_nr) with the
        # MDP_post_nr compare is compute-redundant with --pairing-audit (live MDP_pre incl.
        # vb_call1) + --tier3g (NR accumulation), which use the same compare script/authority.
        print(
            "[optim1full_parity_gate] --full-replay-integration (step 4a) is RETIRED — "
            "compute-redundant with --pairing-audit + --tier3g (same MDP_post_nr compare/authority). "
            "Use those two gates for integrated optim adoption; see OPTIM1FULL.md "
            "§ 'Current status — optim adoption'.",
            file=sys.stderr,
            flush=True,
        )
        return 2

    if args.check_authority:
        try:
            assert_optim1full_authority_present()
        except FileNotFoundError as exc:
            print(f"[optim1full_parity_gate] {exc}", file=sys.stderr)
            return 2
        print("[optim1full_parity_gate] authority OK", file=sys.stderr)
        if not any_action:
            return 0

    if compute_tier:
        try:
            assert_optim1full_authority_present()
        except FileNotFoundError as exc:
            print(f"[optim1full_parity_gate] {exc}", file=sys.stderr)
            return 2

    t0 = time.perf_counter()
    if args.tier1:
        for rel in _TIER1_SCRIPTS:
            rc = _run_script(rel)
            if rc != 0:
                return rc

    if args.tier2:
        for rel in (_TIER2_RUN, _TIER2_COMPARE):
            rc = _run_script(rel)
            if rc != 0:
                return rc

    if args.tier3a:
        from tests.demo1.optim1full.optim1full_parity_phases import run_tier_3a_call2_game1

        try:
            run_tier_3a_call2_game1()
        except subprocess.CalledProcessError:
            return 1
        except FileNotFoundError as exc:
            print(f"[optim1full_parity_gate] {exc}", file=sys.stderr)
            return 2

    if args.tier3e:
        from tests.demo1.optim1full.optim1full_parity_phases import run_tier_3e_call3

        try:
            run_tier_3e_call3()
        except subprocess.CalledProcessError:
            return 1
        except FileNotFoundError as exc:
            print(f"[optim1full_parity_gate] {exc}", file=sys.stderr)
            return 2

    if args.tier3f:
        from tests.demo1.optim1full.optim1full_parity_phases import run_tier_3f_call4

        try:
            run_tier_3f_call4()
        except subprocess.CalledProcessError:
            return 1
        except FileNotFoundError as exc:
            print(f"[optim1full_parity_gate] {exc}", file=sys.stderr)
            return 2

    if args.tier3b or args.tier3c:
        print(
            "[optim1full_parity_gate] tier 3b/3c retired — per-game Entry 12 tag RNG was wrong model; "
            "use optim1full_capture_rand_ledger.py + § 11.7.2 ledger replay (OPTIM1.md)",
            file=sys.stderr,
        )
        return 2

    if tier3g:
        from tests.demo1.optim1full.optim1full_rand_ledger import ledger_artifacts_present

        if not ledger_artifacts_present():
            print(
                "[optim1full_parity_gate] tier 3g blocked: missing Model B ledger "
                "(run optim1full_capture_rand_ledger.py once; OPTIM1.md § 11.7.2)",
                file=sys.stderr,
                flush=True,
            )
            return 2
        from tests.demo1.optim1full.optim1full_authority import assert_optim1full_mdp_ledger_session

        try:
            assert_optim1full_mdp_ledger_session()
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"[optim1full_parity_gate] tier 3g blocked: {exc}", file=sys.stderr, flush=True)
            return 2
        print(
            "[optim1full_parity_gate] tier 3g: full MDP_post_nr rebuild (ledger replay)",
            file=sys.stderr,
            flush=True,
        )
        for rel in (_TIER3G_RUN, _TIER3G_COMPARE):
            rc = _run_script(rel)
            if rc != 0:
                return rc

    if persistence_audit:
        import pickle

        from tests.demo1.optim1full.optim1full_mi_boundary import (
            assert_optim1full_mdp_pre_pairing_equal,
            load_mdp_from_mat,
        )
        from tests.demo1.optim1full.optim1full_paths import (
            optim1full_fixtures_dir,
            optim1full_mdp_pre_active_inference_mat,
        )

        staging_path = optim1full_fixtures_dir() / "deprecated" / "_optim1full_capture_staging.pkl"
        mat_path = optim1full_mdp_pre_active_inference_mat()
        if not staging_path.is_file():
            print(f"[optim1full_parity_gate] persistence-audit missing staging {staging_path}", file=sys.stderr)
            return 2
        with staging_path.open("rb") as f:
            staged = pickle.load(f)
        mdp_pre = staged["mdp_pre"]
        nm = int(staged["nm"])
        print(
            "[optim1full_parity_gate] persistence-audit: staging mdp_pre vs authority MDP_pre.mat",
            file=sys.stderr,
            flush=True,
        )
        mdp_mat = load_mdp_from_mat(mat_path, "MDP_pre_active_inference")
        assert_optim1full_mdp_pre_pairing_equal(mdp_pre, mdp_mat, nm)
        print("[optim1full_parity_gate] persistence-audit PASS", file=sys.stderr, flush=True)

    if pairing_audit:
        from tests.demo1.optim1full.optim1full_rand_ledger import ledger_artifacts_present

        if not ledger_artifacts_present():
            print(
                "[optim1full_parity_gate] pairing-audit blocked: missing Model B ledger",
                file=sys.stderr,
                flush=True,
            )
            return 2
        print(
            "[optim1full_parity_gate] pairing-audit: live Entries 1–11 vs authority MDP_pre.mat",
            file=sys.stderr,
            flush=True,
        )
        rc = _run_script(_PAIRING_RUN, "--deadline-minutes", str(args.deadline_minutes))
        if rc != 0:
            return rc
        rc = _run_script(_PAIRING_COMPARE)
        if rc != 0:
            return rc

    if full_replay:
        from tests.demo1.optim1full.optim1full_rand_ledger import ledger_artifacts_present

        if not ledger_artifacts_present():
            print(
                "[optim1full_parity_gate] full-replay blocked: missing Model B ledger "
                "(run optim1full_capture_rand_ledger.py once; OPTIM1.md § 11.7.2)",
                file=sys.stderr,
                flush=True,
            )
            return 2
        from tests.demo1.optim1full.optim1full_authority import assert_optim1full_mdp_ledger_session

        try:
            assert_optim1full_mdp_ledger_session()
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"[optim1full_parity_gate] full-replay blocked: {exc}", file=sys.stderr, flush=True)
            return 2

        print(
            "[optim1full_parity_gate] step 4b (optional completion smoke): "
            "full run_dem_atariiii_optim1full_parity + MDP_post_nr compare",
            file=sys.stderr,
            flush=True,
        )
        rc = _run_script(_FULL_REPLAY_RUN, *_full_replay_runner_argv(args))
        if rc != 0:
            return rc
        rc = _run_script(_FULL_REPLAY_COMPARE)
        if rc != 0:
            return rc

    if plot_oracle:
        from tests.demo1.optim1full.optim1full_plot import assert_optim1full_plot_fixtures_present

        try:
            assert_optim1full_plot_fixtures_present()
        except FileNotFoundError as exc:
            print(f"[optim1full_parity_gate] {exc}", file=sys.stderr)
            return 2
        print(
            "[optim1full_parity_gate] plot-oracle: fixture-first plot pytest (no VB)",
            file=sys.stderr,
            flush=True,
        )
        rc = _run_pytest(_PLOT_ORACLE_TEST)
        if rc != 0:
            return rc

    if plot_parity:
        from tests.demo1.optim1full.optim1full_plot_parity import run_plot_parity

        sites = [str(args.plot_parity_site).strip()] if args.plot_parity_site else None
        check_only = bool(args.plot_parity_check_only)
        force_export = bool(args.force_export)
        force_refresh_oracle = bool(args.force_refresh_oracle)
        mode = "check-only"
        if not check_only:
            bits = ["dump-once pair"]
            if force_export:
                bits.append("force-export")
            if force_refresh_oracle:
                bits.append("force-refresh-oracle")
            mode = "+".join(bits)
        print(
            "[optim1full_parity_gate] plot-parity: Python plot code vs MATLAB plot code on the "
            f"MATLAB-owned fence PDP ({mode})",
            file=sys.stderr,
            flush=True,
        )
        rc = run_plot_parity(
            sites,
            check_only=check_only,
            force_export=force_export,
            force_refresh_oracle=force_refresh_oracle,
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if vb_optim_tier3a:
        from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
            ENTRY12_OPTIM1FULL_CALL2_TAG,
        )

        rc = _run_vb_optim_matlab_equivalence_tag(
            ENTRY12_OPTIM1FULL_CALL2_TAG,
            gate_label="vb-optim-tier3a",
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if vb_optim_tier3e:
        from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
            ENTRY12_OPTIM1FULL_CALL3_TAG,
        )

        rc = _run_vb_optim_matlab_equivalence_tag(
            ENTRY12_OPTIM1FULL_CALL3_TAG,
            gate_label="vb-optim-tier3e",
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if vb_optim_tier3f:
        from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
            ENTRY12_OPTIM1FULL_CALL4_TAG,
        )

        rc = _run_vb_optim_matlab_equivalence_tag(
            ENTRY12_OPTIM1FULL_CALL4_TAG,
            gate_label="vb-optim-tier3f",
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if vb_optim_nr_g01:
        from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
            ENTRY12_OPTIM1FULL_NR_G01_TAG,
        )

        rc = _run_vb_optim_matlab_equivalence_tag(
            ENTRY12_OPTIM1FULL_NR_G01_TAG,
            gate_label="vb-optim-nr-g01",
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if any_action:
        print(
            f"[optim1full_parity_gate] PASS wall_s={time.perf_counter() - t0:.3f}",
            file=sys.stderr,
        )
        return 0

    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
