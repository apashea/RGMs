"""
ctypes wrapper for vendored LAPACK ``dgeevx`` (``balanc='N'``).

Built artifact expected at package dir: ``_eig_lapack_nobalance*.dll`` / ``.so``.
See repo-root ``eig.md`` §25.4.
"""

from __future__ import annotations

import ctypes
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Tuple

import numpy as np

_PKG_DIR = Path(__file__).resolve().parent


def _library_path() -> Path | None:
    if sys.platform == "win32":
        names = ["_eig_lapack_nobalance.dll", "eig_lapack_nobalance.dll"]
    elif sys.platform == "darwin":
        names = ["_eig_lapack_nobalance.dylib", "libeig_lapack_nobalance.dylib"]
    else:
        names = ["_eig_lapack_nobalance.so", "libeig_lapack_nobalance.so"]
    for name in names:
        p = _PKG_DIR / name
        if p.is_file():
            return p
    return None


@lru_cache(maxsize=1)
def _load_lib() -> ctypes.CDLL:
    path = _library_path()
    if path is None:
        raise RuntimeError(
            "vendored eig_lapack_nobalance native library not built; "
            "see eig.md §25.4"
        )
    lib = ctypes.CDLL(str(path))
    # gfortran BIND(C) passes default INTEGER by reference (not VALUE).
    lib.rgms_eig_nobalance_dgeevx.argtypes = [
        ctypes.POINTER(ctypes.c_int),  # n
        ctypes.c_void_p,  # a (column-major)
        ctypes.POINTER(ctypes.c_int),  # lda
        ctypes.c_void_p,  # wr
        ctypes.c_void_p,  # wi
        ctypes.c_void_p,  # vr
        ctypes.POINTER(ctypes.c_int),  # ldvr
        ctypes.POINTER(ctypes.c_int),  # info
    ]
    lib.rgms_eig_nobalance_dgeevx.restype = None
    for sym in (
        "rgms_dtrevc3_debug_reset",
        "rgms_dtrevc3_debug_set_col",
        "rgms_dtrevc3_debug_set_row_pair",
        "rgms_dtrevc3_debug_get",
        "rgms_dtrevc3_debug_get_qr0_sweep_table",
        "rgms_dtrevc3_debug_get_qr0_sweep37_boundary",
        "rgms_dtrevc3_debug_get_qr0_sweep7_boundary",
        "rgms_dtrevc3_debug_get_qr0_sweep6_post_dlaqr5",
        "rgms_dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5",
        "rgms_dtrevc3_debug_get_qr5_in_plate",
        "rgms_dtrevc3_debug_get_qr5_plate_trace",
        "rgms_dtrevc3_debug_get_qr5_out5_plate",
        "rgms_dtrevc3_debug_get_qr5_s5_intra_trace",
        "rgms_dtrevc3_debug_get_qr5_s5_zpre_subtrace",
        "rgms_dtrevc3_debug_get_qr5_s5_z1_do140",
        "rgms_dtrevc3_debug_get_qr5_s5_z1_gap",
        "rgms_dtrevc3_debug_get_qr5_s5_z145_pre_zp1",
    ):
        if not hasattr(lib, sym):
            continue
    if hasattr(lib, "rgms_dtrevc3_debug_reset"):
        lib.rgms_dtrevc3_debug_reset.argtypes = []
        lib.rgms_dtrevc3_debug_reset.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_set_col"):
        lib.rgms_dtrevc3_debug_set_col.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.rgms_dtrevc3_debug_set_col.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_set_row_pair"):
        lib.rgms_dtrevc3_debug_set_row_pair.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        lib.rgms_dtrevc3_debug_set_row_pair.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get"):
        _p_i = ctypes.POINTER(ctypes.c_int)
        _p_d = ctypes.POINTER(ctypes.c_double)
        lib.rgms_dtrevc3_debug_get.argtypes = (
            [_p_i] * 5
            + [_p_d] * 20
            + [_p_i] * 4
            + [_p_d] * 2
            + [_p_i]
            + [_p_d] * 14
            + [_p_i] * 4
            + [_p_d] * 2
            + [_p_i]
            + [_p_d] * 2
            + [_p_d] * 2
            + [_p_i]
            + [_p_i] * 2
            + [_p_d] * 11
            + [_p_i] * 6
            + [_p_d] * 4
            + [_p_i] * 3
        )
        lib.rgms_dtrevc3_debug_get.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep_table"):
        _p_i = ctypes.POINTER(ctypes.c_int)
        _p_d = ctypes.POINTER(ctypes.c_double)
        lib.rgms_dtrevc3_debug_get_qr0_sweep_table.argtypes = [
            _p_i,
            _p_i,
            _p_i,
            _p_i,
            _p_i,
            _p_i,
            _p_i,
            _p_i,
            _p_d,
            _p_d,
        ]
        lib.rgms_dtrevc3_debug_get_qr0_sweep_table.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep37_boundary"):
        _p_i = ctypes.POINTER(ctypes.c_int)
        _p_d = ctypes.POINTER(ctypes.c_double)
        lib.rgms_dtrevc3_debug_get_qr0_sweep37_boundary.argtypes = [
            _p_i,
            _p_i,
            _p_i,
            _p_d,
            _p_d,
            _p_d,
            _p_d,
        ]
        lib.rgms_dtrevc3_debug_get_qr0_sweep37_boundary.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep7_boundary"):
        lib.rgms_dtrevc3_debug_get_qr0_sweep7_boundary.argtypes = (
            [_p_i] * 4 + [_p_d] * 8
        )
        lib.rgms_dtrevc3_debug_get_qr0_sweep7_boundary.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep6_post_dlaqr5"):
        lib.rgms_dtrevc3_debug_get_qr0_sweep6_post_dlaqr5.argtypes = (
            [_p_i] * 3 + [_p_d] * 4
        )
        lib.rgms_dtrevc3_debug_get_qr0_sweep6_post_dlaqr5.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5"):
        lib.rgms_dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5.argtypes = (
            [_p_i] * 3 + [_p_d] * 4
        )
        lib.rgms_dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_in_plate"):
        _p_i = ctypes.POINTER(ctypes.c_int)
        _p_d = ctypes.POINTER(ctypes.c_double)
        lib.rgms_dtrevc3_debug_get_qr5_in_plate.argtypes = [
            _p_i,
            _p_d,
            _p_d,
            _p_d,
            _p_d,
            _p_d,
            _p_d,
        ]
        lib.rgms_dtrevc3_debug_get_qr5_in_plate.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_plate_trace"):
        lib.rgms_dtrevc3_debug_get_qr5_plate_trace.argtypes = (
            [_p_i] * 3 + [_p_d] * 8
        )
        lib.rgms_dtrevc3_debug_get_qr5_plate_trace.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_out5_plate"):
        lib.rgms_dtrevc3_debug_get_qr5_out5_plate.argtypes = (
            [_p_i] + [_p_d] * 4
        )
        lib.rgms_dtrevc3_debug_get_qr5_out5_plate.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_intra_trace"):
        lib.rgms_dtrevc3_debug_get_qr5_s5_intra_trace.argtypes = (
            [_p_i] * 10 + [_p_d] * 20
        )
        lib.rgms_dtrevc3_debug_get_qr5_s5_intra_trace.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_zpre_subtrace"):
        lib.rgms_dtrevc3_debug_get_qr5_s5_zpre_subtrace.argtypes = (
            [_p_i] * 4 + [_p_d] * 12
        )
        lib.rgms_dtrevc3_debug_get_qr5_s5_zpre_subtrace.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_z1_do140"):
        lib.rgms_dtrevc3_debug_get_qr5_s5_z1_do140.argtypes = (
            [_p_i] * 7 + [_p_d] * 20
        )
        lib.rgms_dtrevc3_debug_get_qr5_s5_z1_do140.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_z1_gap"):
        lib.rgms_dtrevc3_debug_get_qr5_s5_z1_gap.argtypes = (
            [_p_i] + [_p_d] * 4 + [_p_i] + [_p_d] * 4
        )
        lib.rgms_dtrevc3_debug_get_qr5_s5_z1_gap.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_z145_pre_zp1"):
        lib.rgms_dtrevc3_debug_get_qr5_s5_z145_pre_zp1.argtypes = (
            [_p_i] * 9 + [_p_d] * 12
        )
        lib.rgms_dtrevc3_debug_get_qr5_s5_z145_pre_zp1.restype = None
    if hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_zp1_boundary"):
        lib.rgms_dtrevc3_debug_get_qr5_s5_zp1_boundary.argtypes = (
            [_p_i] * 13 + [_p_d] * 28
        )
        lib.rgms_dtrevc3_debug_get_qr5_s5_zp1_boundary.restype = None
    return lib


