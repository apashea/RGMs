#!/usr/bin/env python3
"""MATLAB-only sanity: FSL backward ``RDP_reference`` vs Entry 12 Call 1 ``RDP`` ``.mat``.

Does **not** load Python PKL. Does **not** run Entry 12 scripts. Read-only compare of
two MATLAB-produced nested ``RDP`` trees.

Report: ``matlab_custom/fsl_backward_compare_matlab_rdps_output.txt``
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _report_path() -> Path:
    return _REPO / "matlab_custom" / "fsl_backward_compare_matlab_rdps_output.txt"


def _load_rdp_from_mat(mat_path: Path, var: str) -> object:
    from scipy.io import loadmat

    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    raw = loadmat(str(mat_path), simplify_cells=True)
    if var not in raw:
        keys = sorted(k for k in raw if not str(k).startswith("__"))
        raise KeyError(f"{var} not in {mat_path}, keys={keys}")
    return mat_nested_to_py(raw[var])


def main(argv: list[str] | None = None) -> int:
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call_rdp_mat_path
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--fsl-mat",
        type=Path,
        default=_REPO
        / "tests/oracle/toolbox/DEM/fixtures/dem_atari_rand_buf_through_entry11.mat",
    )
    p.add_argument(
        "--entry12-mat",
        type=Path,
        default=None,
        help="Default: DEMAtariIII_XXX_12_rdp.mat (Entry 12 Call 1 input; read-only)",
    )
    args = p.parse_args(argv)
    entry12_mat = args.entry12_mat or entry12_atari_call_rdp_mat_path("rgms_canonical")
    fsl_mat = args.fsl_mat.resolve()

    out_path = _report_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def log(msg: str) -> None:
        lines.append(msg)
        print(msg, file=sys.stderr)

    try:
        if not fsl_mat.is_file():
            raise FileNotFoundError(fsl_mat)
        if not entry12_mat.is_file():
            raise FileNotFoundError(entry12_mat)
        ref = _load_rdp_from_mat(fsl_mat, "RDP_reference")
        e12 = _load_rdp_from_mat(entry12_mat, "RDP")
        log(f"[FSL backward MATLAB sanity] RDP_reference={fsl_mat}")
        log(f"[FSL backward MATLAB sanity] Entry12 RDP={entry12_mat}")
        _assert_nested_rdp_equal(ref, e12, "RDP")
        log("OK: RDP_reference matches Entry 12 Call 1 RDP mat")
        code = 0
    except Exception as exc:
        log(f"FAIL: {exc}")
        traceback.print_exc(file=sys.stderr)
        code = 1

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
