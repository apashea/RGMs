import pytest

from python_src.spm_check_version import spm_check_version
from tests.helpers.compare import assert_matlab_match


def test_spm_check_version_default_toolbox_oracle(eng):
    tbx_matlab = eng.spm_check_version()
    tbx_python = spm_check_version()

    assert tbx_matlab == tbx_python


def test_spm_check_version_matlab_version_oracle(eng):
    v_matlab = eng.spm_check_version("matlab")
    v_python = spm_check_version("matlab")

    assert v_matlab == v_python


def test_spm_check_version_status_oracle(eng):
    status_matlab = eng.spm_check_version("matlab", "1")
    status_python = spm_check_version("matlab", "1")

    assert_matlab_match(status_matlab, status_python)


def test_spm_check_version_unknown_toolbox_error_oracle(eng):
    with pytest.raises(Exception):
        eng.spm_check_version("definitely_missing_toolbox_for_oracle")

    with pytest.raises(Exception):
        spm_check_version("definitely_missing_toolbox_for_oracle")


def test_spm_check_version_too_many_fields_error_oracle(eng):
    with pytest.raises(Exception):
        eng.spm_check_version("matlab", "1.2.3.4.5")

    with pytest.raises(Exception):
        spm_check_version("matlab", "1.2.3.4.5")