def lapack_nobalance_available() -> bool:
    """True when the vendored native library was built and is loadable."""
    path = _library_path()
    if path is None:
        return False
    try:
        _load_lib()
        return True
    except OSError:
        return False


def _real_geev_evecs_to_complex(vr: np.ndarray, wi: np.ndarray) -> np.ndarray:
    vr = np.asarray(vr, dtype=np.float64)
    wi = np.asarray(wi, dtype=np.float64).ravel(order="F")
    n = int(vr.shape[0])
    vc = np.zeros((n, n), dtype=np.complex128, order="F")
    k = 0
    while k < n:
        if abs(float(wi[k])) < 1e-300:
            vc[:, k] = vr[:, k]
            k += 1
        else:
            vc[:, k] = vr[:, k] + 1j * vr[:, k + 1]
            vc[:, k + 1] = vr[:, k] - 1j * vr[:, k + 1]
            k += 2
    return vc


def _debug_api_available() -> bool:
    lib = _load_lib()
    return hasattr(lib, "rgms_dtrevc3_debug_reset")


def dtrevc3_debug_reset() -> None:
    """Clear RGMs DTREVC3 debug COMMON (E2e instrument)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_reset"):
        raise RuntimeError("DTREVC3 debug API not in vendored DLL; rebuild fork")
    lib.rgms_dtrevc3_debug_reset()


def dtrevc3_debug_set_col(fortran_col_1based: int) -> None:
    """Arm DTREVC3 snapshot for Fortran column ``KI`` (1-based)."""
    col = ctypes.c_int(int(fortran_col_1based))
    _load_lib().rgms_dtrevc3_debug_set_col(ctypes.byref(col))


def dtrevc3_debug_set_row_pair(row_lo_1based: int, row_hi_1based: int) -> None:
    """Parametrize debug row pair (Fortran 1-based; default 14/45 = 0-based 13/44)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_set_row_pair"):
        raise RuntimeError("DTREVC3 row-pair API not in vendored DLL; rebuild fork")
    row_lo = ctypes.c_int(int(row_lo_1based))
    row_hi = ctypes.c_int(int(row_hi_1based))
    lib.rgms_dtrevc3_debug_set_row_pair(ctypes.byref(row_lo), ctypes.byref(row_hi))


