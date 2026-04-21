import matlab.engine


def main():
    eng = matlab.engine.start_matlab()
    p = __import__("pathlib").Path(__file__).resolve().parent
    eng.addpath(str(p), nargout=0)
    eng.eval("probe_randperm_floor", nargout=0)
    eng.quit()


if __name__ == "__main__":
    main()
