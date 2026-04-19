from pathlib import Path


def spm_check_version(tbx=None, chk=None):
    eng = _matlab_engine()

    if tbx is None and chk is None:
        return eng.spm_check_version()
    if chk is None:
        return eng.spm_check_version(tbx)
    return eng.spm_check_version(tbx, chk)


_ENGINE = None


def _matlab_engine():
    global _ENGINE
    if _ENGINE is None:
        import matlab.engine

        _ENGINE = matlab.engine.start_matlab()
        matlab_src = Path(__file__).resolve().parents[1] / "matlab_src"
        _ENGINE.addpath(str(matlab_src), "-begin", nargout=0)
    return _ENGINE