def dtrevc3_debug_get() -> dict[str, float | int]:
    """Read last DTREVC3 back-transform / ``IDAMAX`` snapshot."""
    lib = _load_lib()
    hit = ctypes.c_int(0)
    col_ki = ctypes.c_int(0)
    idamax_ii = ctypes.c_int(0)
    nb_used = ctypes.c_int(0)
    path_code = ctypes.c_int(0)
    hrd13 = ctypes.c_double(0.0)
    hrd44 = ctypes.c_double(0.0)
    org13 = ctypes.c_double(0.0)
    org44 = ctypes.c_double(0.0)
    hse13 = ctypes.c_double(0.0)
    hse44 = ctypes.c_double(0.0)
    schur1 = ctypes.c_double(0.0)
    schur2 = ctypes.c_double(0.0)
    man13 = ctypes.c_double(0.0)
    man44 = ctypes.c_double(0.0)
    vrk13 = ctypes.c_double(0.0)
    vrk44 = ctypes.c_double(0.0)
    pre13 = ctypes.c_double(0.0)
    pre44 = ctypes.c_double(0.0)
    post13 = ctypes.c_double(0.0)
    post44 = ctypes.c_double(0.0)
    qr0in13 = ctypes.c_double(0.0)
    qr0in44 = ctypes.c_double(0.0)
    qr0out13 = ctypes.c_double(0.0)
    qr0out44 = ctypes.c_double(0.0)
    qr_sweep_total = ctypes.c_int(0)
    qr_first_strict_step = ctypes.c_int(0)
    qr_first_route = ctypes.c_int(0)
    qr_first_it = ctypes.c_int(0)
    qr_first_strict_13 = ctypes.c_double(0.0)
    qr_first_strict_44 = ctypes.c_double(0.0)
    qr5_kacc22 = ctypes.c_int(0)
    qr5_in13 = ctypes.c_double(0.0)
    qr5_in44 = ctypes.c_double(0.0)
    qr5_dir13 = ctypes.c_double(0.0)
    qr5_dir44 = ctypes.c_double(0.0)
    qr5_gem13 = ctypes.c_double(0.0)
    qr5_gem44 = ctypes.c_double(0.0)
    qr5_out13 = ctypes.c_double(0.0)
    qr5_out44 = ctypes.c_double(0.0)
    qr5_hpre13 = ctypes.c_double(0.0)
    qr5_hpre44 = ctypes.c_double(0.0)
    qr5_hpost13 = ctypes.c_double(0.0)
    qr5_hpost44 = ctypes.c_double(0.0)
    qr5_zpre13 = ctypes.c_double(0.0)
    qr5_zpre44 = ctypes.c_double(0.0)
    qr5_z140_first_m = ctypes.c_int(0)
    qr5_z140_first_13_m = ctypes.c_int(0)
    qr5_z140_last_m = ctypes.c_int(0)
    qr5_z140_steps = ctypes.c_int(0)
    qr5_z140_first_abs_13 = ctypes.c_double(0.0)
    qr5_z140_first_abs_44 = ctypes.c_double(0.0)
    qr5_z140_strict_13_m = ctypes.c_int(0)
    qr5_z140_strict_abs_13 = ctypes.c_double(0.0)
    qr5_z140_strict_abs_44 = ctypes.c_double(0.0)
    qr5_z140_last_abs_13 = ctypes.c_double(0.0)
    qr5_z140_last_abs_44 = ctypes.c_double(0.0)
    qr5_z140_iters = ctypes.c_int(0)
    qr5_m5_k = ctypes.c_int(0)
    qr5_m5_hit = ctypes.c_int(0)
    qr5_m5_v1 = ctypes.c_double(0.0)
    qr5_m5_v2 = ctypes.c_double(0.0)
    qr5_m5_v3 = ctypes.c_double(0.0)
    qr5_m5_pre13 = ctypes.c_double(0.0)
    qr5_m5_pre44 = ctypes.c_double(0.0)
    qr5_m5_z13k = ctypes.c_double(0.0)
    qr5_m5_z13k1 = ctypes.c_double(0.0)
    qr5_m5_z13k2 = ctypes.c_double(0.0)
    qr5_m5_z44k = ctypes.c_double(0.0)
    qr5_m5_z44k1 = ctypes.c_double(0.0)
    qr5_m5_z44k2 = ctypes.c_double(0.0)
    qr5_chain_145 = ctypes.c_int(0)
    qr5_strict_145 = ctypes.c_int(0)
    qr5_chain_mbot = ctypes.c_int(0)
    qr5_chain_mtop = ctypes.c_int(0)
    qr5_chain_krcol = ctypes.c_int(0)
    qr5_chain_firstm = ctypes.c_int(0)
    qr5_chain_zpre13 = ctypes.c_double(0.0)
    qr5_chain_zpre44 = ctypes.c_double(0.0)
    qr5_chain_dir13 = ctypes.c_double(0.0)
    qr5_chain_dir44 = ctypes.c_double(0.0)
    qr5_first_m1_145 = ctypes.c_int(0)
    qr5_last_m1_145 = ctypes.c_int(0)
    qr5_tail_first_m1_145 = ctypes.c_int(0)
    lib.rgms_dtrevc3_debug_get(
        ctypes.byref(hit),
        ctypes.byref(col_ki),
        ctypes.byref(idamax_ii),
        ctypes.byref(nb_used),
        ctypes.byref(path_code),
        ctypes.byref(hrd13),
        ctypes.byref(hrd44),
        ctypes.byref(org13),
        ctypes.byref(org44),
        ctypes.byref(hse13),
        ctypes.byref(hse44),
        ctypes.byref(schur1),
        ctypes.byref(schur2),
        ctypes.byref(man13),
        ctypes.byref(man44),
        ctypes.byref(vrk13),
        ctypes.byref(vrk44),
        ctypes.byref(pre13),
        ctypes.byref(pre44),
        ctypes.byref(post13),
        ctypes.byref(post44),
        ctypes.byref(qr0in13),
        ctypes.byref(qr0in44),
        ctypes.byref(qr0out13),
        ctypes.byref(qr0out44),
        ctypes.byref(qr_sweep_total),
        ctypes.byref(qr_first_strict_step),
        ctypes.byref(qr_first_route),
        ctypes.byref(qr_first_it),
        ctypes.byref(qr_first_strict_13),
        ctypes.byref(qr_first_strict_44),
        ctypes.byref(qr5_kacc22),
        ctypes.byref(qr5_in13),
        ctypes.byref(qr5_in44),
        ctypes.byref(qr5_dir13),
        ctypes.byref(qr5_dir44),
        ctypes.byref(qr5_gem13),
        ctypes.byref(qr5_gem44),
        ctypes.byref(qr5_out13),
        ctypes.byref(qr5_out44),
        ctypes.byref(qr5_hpre13),
        ctypes.byref(qr5_hpre44),
        ctypes.byref(qr5_hpost13),
        ctypes.byref(qr5_hpost44),
        ctypes.byref(qr5_zpre13),
        ctypes.byref(qr5_zpre44),
        ctypes.byref(qr5_z140_first_m),
        ctypes.byref(qr5_z140_first_13_m),
        ctypes.byref(qr5_z140_last_m),
        ctypes.byref(qr5_z140_steps),
        ctypes.byref(qr5_z140_first_abs_13),
        ctypes.byref(qr5_z140_first_abs_44),
        ctypes.byref(qr5_z140_strict_13_m),
        ctypes.byref(qr5_z140_strict_abs_13),
        ctypes.byref(qr5_z140_strict_abs_44),
        ctypes.byref(qr5_z140_last_abs_13),
        ctypes.byref(qr5_z140_last_abs_44),
        ctypes.byref(qr5_z140_iters),
        ctypes.byref(qr5_m5_k),
        ctypes.byref(qr5_m5_hit),
        ctypes.byref(qr5_m5_v1),
        ctypes.byref(qr5_m5_v2),
        ctypes.byref(qr5_m5_v3),
        ctypes.byref(qr5_m5_pre13),
        ctypes.byref(qr5_m5_pre44),
        ctypes.byref(qr5_m5_z13k),
        ctypes.byref(qr5_m5_z13k1),
        ctypes.byref(qr5_m5_z13k2),
        ctypes.byref(qr5_m5_z44k),
        ctypes.byref(qr5_m5_z44k1),
        ctypes.byref(qr5_m5_z44k2),
        ctypes.byref(qr5_chain_145),
        ctypes.byref(qr5_strict_145),
        ctypes.byref(qr5_chain_mbot),
        ctypes.byref(qr5_chain_mtop),
        ctypes.byref(qr5_chain_krcol),
        ctypes.byref(qr5_chain_firstm),
        ctypes.byref(qr5_chain_zpre13),
        ctypes.byref(qr5_chain_zpre44),
        ctypes.byref(qr5_chain_dir13),
        ctypes.byref(qr5_chain_dir44),
        ctypes.byref(qr5_first_m1_145),
        ctypes.byref(qr5_last_m1_145),
        ctypes.byref(qr5_tail_first_m1_145),
    )
    path = int(path_code.value)
    return {
        "hit": int(hit.value),
        "fortran_col_ki": int(col_ki.value),
        "idamax_ii_1based": int(idamax_ii.value),
        "idamax_ii_0based": int(idamax_ii.value) - 1,
        "nb_used": int(nb_used.value),
        "path_code": path,
        "path": ("dgemm" if path == 2 else "dgemv" if path == 1 else "unknown"),
        "post_dgehrd_hess_col_abs_13": float(hrd13.value),
        "post_dgehrd_hess_col_abs_44": float(hrd44.value),
        "post_dorghr_q_col_abs_13": float(org13.value),
        "post_dorghr_q_col_abs_44": float(org44.value),
        "post_dhseqr_schur_vr_col_abs_13": float(hse13.value),
        "post_dhseqr_schur_vr_col_abs_44": float(hse44.value),
        "post_dhseqr_pre_dtrevc3_abs_13": float(hse13.value),
        "post_dhseqr_pre_dtrevc3_abs_44": float(hse44.value),
        "schur_w1": float(schur1.value),
        "schur_w2": float(schur2.value),
        "manual_bt_abs_13": float(man13.value),
        "manual_bt_abs_44": float(man44.value),
        "vr_col_k_abs_13": float(vrk13.value),
        "vr_col_k_abs_44": float(vrk44.value),
        "post_bt_pre_idamax_abs_13": float(pre13.value),
        "post_bt_pre_idamax_abs_44": float(pre44.value),
        "pre_abs_13": float(pre13.value),
        "pre_abs_44": float(pre44.value),
        "post_abs_13": float(post13.value),
        "post_abs_44": float(post44.value),
        "dlaqr0_in_vr_col_abs_13": float(qr0in13.value),
        "dlaqr0_in_vr_col_abs_44": float(qr0in44.value),
        "dlaqr0_out_vr_col_abs_13": float(qr0out13.value),
        "dlaqr0_out_vr_col_abs_44": float(qr0out44.value),
        "qr_sweep_total": int(qr_sweep_total.value),
        "qr_first_strict_step": int(qr_first_strict_step.value),
        "qr_first_strict_route": int(qr_first_route.value),
        "qr_first_strict_route_name": (
            "dlaqr3" if int(qr_first_route.value) == 3 else "dlaqr5" if int(qr_first_route.value) == 5 else "unknown"
        ),
        "qr_first_strict_it": int(qr_first_it.value),
        "qr_first_strict_abs_13": float(qr_first_strict_13.value),
        "qr_first_strict_abs_44": float(qr_first_strict_44.value),
        "qr5_kacc22": int(qr5_kacc22.value),
        "qr5_in_abs_13": float(qr5_in13.value),
        "qr5_in_abs_44": float(qr5_in44.value),
        "qr5_dir_abs_13": float(qr5_dir13.value),
        "qr5_dir_abs_44": float(qr5_dir44.value),
        "qr5_gem_abs_13": float(qr5_gem13.value),
        "qr5_gem_abs_44": float(qr5_gem44.value),
        "qr5_out_abs_13": float(qr5_out13.value),
        "qr5_out_abs_44": float(qr5_out44.value),
        "qr5_hpre_abs_13": float(qr5_hpre13.value),
        "qr5_hpre_abs_44": float(qr5_hpre44.value),
        "qr5_hpost_abs_13": float(qr5_hpost13.value),
        "qr5_hpost_abs_44": float(qr5_hpost44.value),
        "qr5_zpre_abs_13": float(qr5_zpre13.value),
        "qr5_zpre_abs_44": float(qr5_zpre44.value),
        "qr5_z140_first_m": int(qr5_z140_first_m.value),
        "qr5_z140_first_13_m": int(qr5_z140_first_13_m.value),
        "qr5_z140_last_m": int(qr5_z140_last_m.value),
        "qr5_z140_steps": int(qr5_z140_steps.value),
        "qr5_z140_first_abs_13": float(qr5_z140_first_abs_13.value),
        "qr5_z140_first_abs_44": float(qr5_z140_first_abs_44.value),
        "qr5_z140_strict_13_m": int(qr5_z140_strict_13_m.value),
        "qr5_z140_strict_abs_13": float(qr5_z140_strict_abs_13.value),
        "qr5_z140_strict_abs_44": float(qr5_z140_strict_abs_44.value),
        "qr5_z140_last_abs_13": float(qr5_z140_last_abs_13.value),
        "qr5_z140_last_abs_44": float(qr5_z140_last_abs_44.value),
        "qr5_z140_iters": int(qr5_z140_iters.value),
        "qr5_m5_k": int(qr5_m5_k.value),
        "qr5_m5_hit": int(qr5_m5_hit.value),
        "qr5_m5_v1": float(qr5_m5_v1.value),
        "qr5_m5_v2": float(qr5_m5_v2.value),
        "qr5_m5_v3": float(qr5_m5_v3.value),
        "qr5_m5_pre13": float(qr5_m5_pre13.value),
        "qr5_m5_pre44": float(qr5_m5_pre44.value),
        "qr5_m5_z13k": float(qr5_m5_z13k.value),
        "qr5_m5_z13k1": float(qr5_m5_z13k1.value),
        "qr5_m5_z13k2": float(qr5_m5_z13k2.value),
        "qr5_m5_z44k": float(qr5_m5_z44k.value),
        "qr5_m5_z44k1": float(qr5_m5_z44k1.value),
        "qr5_m5_z44k2": float(qr5_m5_z44k2.value),
        "qr5_chain_145": int(qr5_chain_145.value),
        "qr5_strict_145": int(qr5_strict_145.value),
        "qr5_chain_mbot": int(qr5_chain_mbot.value),
        "qr5_chain_mtop": int(qr5_chain_mtop.value),
        "qr5_chain_krcol": int(qr5_chain_krcol.value),
        "qr5_chain_firstm": int(qr5_chain_firstm.value),
        "qr5_chain_zpre13": float(qr5_chain_zpre13.value),
        "qr5_chain_zpre44": float(qr5_chain_zpre44.value),
        "qr5_chain_dir13": float(qr5_chain_dir13.value),
        "qr5_chain_dir44": float(qr5_chain_dir44.value),
        "qr5_first_m1_145": int(qr5_first_m1_145.value),
        "qr5_last_m1_145": int(qr5_last_m1_145.value),
        "qr5_tail_first_m1_145": int(qr5_tail_first_m1_145.value),
    }


