import numpy as np
import matlab.engine


def main():
    eng = matlab.engine.start_matlab()
    eng.eval("rng(0,'twister');", nargout=0)
    r0 = float(np.asarray(eng.eval("rand()")).squeeze())
    eng.eval("rng(0,'twister');", nargout=0)
    eng.eval("rp = randperm(10,1);", nargout=0)
    r_after_rp = float(np.asarray(eng.eval("rand()")).squeeze())
    eng.eval("rng(0,'twister');", nargout=0)
    eng.eval("x = rand(1,1);", nargout=0)
    r_second = float(np.asarray(eng.eval("rand()")).squeeze())
    print("first rand", r0)
    print("rand after randperm(10,1)", r_after_rp)
    print("second rand after rng(0) x2", r_second)

    eng.eval("rng(0,'twister'); rp = randperm(10,1);", nargout=0)
    rp = int(np.asarray(eng.eval("rp")).squeeze())
    eng.eval("rng(0,'twister'); r1 = rand(); j = floor(10*r1) + 1;", nargout=0)
    j_floor = int(np.asarray(eng.eval("j")).squeeze())

    eng.eval("rng(0,'twister'); r1 = rand(); j2 = ceil(10*r1);", nargout=0)
    j_ceil = int(np.asarray(eng.eval("j2")).squeeze())

    print("randperm(10,1)", rp, "floor(10*r)+1", j_floor, "ceil(10*r)", j_ceil)
    eng.quit()


if __name__ == "__main__":
    main()
