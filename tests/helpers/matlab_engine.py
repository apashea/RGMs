from pathlib import Path

import pytest

try:
    import matlab.engine
except ImportError as exc:
    _MATLAB_ENGINE_IMPORT_ERROR = exc
else:
    _MATLAB_ENGINE_IMPORT_ERROR = None


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MATLAB_SRC = _REPO_ROOT / "matlab_src"


@pytest.fixture(scope="session")
def eng():
    if _MATLAB_ENGINE_IMPORT_ERROR is not None:
        raise RuntimeError(
            "MATLAB Engine for Python is required for oracle tests."
        ) from _MATLAB_ENGINE_IMPORT_ERROR

    engine = matlab.engine.start_matlab()
    try:
        engine.addpath(str(_MATLAB_SRC), nargout=0)
        yield engine
    finally:
        engine.quit()