def dtrevc3_debug_get_qr0_sweep_table(*, max_n: int = 48) -> dict[str, object]:
    """Per-sweep ``DLAQR0`` row **13/44** history (E2i-m instrument)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep_table"):
        raise RuntimeError(
            "DTREVC3 QR0 sweep-table API not in vendored DLL; rebuild fork"
        )
    cap = int(max_n)
    count = ctypes.c_int(0)
    maxn = ctypes.c_int(cap)
    first13gt44 = ctypes.c_int(0)
    last13gt44 = ctypes.c_int(0)
    first44gt13 = ctypes.c_int(0)
    last44gt13 = ctypes.c_int(0)
    routes = (ctypes.c_int * cap)()
    its = (ctypes.c_int * cap)()
    s13 = (ctypes.c_double * cap)()
    s44 = (ctypes.c_double * cap)()
    lib.rgms_dtrevc3_debug_get_qr0_sweep_table(
        ctypes.byref(count),
        ctypes.byref(maxn),
        ctypes.byref(first13gt44),
        ctypes.byref(last13gt44),
        ctypes.byref(first44gt13),
        ctypes.byref(last44gt13),
        routes,
        its,
        s13,
        s44,
    )
    n = int(count.value)
    rows: list[dict[str, float | int | str]] = []
    for i in range(n):
        route = int(routes[i])
        rows.append(
            {
                "sweep": i + 1,
                "route": route,
                "route_name": (
                    "dlaqr3" if route == 3 else "dlaqr5" if route == 5 else "unknown"
                ),
                "it": int(its[i]),
                "abs_13": float(s13[i]),
                "abs_44": float(s44[i]),
                "leader_0based": _sweep_leader(float(s13[i]), float(s44[i])),
            }
        )
    return {
        "count": n,
        "first_13gt44_sweep": int(first13gt44.value),
        "last_13gt44_sweep": int(last13gt44.value),
        "first_44gt13_sweep": int(first44gt13.value),
        "last_44gt13_sweep": int(last44gt13.value),
        "rows": rows,
    }


def dtrevc3_debug_get_qr0_sweep37_boundary() -> dict[str, float | int]:
    """Latch pre/post row **13/44** around sweep **37** (`DLAQR3`, `IT=29`)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep37_boundary"):
        raise RuntimeError(
            "DTREVC3 sweep37 boundary API not in vendored DLL; rebuild fork"
        )
    hit = ctypes.c_int(0)
    itloop = ctypes.c_int(0)
    ldval = ctypes.c_int(0)
    pre13 = ctypes.c_double(0.0)
    pre44 = ctypes.c_double(0.0)
    post13 = ctypes.c_double(0.0)
    post44 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr0_sweep37_boundary(
        ctypes.byref(hit),
        ctypes.byref(itloop),
        ctypes.byref(ldval),
        ctypes.byref(pre13),
        ctypes.byref(pre44),
        ctypes.byref(post13),
        ctypes.byref(post44),
    )
    return {
        "hit": int(hit.value),
        "it": int(itloop.value),
        "ld": int(ldval.value),
        "pre_abs_13": float(pre13.value),
        "pre_abs_44": float(pre44.value),
        "post_abs_13": float(post13.value),
        "post_abs_44": float(post44.value),
    }


def dtrevc3_debug_get_qr0_sweep7_boundary() -> dict[str, float | int]:
    """Signed row **13/44** plate pre/post sweep **7** (`DLAQR3`, `IT=5`)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep7_boundary"):
        raise RuntimeError(
            "DTREVC3 sweep7 boundary API not in vendored DLL; rebuild fork"
        )
    hit = ctypes.c_int(0)
    itloop = ctypes.c_int(0)
    ldval = ctypes.c_int(0)
    qrs_at_pre = ctypes.c_int(0)
    pre_z13k = ctypes.c_double(0.0)
    pre_z44k = ctypes.c_double(0.0)
    pre_z13kp1 = ctypes.c_double(0.0)
    pre_z44kp1 = ctypes.c_double(0.0)
    post_z13k = ctypes.c_double(0.0)
    post_z44k = ctypes.c_double(0.0)
    post_z13kp1 = ctypes.c_double(0.0)
    post_z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr0_sweep7_boundary(
        ctypes.byref(hit),
        ctypes.byref(itloop),
        ctypes.byref(ldval),
        ctypes.byref(qrs_at_pre),
        ctypes.byref(pre_z13k),
        ctypes.byref(pre_z44k),
        ctypes.byref(pre_z13kp1),
        ctypes.byref(pre_z44kp1),
        ctypes.byref(post_z13k),
        ctypes.byref(post_z44k),
        ctypes.byref(post_z13kp1),
        ctypes.byref(post_z44kp1),
    )
    return {
        "hit": int(hit.value),
        "it": int(itloop.value),
        "ld": int(ldval.value),
        "qrsweep_at_pre": int(qrs_at_pre.value),
        "pre_z13_k": float(pre_z13k.value),
        "pre_z44_k": float(pre_z44k.value),
        "pre_z13_kp1": float(pre_z13kp1.value),
        "pre_z44_kp1": float(pre_z44kp1.value),
        "post_z13_k": float(post_z13k.value),
        "post_z44_k": float(post_z44k.value),
        "post_z13_kp1": float(post_z13kp1.value),
        "post_z44_kp1": float(post_z44kp1.value),
        "pre_kp1_delta": float(pre_z13kp1.value) - float(pre_z44kp1.value),
        "post_kp1_delta": float(post_z13kp1.value) - float(post_z44kp1.value),
    }


def dtrevc3_debug_get_qr0_sweep6_post_dlaqr5() -> dict[str, float | int]:
    """Signed row **13/44** plate in ``dlaqr0`` right after sweep **6** ``DLAQR5``."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep6_post_dlaqr5"):
        raise RuntimeError(
            "DTREVC3 sweep6 post-DLAQR5 API not in vendored DLL; rebuild fork"
        )
    hit = ctypes.c_int(0)
    itloop = ctypes.c_int(0)
    qrs_at_post = ctypes.c_int(0)
    z13k = ctypes.c_double(0.0)
    z44k = ctypes.c_double(0.0)
    z13kp1 = ctypes.c_double(0.0)
    z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr0_sweep6_post_dlaqr5(
        ctypes.byref(hit),
        ctypes.byref(itloop),
        ctypes.byref(qrs_at_post),
        ctypes.byref(z13k),
        ctypes.byref(z44k),
        ctypes.byref(z13kp1),
        ctypes.byref(z44kp1),
    )
    return {
        "hit": int(hit.value),
        "it": int(itloop.value),
        "qrsweep_at_post": int(qrs_at_post.value),
        "dlaqr0_sweep": 6,
        "z13_k": float(z13k.value),
        "z44_k": float(z44k.value),
        "z13_kp1": float(z13kp1.value),
        "z44_kp1": float(z44kp1.value),
        "k_delta": float(z13k.value) - float(z44k.value),
        "kp1_delta": float(z13kp1.value) - float(z44kp1.value),
    }


def dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5() -> dict[str, float | int]:
    """Signed row **13/44** plate in ``dlaqr0`` immediately before sweep **8** ``DLAQR5``."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5"):
        raise RuntimeError(
            "DTREVC3 sweep8 pre-DLAQR5 API not in vendored DLL; rebuild fork"
        )
    hit = ctypes.c_int(0)
    itloop = ctypes.c_int(0)
    qrs_at_pre = ctypes.c_int(0)
    z13k = ctypes.c_double(0.0)
    z44k = ctypes.c_double(0.0)
    z13kp1 = ctypes.c_double(0.0)
    z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr0_sweep8_pre_dlaqr5(
        ctypes.byref(hit),
        ctypes.byref(itloop),
        ctypes.byref(qrs_at_pre),
        ctypes.byref(z13k),
        ctypes.byref(z44k),
        ctypes.byref(z13kp1),
        ctypes.byref(z44kp1),
    )
    return {
        "hit": int(hit.value),
        "it": int(itloop.value),
        "qrsweep_at_pre": int(qrs_at_pre.value),
        "dlaqr0_sweep": 8,
        "z13_k": float(z13k.value),
        "z44_k": float(z44k.value),
        "z13_kp1": float(z13kp1.value),
        "z44_kp1": float(z44kp1.value),
        "k_delta": float(z13k.value) - float(z44k.value),
        "kp1_delta": float(z13kp1.value) - float(z44kp1.value),
    }


def dtrevc3_debug_get_qr5_plate_trace() -> dict[str, Any]:
    """Signed row **13/44** plates at ``DLAQR5`` entry for ``QRSWEEP`` 3/5/7."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_plate_trace"):
        raise RuntimeError(
            "DTREVC3 qr5 plate trace API not in vendored DLL; rebuild fork"
        )
    hit1 = ctypes.c_int(0)
    hit2 = ctypes.c_int(0)
    hit3 = ctypes.c_int(0)
    pl3z13k = ctypes.c_double(0.0)
    pl3z44k = ctypes.c_double(0.0)
    pl3z13kp1 = ctypes.c_double(0.0)
    pl3z44kp1 = ctypes.c_double(0.0)
    pl5z13k = ctypes.c_double(0.0)
    pl5z44k = ctypes.c_double(0.0)
    pl5z13kp1 = ctypes.c_double(0.0)
    pl5z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_plate_trace(
        ctypes.byref(hit1),
        ctypes.byref(hit2),
        ctypes.byref(hit3),
        ctypes.byref(pl3z13k),
        ctypes.byref(pl3z44k),
        ctypes.byref(pl3z13kp1),
        ctypes.byref(pl3z44kp1),
        ctypes.byref(pl5z13k),
        ctypes.byref(pl5z44k),
        ctypes.byref(pl5z13kp1),
        ctypes.byref(pl5z44kp1),
    )

    def _slot(
        hit: int,
        qrsweep: int,
        dlaqr0_sweep: int,
        z13k: float,
        z44k: float,
        z13kp1: float,
        z44kp1: float,
    ) -> dict[str, Any]:
        return {
            "hit": int(hit),
            "qrsweep": qrsweep,
            "dlaqr0_sweep": dlaqr0_sweep,
            "z13_k": float(z13k),
            "z44_k": float(z44k),
            "z13_kp1": float(z13kp1),
            "z44_kp1": float(z44kp1),
            "k_delta": float(z13k) - float(z44k),
            "kp1_delta": float(z13kp1) - float(z44kp1),
        }

    return {
        "sweep4_dlaqr5_entry": _slot(
            hit1.value, 3, 4, pl3z13k.value, pl3z44k.value, pl3z13kp1.value, pl3z44kp1.value
        ),
        "sweep6_dlaqr5_entry": _slot(
            hit2.value, 5, 6, pl5z13k.value, pl5z44k.value, pl5z13kp1.value, pl5z44kp1.value
        ),
        "sweep8_dlaqr5_entry": {
            "hit": int(hit3.value),
            "qrsweep": 7,
            "dlaqr0_sweep": 8,
            "note": "full plate via dtrevc3_debug_get_qr5_in_plate",
        },
    }


def dtrevc3_debug_get_qr5_out5_plate() -> dict[str, float | int]:
    """Signed row **13/44** plate at sweep **6** ``DLAQR5`` exit (``QRSWEEP=5``)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_out5_plate"):
        raise RuntimeError(
            "DTREVC3 qr5_out5 plate API not in vendored DLL; rebuild fork"
        )
    hit = ctypes.c_int(0)
    z13k = ctypes.c_double(0.0)
    z44k = ctypes.c_double(0.0)
    z13kp1 = ctypes.c_double(0.0)
    z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_out5_plate(
        ctypes.byref(hit),
        ctypes.byref(z13k),
        ctypes.byref(z44k),
        ctypes.byref(z13kp1),
        ctypes.byref(z44kp1),
    )
    return {
        "hit": int(hit.value),
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "z13_k": float(z13k.value),
        "z44_k": float(z44k.value),
        "z13_kp1": float(z13kp1.value),
        "z44_kp1": float(z44kp1.value),
        "k_delta": float(z13k.value) - float(z44k.value),
        "kp1_delta": float(z13kp1.value) - float(z44kp1.value),
    }


def _plate_slot(
    z13k: float, z44k: float, z13kp1: float, z44kp1: float
) -> dict[str, float | int]:
    return {
        "z13_k": float(z13k),
        "z44_k": float(z44k),
        "z13_kp1": float(z13kp1),
        "z44_kp1": float(z44kp1),
        "k_delta": float(z13k) - float(z44k),
        "kp1_delta": float(z13kp1) - float(z44kp1),
    }


def dtrevc3_debug_get_qr5_s5_intra_trace() -> dict[str, Any]:
    """Intra sweep-6 ``DLAQR5`` (``QRSWEEP=5``) stage plates for row **13/44**."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_intra_trace"):
        raise RuntimeError(
            "DTREVC3 qr5_s5 intra trace API not in vendored DLL; rebuild fork"
        )
    zprehit = ctypes.c_int(0)
    dirhit = ctypes.c_int(0)
    gemhit = ctypes.c_int(0)
    outhit = ctypes.c_int(0)
    fashit = ctypes.c_int(0)
    fastage = ctypes.c_int(0)
    zpreiters = ctypes.c_int(0)
    kacc22 = ctypes.c_int(0)
    z140steps = ctypes.c_int(0)
    z140iters = ctypes.c_int(0)
    zprez13k = ctypes.c_double(0.0)
    zprez44k = ctypes.c_double(0.0)
    zprez13kp1 = ctypes.c_double(0.0)
    zprez44kp1 = ctypes.c_double(0.0)
    dirz13k = ctypes.c_double(0.0)
    dirz44k = ctypes.c_double(0.0)
    dirz13kp1 = ctypes.c_double(0.0)
    dirz44kp1 = ctypes.c_double(0.0)
    gemz13k = ctypes.c_double(0.0)
    gemz44k = ctypes.c_double(0.0)
    gemz13kp1 = ctypes.c_double(0.0)
    gemz44kp1 = ctypes.c_double(0.0)
    outz13k = ctypes.c_double(0.0)
    outz44k = ctypes.c_double(0.0)
    outz13kp1 = ctypes.c_double(0.0)
    outz44kp1 = ctypes.c_double(0.0)
    fasz13k = ctypes.c_double(0.0)
    fasz44k = ctypes.c_double(0.0)
    fasz13kp1 = ctypes.c_double(0.0)
    fasz44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_s5_intra_trace(
        ctypes.byref(zprehit),
        ctypes.byref(dirhit),
        ctypes.byref(gemhit),
        ctypes.byref(outhit),
        ctypes.byref(fashit),
        ctypes.byref(fastage),
        ctypes.byref(zpreiters),
        ctypes.byref(kacc22),
        ctypes.byref(z140steps),
        ctypes.byref(z140iters),
        ctypes.byref(zprez13k),
        ctypes.byref(zprez44k),
        ctypes.byref(zprez13kp1),
        ctypes.byref(zprez44kp1),
        ctypes.byref(dirz13k),
        ctypes.byref(dirz44k),
        ctypes.byref(dirz13kp1),
        ctypes.byref(dirz44kp1),
        ctypes.byref(gemz13k),
        ctypes.byref(gemz44k),
        ctypes.byref(gemz13kp1),
        ctypes.byref(gemz44kp1),
        ctypes.byref(outz13k),
        ctypes.byref(outz44k),
        ctypes.byref(outz13kp1),
        ctypes.byref(outz44kp1),
        ctypes.byref(fasz13k),
        ctypes.byref(fasz44k),
        ctypes.byref(fasz13kp1),
        ctypes.byref(fasz44kp1),
    )
    return {
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_hit": int(zprehit.value),
        "dir_hit": int(dirhit.value),
        "gem_hit": int(gemhit.value),
        "out_hit": int(outhit.value),
        "fas_hit": int(fashit.value),
        "fas_stage": int(fastage.value),
        "zpre_iters": int(zpreiters.value),
        "kacc22": int(kacc22.value),
        "z140_steps": int(z140steps.value),
        "z140_iters": int(z140iters.value),
        "zpre": _plate_slot(
            zprez13k.value, zprez44k.value, zprez13kp1.value, zprez44kp1.value
        ),
        "dir": _plate_slot(
            dirz13k.value, dirz44k.value, dirz13kp1.value, dirz44kp1.value
        ),
        "gem": _plate_slot(
            gemz13k.value, gemz44k.value, gemz13kp1.value, gemz44kp1.value
        ),
        "out": _plate_slot(
            outz13k.value, outz44k.value, outz13kp1.value, outz44kp1.value
        ),
        "fas": _plate_slot(
            fasz13k.value, fasz44k.value, fasz13kp1.value, fasz44kp1.value
        ),
    }


