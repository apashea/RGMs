function demo1_add_matlab_src(repoRoot)
%DEMO1_ADD_MATLAB_SRC  Staged SPM + matlab_custom only (no external spm-main).
addpath(genpath(fullfile(repoRoot, 'matlab_src')), '-begin');
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
