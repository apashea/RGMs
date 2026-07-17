#!/usr/bin/env python3
"""W2 Phase **3** — row **5** spine adoption proof (fidelity vs ``--vb-dev-optim``).

Runs ``optim1full_export_spine_fence_pdp`` for ``dem_active_inference_nr`` (resume
``mdp_pre``), writes sidecar ``.pkl`` artifacts, compares PDP via
``optim1full_compare_spine_fence_pdp_pkl_to_mat.py --ref-pkl``.

Usage (repo root)::

    python tests/demo1/optim1full/optim1full_vb_dev_adoption_spine.py --fidelity-export
    python tests/demo1/optim1full/optim1full_vb_dev_adoption_spine.py --optim-export
    python tests/demo1/optim1full/optim1full_vb_dev_adoption_spine.py --compare
    python tests/demo1/optim1full/optim1full_vb_dev_adoption_spine.py --run
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_SITE = "dem_active_inference_nr"
_SIDECAR_DIR = _REPO / "tests" / "demo1" / "optim1full" / "sidecars" / "w2_phase3"
_FIDELITY_PKL = _SIDECAR_DIR / f"{_SITE}_fidelity.pkl"
_OPTIM_PKL = _SIDECAR_DIR / f"{_SITE}_optim.pkl"
_COMPARE = _REPO / "tests" / "demo1" / "optim1full" / "optim1full_compare_spine_fence_pdp_pkl_to_mat.py"
_EXPORT = _REPO / "tests" / "demo1" / "optim1full" / "optim1full_export_spine_fence_pdp.py"


def _run_export(*, vb_dev_optim: bool, output_pkl: Path, deadline_minutes: str) -> int:
    from tests.demo1.optim1full.optim1full_vb_dispatch import configure_vb_dev_optim

    configure_vb_dev_optim(bool(vb_dev_optim))
    cmd = [
        sys.executable,
        str(_EXPORT),
        "--site",
        _SITE,
        "--resume-from",
        "mdp_pre",
        "--deadline-minutes",
        str(deadline_minutes),
        "--output-pkl",
        str(output_pkl),
    ]
    if vb_dev_optim:
        cmd.append("--vb-dev-optim")
    print(f"[optim1full_vb_dev_adoption_spine] RUN {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=str(_REPO))


def _run_compare() -> int:
    cmd = [
        sys.executable,
        str(_COMPARE),
        "--site",
        _SITE,
        "--pkl",
        str(_OPTIM_PKL),
        "--ref-pkl",
        str(_FIDELITY_PKL),
    ]
    print(f"[optim1full_vb_dev_adoption_spine] RUN {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=str(_REPO))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fidelity-export", action="store_true", help="export fidelity sidecar only")
    p.add_argument("--optim-export", action="store_true", help="export optim sidecar only")
    p.add_argument("--compare", action="store_true", help="compare existing sidecars")
    p.add_argument("--run", action="store_true", help="fidelity export + optim export + compare")
    p.add_argument("--deadline-minutes", default="240")
    args = p.parse_args(argv)

    if not (args.fidelity_export or args.optim_export or args.compare or args.run):
        p.print_help()
        return 2

    _SIDECAR_DIR.mkdir(parents=True, exist_ok=True)

    if args.run or args.fidelity_export:
        rc = _run_export(
            vb_dev_optim=False,
            output_pkl=_FIDELITY_PKL,
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if args.run or args.optim_export:
        rc = _run_export(
            vb_dev_optim=True,
            output_pkl=_OPTIM_PKL,
            deadline_minutes=str(args.deadline_minutes),
        )
        if rc != 0:
            return rc

    if args.run or args.compare:
        if not _FIDELITY_PKL.is_file() or not _OPTIM_PKL.is_file():
            print(
                f"[optim1full_vb_dev_adoption_spine] missing sidecar(s): "
                f"fidelity={_FIDELITY_PKL.is_file()} optim={_OPTIM_PKL.is_file()}",
                file=sys.stderr,
            )
            return 2
        return _run_compare()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