def dtrevc3_debug_get_qr5_s5_zpre_subtrace() -> dict[str, Any]:
    """First / first-asymmetric / last ``zpre`` plates inside sweep-6 ``DLAQR5``."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_zpre_subtrace"):
        raise RuntimeError(
            "DTREVC3 qr5_s5 zpre subtrace API not in vendored DLL; rebuild fork"
        )
    zp1hit = ctypes.c_int(0)
    zpahit = ctypes.c_int(0)
    zpaiter = ctypes.c_int(0)
    zpreiters = ctypes.c_int(0)
    zp1z13k = ctypes.c_double(0.0)
    zp1z44k = ctypes.c_double(0.0)
    zp1z13kp1 = ctypes.c_double(0.0)
    zp1z44kp1 = ctypes.c_double(0.0)
    zpaz13k = ctypes.c_double(0.0)
    zpaz44k = ctypes.c_double(0.0)
    zpaz13kp1 = ctypes.c_double(0.0)
    zpaz44kp1 = ctypes.c_double(0.0)
    zlastz13k = ctypes.c_double(0.0)
    zlastz44k = ctypes.c_double(0.0)
    zlastz13kp1 = ctypes.c_double(0.0)
    zlastz44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_s5_zpre_subtrace(
        ctypes.byref(zp1hit),
        ctypes.byref(zpahit),
        ctypes.byref(zpaiter),
        ctypes.byref(zpreiters),
        ctypes.byref(zp1z13k),
        ctypes.byref(zp1z44k),
        ctypes.byref(zp1z13kp1),
        ctypes.byref(zp1z44kp1),
        ctypes.byref(zpaz13k),
        ctypes.byref(zpaz44k),
        ctypes.byref(zpaz13kp1),
        ctypes.byref(zpaz44kp1),
        ctypes.byref(zlastz13k),
        ctypes.byref(zlastz44k),
        ctypes.byref(zlastz13kp1),
        ctypes.byref(zlastz44kp1),
    )
    return {
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zp1_hit": int(zp1hit.value),
        "zpa_hit": int(zpahit.value),
        "zpa_iter": int(zpaiter.value),
        "zpre_iters": int(zpreiters.value),
        "zp1": _plate_slot(
            zp1z13k.value, zp1z44k.value, zp1z13kp1.value, zp1z44kp1.value
        ),
        "zpa": _plate_slot(
            zpaz13k.value, zpaz44k.value, zpaz13kp1.value, zpaz44kp1.value
        ),
        "zlast": _plate_slot(
            zlastz13k.value, zlastz44k.value, zlastz13kp1.value, zlastz44kp1.value
        ),
    }


def dtrevc3_debug_get_qr5_s5_z1_do140() -> dict[str, Any]:
    """Per-**M** signed plates from ``DO140`` during first ``zpre`` iter (sweep 6)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_z1_do140"):
        raise RuntimeError(
            "DTREVC3 qr5_s5 z1 DO140 API not in vendored DLL; rebuild fork"
        )
    m5hit = ctypes.c_int(0)
    m4hit = ctypes.c_int(0)
    m3hit = ctypes.c_int(0)
    m2hit = ctypes.c_int(0)
    m1hit = ctypes.c_int(0)
    fasmm = ctypes.c_int(0)
    steps = ctypes.c_int(0)
    m5z13k = ctypes.c_double(0.0)
    m5z44k = ctypes.c_double(0.0)
    m5z13kp1 = ctypes.c_double(0.0)
    m5z44kp1 = ctypes.c_double(0.0)
    m4z13k = ctypes.c_double(0.0)
    m4z44k = ctypes.c_double(0.0)
    m4z13kp1 = ctypes.c_double(0.0)
    m4z44kp1 = ctypes.c_double(0.0)
    m3z13k = ctypes.c_double(0.0)
    m3z44k = ctypes.c_double(0.0)
    m3z13kp1 = ctypes.c_double(0.0)
    m3z44kp1 = ctypes.c_double(0.0)
    m2z13k = ctypes.c_double(0.0)
    m2z44k = ctypes.c_double(0.0)
    m2z13kp1 = ctypes.c_double(0.0)
    m2z44kp1 = ctypes.c_double(0.0)
    m1z13k = ctypes.c_double(0.0)
    m1z44k = ctypes.c_double(0.0)
    m1z13kp1 = ctypes.c_double(0.0)
    m1z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_s5_z1_do140(
        ctypes.byref(m5hit),
        ctypes.byref(m4hit),
        ctypes.byref(m3hit),
        ctypes.byref(m2hit),
        ctypes.byref(m1hit),
        ctypes.byref(fasmm),
        ctypes.byref(steps),
        ctypes.byref(m5z13k),
        ctypes.byref(m5z44k),
        ctypes.byref(m5z13kp1),
        ctypes.byref(m5z44kp1),
        ctypes.byref(m4z13k),
        ctypes.byref(m4z44k),
        ctypes.byref(m4z13kp1),
        ctypes.byref(m4z44kp1),
        ctypes.byref(m3z13k),
        ctypes.byref(m3z44k),
        ctypes.byref(m3z13kp1),
        ctypes.byref(m3z44kp1),
        ctypes.byref(m2z13k),
        ctypes.byref(m2z44k),
        ctypes.byref(m2z13kp1),
        ctypes.byref(m2z44kp1),
        ctypes.byref(m1z13k),
        ctypes.byref(m1z44k),
        ctypes.byref(m1z13kp1),
        ctypes.byref(m1z44kp1),
    )

    def _m_slot(
        hit: int, z13k: float, z44k: float, z13kp1: float, z44kp1: float
    ) -> dict[str, float | int]:
        return {
            "hit": int(hit),
            "plate": _plate_slot(z13k, z44k, z13kp1, z44kp1),
        }

    return {
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_iter": 1,
        "do140_steps": int(steps.value),
        "first_asym_m": int(fasmm.value),
        "m5": _m_slot(m5hit.value, m5z13k.value, m5z44k.value, m5z13kp1.value, m5z44kp1.value),
        "m4": _m_slot(m4hit.value, m4z13k.value, m4z44k.value, m4z13kp1.value, m4z44kp1.value),
        "m3": _m_slot(m3hit.value, m3z13k.value, m3z44k.value, m3z13kp1.value, m3z44kp1.value),
        "m2": _m_slot(m2hit.value, m2z13k.value, m2z44k.value, m2z13kp1.value, m2z44kp1.value),
        "m1": _m_slot(m1hit.value, m1z13k.value, m1z44k.value, m1z13kp1.value, m1z44kp1.value),
    }


