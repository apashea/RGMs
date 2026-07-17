% dump_MDP_pre_entry11.m
%
% One-time MATLAB authority for FSL backward Entry 11 input (after Entry 10, before Entry 11).
% Same ``rng(2)`` ledger scale as Entry 12 Call 1 ``DEMAtariIII_XXX_12_rdp.mat`` (outer 128, T=10000).
%
% Output: tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry11.mat
%   MDP_pre_entry11 — cell MDP after Entry 10 (post ``spm_RDP_sort``, post ``spm_set_goals``, paths block omitted)
%   C, Ne, Nm, meta
%
% Then (once): python tests/oracle/toolbox/DEM/fsl_backward_materialize_mdp_pre_entry11_pkl.py
%
% See Atari_example.md § FSL backward validation (Entry 11 → 1).

function dump_MDP_pre_entry11()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
demo1_add_matlab_src(repoRoot);
outDir = demo1_fixtures_dir(repoRoot);

rng(2);
fprintf(1, '[FSL backward dump] rng(2) — ledger through Entry 10 (pre-Entry-11 boundary)\n');

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C  = 32;

[GDP, ~, ~, ~, ~] = spm_MDP_pong(Nr, Nc, Nd, true, 0);

S = ones(4, 3);
S(1, :) = [Nr, Nc, 1];
S(2, :) = [1, 1, 1];
S(3, :) = [1, 1, 1];
S(4, :) = [1, 1, 1];

spm_get_hits = @(o, id) find(o(id.reward, :) > 1);
spm_get_miss = @(o, id) find(o(id.contraint, :) > 1);

GDP.tau = 1;
GDP.T   = 10000;
PDP = spm_MDP_generate(GDP);

MDP = spm_faster_structure_learning(PDP.O(:, 1:1000), S, Sc);

Nm = numel(MDP);
Ne = max(2^(Nm - 1), 1);
for n = 1:Nm
    for g = 1:numel(MDP{n}.a)
        MDP{n}.a{g} = [];
    end
    for f = 1:numel(MDP{n}.b)
        MDP{n}.b{f} = [];
    end
end

r = spm_get_hits(PDP.o, GDP.id);
c = spm_get_miss(PDP.o, GDP.id);
for i = 1:numel(r)
    s = c(find(c < r(i), 1, 'last'));
    t = (s + Ne):(r(i) + Ne);
    if numel(t)
        for s = 1:Ne
            MDP = spm_merge_structure_learning(PDP.O(:, t + s), MDP);
        end
    end
end

NT = 100;
for i = 1:128
    q = rem(i, 100 - 1);
    t = (0:(NT + Ne)) + q * NT;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP.O(:, t + s), MDP);
    end
    [MDP, d] = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if all(d)
        break;
    end
end

MDP = spm_RDP_sort(MDP);
MDP_pre_entry11 = spm_set_goals(MDP, [2, 3], [C, -C]);

meta = struct();
meta.capture_script = mfilename;
meta.rng_seed = 2;
meta.GDP_T = GDP.T;
meta.GDP_tau = GDP.tau;
meta.n_outer = 128;
meta.boundary = 'post_entry10_pre_entry11';
meta.timestamp = datestr(now, 31);
meta.matlab_release = version;

outMat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry11.mat');
save(outMat, 'MDP_pre_entry11', 'C', 'Ne', 'Nm', 'meta', '-v7');
fprintf(1, '[FSL backward dump] wrote %s (Nm=%d Ne=%d)\n', outMat, Nm, Ne);
end
