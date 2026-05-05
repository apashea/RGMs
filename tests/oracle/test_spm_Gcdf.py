"""
Oracle: ``spm_Gcdf`` vs MATLAB Engine (staged ``matlab_src/spm_Gcdf.m`` / SPM path).
"""

import numpy as np
import pytest

from python_src.spm_Gcdf import spm_Gcdf


def test_spm_Gcdf_vector_oracle(eng) -> None:
    x = np.arange(0, 4, 0.5, dtype=np.float64)
    h = np.array(2.0, dtype=np.float64)
    l = np.array(1.0, dtype=np.float64)
    eng.eval(f"rgms_x = {x.tolist()};", nargout=0)
    eng.eval(f"rgms_h = {float(h)}; rgms_l = {float(l)};", nargout=0)
    eng.eval("rgms_F = spm_Gcdf(rgms_x, rgms_h, rgms_l);", nargout=0)
    f_m = np.asarray(eng.eval("rgms_F"), dtype=np.float64).ravel()
    f_py = np.asarray(spm_Gcdf(x, h, l), dtype=np.float64).ravel()
    np.testing.assert_allclose(f_py, f_m, rtol=1e-10, atol=1e-12)


def test_spm_Gcdf_upper_tail_oracle(eng) -> None:
    x = np.array([0.5, 1.0, 1.5], dtype=np.float64)
    h = np.array(3.0, dtype=np.float64)
    l = np.array(0.5, dtype=np.float64)
    eng.eval(f"rgms_x = {x.tolist()};", nargout=0)
    eng.eval(f"rgms_h = {float(h)}; rgms_l = {float(l)};", nargout=0)
    eng.eval("rgms_Fu = spm_Gcdf(rgms_x, rgms_h, rgms_l, 'upper');", nargout=0)
    f_m = np.asarray(eng.eval("rgms_Fu"), dtype=np.float64).ravel()
    f_py = np.asarray(spm_Gcdf(x, h, l, "upper"), dtype=np.float64).ravel()
    np.testing.assert_allclose(f_py, f_m, rtol=1e-10, atol=1e-12)