def dtrevc3_debug_get_qr5_s5_z1_gap() -> dict[str, Any]:
    """Post-``DO140`` / first-``dir`` plates during first ``zpre`` iter (sweep 6)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_z1_gap"):
        raise RuntimeError(
            "DTREVC3 qr5_s5 z1 gap API not in vendored DLL; rebuild fork"
        )
    posthit = ctypes.c_int(0)
    d1hit = ctypes.c_int(0)
    postz13k = ctypes.c_double(0.0)
    postz44k = ctypes.c_double(0.0)
    postz13kp1 = ctypes.c_double(0.0)
    postz44kp1 = ctypes.c_double(0.0)
    d1z13k = ctypes.c_double(0.0)
    d1z44k = ctypes.c_double(0.0)
    d1z13kp1 = ctypes.c_double(0.0)
    d1z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_s5_z1_gap(
        ctypes.byref(posthit),
        ctypes.byref(postz13k),
        ctypes.byref(postz44k),
        ctypes.byref(postz13kp1),
        ctypes.byref(postz44kp1),
        ctypes.byref(d1hit),
        ctypes.byref(d1z13k),
        ctypes.byref(d1z44k),
        ctypes.byref(d1z13kp1),
        ctypes.byref(d1z44kp1),
    )
    return {
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "zpre_iter": 1,
        "post_do140": {
            "hit": int(posthit.value),
            "plate": _plate_slot(
                postz13k.value, postz44k.value, postz13kp1.value, postz44kp1.value
            ),
        },
        "z1_dir1": {
            "hit": int(d1hit.value),
            "plate": _plate_slot(
                d1z13k.value, d1z44k.value, d1z13kp1.value, d1z44kp1.value
            ),
        },
    }


def dtrevc3_debug_get_qr5_s5_z145_pre_zp1() -> dict[str, Any]:
    """``DO 41`` / pre-``zp1`` plates before first stage-**5** snap (sweep 6)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_z145_pre_zp1"):
        raise RuntimeError(
            "DTREVC3 qr5_s5 z145 pre-zp1 API not in vendored DLL; rebuild fork"
        )
    z41hit = ctypes.c_int(0)
    z41steps = ctypes.c_int(0)
    z41fahit = ctypes.c_int(0)
    z41faskrcol = ctypes.c_int(0)
    z41fask = ctypes.c_int(0)
    z41fasm = ctypes.c_int(0)
    z41lshit = ctypes.c_int(0)
    prezp1hit = ctypes.c_int(0)
    prezp1krcol = ctypes.c_int(0)
    z41faz13k = ctypes.c_double(0.0)
    z41faz44k = ctypes.c_double(0.0)
    z41faz13kp1 = ctypes.c_double(0.0)
    z41faz44kp1 = ctypes.c_double(0.0)
    z41lsz13k = ctypes.c_double(0.0)
    z41lsz44k = ctypes.c_double(0.0)
    z41lsz13kp1 = ctypes.c_double(0.0)
    z41lsz44kp1 = ctypes.c_double(0.0)
    prezp1z13k = ctypes.c_double(0.0)
    prezp1z44k = ctypes.c_double(0.0)
    prezp1z13kp1 = ctypes.c_double(0.0)
    prezp1z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_s5_z145_pre_zp1(
        ctypes.byref(z41hit),
        ctypes.byref(z41steps),
        ctypes.byref(z41fahit),
        ctypes.byref(z41faskrcol),
        ctypes.byref(z41fask),
        ctypes.byref(z41fasm),
        ctypes.byref(z41lshit),
        ctypes.byref(prezp1hit),
        ctypes.byref(prezp1krcol),
        ctypes.byref(z41faz13k),
        ctypes.byref(z41faz44k),
        ctypes.byref(z41faz13kp1),
        ctypes.byref(z41faz44kp1),
        ctypes.byref(z41lsz13k),
        ctypes.byref(z41lsz44k),
        ctypes.byref(z41lsz13kp1),
        ctypes.byref(z41lsz44kp1),
        ctypes.byref(prezp1z13k),
        ctypes.byref(prezp1z44k),
        ctypes.byref(prezp1z13kp1),
        ctypes.byref(prezp1z44kp1),
    )
    return {
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "z41_hit": int(z41hit.value),
        "z41_steps": int(z41steps.value),
        "z41_first_asym": {
            "hit": int(z41fahit.value),
            "krcol": int(z41faskrcol.value) if int(z41fahit.value) else 0,
            "k": int(z41fask.value) if int(z41fahit.value) else 0,
            "m": int(z41fasm.value) if int(z41fahit.value) else 0,
            "plate": _plate_slot(
                z41faz13k.value, z41faz44k.value, z41faz13kp1.value, z41faz44kp1.value
            ),
        },
        "z41_last_sym": {
            "hit": int(z41lshit.value),
            "plate": _plate_slot(
                z41lsz13k.value, z41lsz44k.value, z41lsz13kp1.value, z41lsz44kp1.value
            ),
        },
        "pre_zp1": {
            "hit": int(prezp1hit.value),
            "krcol": int(prezp1krcol.value),
            "plate": _plate_slot(
                prezp1z13k.value, prezp1z44k.value, prezp1z13kp1.value, prezp1z44kp1.value
            ),
        },
    }


def dtrevc3_debug_get_qr5_s5_zp1_boundary() -> dict[str, Any]:
    """Stage-**5** ``pre_zp1`` / inline / ``zp1`` COL+krcol boundary audit (sweep 6)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_s5_zp1_boundary"):
        raise RuntimeError(
            "DTREVC3 qr5_s5 zp1 boundary API not in vendored DLL; rebuild fork"
        )
    dbgcol = ctypes.c_int(0)
    prezp1col = ctypes.c_int(0)
    zp1col = ctypes.c_int(0)
    prezp1krcol = ctypes.c_int(0)
    zp1krcol = ctypes.c_int(0)
    s5inlhit = ctypes.c_int(0)
    s5inchit = ctypes.c_int(0)
    pendit = ctypes.c_int(0)
    scopeit = ctypes.c_int(0)
    s5inlit = ctypes.c_int(0)
    s5incit = ctypes.c_int(0)
    zp1it = ctypes.c_int(0)
    prezp1z13k = ctypes.c_double(0.0)
    prezp1z44k = ctypes.c_double(0.0)
    prezp1z13kp1 = ctypes.c_double(0.0)
    prezp1z44kp1 = ctypes.c_double(0.0)
    s5inlz13k = ctypes.c_double(0.0)
    s5inlz44k = ctypes.c_double(0.0)
    s5inlz13kp1 = ctypes.c_double(0.0)
    s5inlz44kp1 = ctypes.c_double(0.0)
    s5incz13k = ctypes.c_double(0.0)
    s5incz44k = ctypes.c_double(0.0)
    s5incz13kp1 = ctypes.c_double(0.0)
    s5incz44kp1 = ctypes.c_double(0.0)
    zp1z13k = ctypes.c_double(0.0)
    zp1z44k = ctypes.c_double(0.0)
    zp1z13kp1 = ctypes.c_double(0.0)
    zp1z44kp1 = ctypes.c_double(0.0)
    s6commithit = ctypes.c_int(0)
    cmts5inlz13k = ctypes.c_double(0.0)
    cmts5inlz44k = ctypes.c_double(0.0)
    cmts5inlz13kp1 = ctypes.c_double(0.0)
    cmts5inlz44kp1 = ctypes.c_double(0.0)
    cmts5incz13k = ctypes.c_double(0.0)
    cmts5incz44k = ctypes.c_double(0.0)
    cmts5incz13kp1 = ctypes.c_double(0.0)
    cmts5incz44kp1 = ctypes.c_double(0.0)
    cmtzp1z13k = ctypes.c_double(0.0)
    cmtzp1z44k = ctypes.c_double(0.0)
    cmtzp1z13kp1 = ctypes.c_double(0.0)
    cmtzp1z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_s5_zp1_boundary(
        ctypes.byref(dbgcol),
        ctypes.byref(prezp1col),
        ctypes.byref(zp1col),
        ctypes.byref(prezp1krcol),
        ctypes.byref(zp1krcol),
        ctypes.byref(s5inlhit),
        ctypes.byref(s5inchit),
        ctypes.byref(pendit),
        ctypes.byref(scopeit),
        ctypes.byref(s5inlit),
        ctypes.byref(s5incit),
        ctypes.byref(zp1it),
        ctypes.byref(s6commithit),
        ctypes.byref(prezp1z13k),
        ctypes.byref(prezp1z44k),
        ctypes.byref(prezp1z13kp1),
        ctypes.byref(prezp1z44kp1),
        ctypes.byref(s5inlz13k),
        ctypes.byref(s5inlz44k),
        ctypes.byref(s5inlz13kp1),
        ctypes.byref(s5inlz44kp1),
        ctypes.byref(s5incz13k),
        ctypes.byref(s5incz44k),
        ctypes.byref(s5incz13kp1),
        ctypes.byref(s5incz44kp1),
        ctypes.byref(zp1z13k),
        ctypes.byref(zp1z44k),
        ctypes.byref(zp1z13kp1),
        ctypes.byref(zp1z44kp1),
        ctypes.byref(cmts5inlz13k),
        ctypes.byref(cmts5inlz44k),
        ctypes.byref(cmts5inlz13kp1),
        ctypes.byref(cmts5inlz44kp1),
        ctypes.byref(cmts5incz13k),
        ctypes.byref(cmts5incz44k),
        ctypes.byref(cmts5incz13kp1),
        ctypes.byref(cmts5incz44kp1),
        ctypes.byref(cmtzp1z13k),
        ctypes.byref(cmtzp1z44k),
        ctypes.byref(cmtzp1z13kp1),
        ctypes.byref(cmtzp1z44kp1),
    )
    zp1_slot = _plate_slot(
        zp1z13k.value, zp1z44k.value, zp1z13kp1.value, zp1z44kp1.value
    )
    commit_zp1_slot = _plate_slot(
        cmtzp1z13k.value, cmtzp1z44k.value, cmtzp1z13kp1.value, cmtzp1z44kp1.value
    )
    # ``S6COMMITHIT`` COMMON export is unreliable via ctypes; commit CMD latches
    # on the same first-``zp1`` capture as ``s5inc_hit``.
    s6_hit = int(s6commithit.value)
    if s6_hit == 0 and int(s5inchit.value) == 1:
        s6_hit = 1
    return {
        "qrsweep": 5,
        "dlaqr0_sweep": 6,
        "dbg_col": int(dbgcol.value),
        "pre_zp1_col": int(prezp1col.value),
        "zp1_col": int(zp1col.value),
        "pre_zp1_krcol": int(prezp1krcol.value),
        "zp1_krcol": int(zp1krcol.value),
        "s5inl_hit": int(s5inlhit.value),
        "s5inc_hit": int(s5inchit.value),
        "pend_it": int(pendit.value),
        "scope_it": int(scopeit.value),
        "s5inl_it": int(s5inlit.value),
        "s5inc_it": int(s5incit.value),
        "zp1_it": int(zp1it.value),
        "pre_zp1": _plate_slot(
            prezp1z13k.value, prezp1z44k.value, prezp1z13kp1.value, prezp1z44kp1.value
        ),
        "s5inl": _plate_slot(
            s5inlz13k.value, s5inlz44k.value, s5inlz13kp1.value, s5inlz44kp1.value
        ),
        "s5inc": _plate_slot(
            s5incz13k.value, s5incz44k.value, s5incz13kp1.value, s5incz44kp1.value
        ),
        "zp1": zp1_slot,
        "s6commit_hit": s6_hit,
        "commit_s5inl": _plate_slot(
            cmts5inlz13k.value,
            cmts5inlz44k.value,
            cmts5inlz13kp1.value,
            cmts5inlz44kp1.value,
        ),
        "commit_s5inc": _plate_slot(
            cmts5incz13k.value,
            cmts5incz44k.value,
            cmts5incz13kp1.value,
            cmts5incz44kp1.value,
        ),
        "commit_zp1": commit_zp1_slot,
        "slot_eq_commit": (
            zp1_slot == commit_zp1_slot if s6_hit == 1 else None
        ),
    }


def dtrevc3_debug_get_qr5_in_plate() -> dict[str, float | int]:
    """Full row **13/44** plate at ``DLAQR5`` sweep-8 entry (``qr5_in``)."""
    lib = _load_lib()
    if not hasattr(lib, "rgms_dtrevc3_debug_get_qr5_in_plate"):
        raise RuntimeError(
            "DTREVC3 qr5_in plate API not in vendored DLL; rebuild fork"
        )
    hit = ctypes.c_int(0)
    z13km1 = ctypes.c_double(0.0)
    z13k = ctypes.c_double(0.0)
    z13kp1 = ctypes.c_double(0.0)
    z44km1 = ctypes.c_double(0.0)
    z44k = ctypes.c_double(0.0)
    z44kp1 = ctypes.c_double(0.0)
    lib.rgms_dtrevc3_debug_get_qr5_in_plate(
        ctypes.byref(hit),
        ctypes.byref(z13km1),
        ctypes.byref(z13k),
        ctypes.byref(z13kp1),
        ctypes.byref(z44km1),
        ctypes.byref(z44k),
        ctypes.byref(z44kp1),
    )
    return {
        "hit": int(hit.value),
        "z13_km1": float(z13km1.value),
        "z13_k": float(z13k.value),
        "z13_kp1": float(z13kp1.value),
        "z44_km1": float(z44km1.value),
        "z44_k": float(z44k.value),
        "z44_kp1": float(z44kp1.value),
    }


def _sweep_leader(a13: float, a44: float) -> int | None:
    tol = 1e-15 * max(abs(a13), abs(a44), 1.0)
    if abs(a13 - a44) <= tol:
        return None
    return 13 if a13 > a44 else 44


def eig_real_nobalance(a: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Real dense ``a`` → ``(w, V)`` via vendored ``dgeevx``, ``balanc='N'``.

    ``A`` is copied; LAPACK overwrites the working matrix. Eigenvectors follow
    LAPACK real/imag column pairing (same convention as ``eig_nobalance`` geevx path).
    """
    lib = _load_lib()
    a_f = np.array(np.asarray(a, dtype=np.float64), order="F", copy=True)
    n = int(a_f.shape[0])
    if a_f.ndim != 2 or a_f.shape[0] != a_f.shape[1]:
        raise ValueError("eig_real_nobalance expects a square 2-D matrix")

    wr = np.zeros(n, dtype=np.float64, order="F")
    wi = np.zeros(n, dtype=np.float64, order="F")
    vr = np.zeros((n, n), dtype=np.float64, order="F")
    n_c = ctypes.c_int(n)
    lda_c = ctypes.c_int(n)
    ldvr_c = ctypes.c_int(n)
    info = ctypes.c_int(0)

    lib.rgms_eig_nobalance_dgeevx(
        ctypes.byref(n_c),
        a_f.ctypes.data_as(ctypes.c_void_p),
        ctypes.byref(lda_c),
        wr.ctypes.data_as(ctypes.c_void_p),
        wi.ctypes.data_as(ctypes.c_void_p),
        vr.ctypes.data_as(ctypes.c_void_p),
        ctypes.byref(ldvr_c),
        ctypes.byref(info),
    )
    if int(info.value) != 0:
        raise RuntimeError(f"vendored DGEEVX failed with info={int(info.value)}")

    w = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = _real_geev_evecs_to_complex(vr, wi)
    return w, v
