% dump_MDP_pre_call3_post_nr.m
%
% DEMO2 lane B authority — ``MDP`` after full active-inference NR loop, before call 3
% ``spm_RDP_sort`` (~``DEM_AtariIII.m`` lines 254--325 then 330).
%
% Output: tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_demo2_MDP_pre_call3_post_nr.mat
%   MDP_pre_post_nr — cell MDP after NR=32 loop (GDP attached)
%   GDP, C, Ne, Nm, NT, NR, NS, meta
%
% Same ``rng(2)`` ledger scale as DEMO1 / Entry 12 (T=10000, outer 128 basin loop).
%
%   matlab -batch "cd('...\matlab_custom\demo2'); dump_MDP_pre_call3_post_nr;"

function dump_MDP_pre_call3_post_nr()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
fslDir = fullfile(repoRoot, 'matlab_custom', 'fsl_backward');
entry12Dir = fullfile(repoRoot, 'matlab_custom', 'entry12');
demDir = fullfile(repoRoot, 'matlab_src', 'toolbox', 'DEM');
addpath(genpath(fullfile(repoRoot, 'matlab_src')), '-begin');
addpath(demDir, '-begin');
addpath(fslDir, '-begin');
addpath(entry12Dir, '-begin');
addpath(thisDir, '-begin');

outDir = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

rng(2);
fprintf(1, '[DEMO2 dump] rng(2) — ledger through NR loop (pre call 3)\n');

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C  = 32;
NT = 256;
NR = 32;
NS = 256;

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

NTbasin = 100;
for i = 1:128
    q = rem(i, 100 - 1);
    t = (0:(NTbasin + Ne)) + q * NTbasin;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP.O(:, t + s), MDP);
    end
    [MDP, d] = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if all(d)
        break;
    end
end

MDP = spm_RDP_sort(MDP);
MDP = spm_set_goals(MDP, [2, 3], [C, -C]);

% First illustrate VB (preamble end) — state continuity into post-12.
RDP1 = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP1 = spm_set_costs(RDP1, [2, 3], [C, -C]);
RDP1 = spm_mdp2rdp(RDP1);
RDP1.T = 64;
OPTIONS = struct('std', 1, 'tol', 1/128, 'Nmax', 16, 'n', 4, 'noprint', true);
spm_MDP_VB_XXX(RDP1, OPTIONS, false, false);

% Active inference (~DEM_AtariIII.m 239--325).
MDP{1}.GA = GDP.A;
MDP{1}.GB = GDP.B;
MDP{1}.GU = GDP.U;
MDP{1}.GD = GDP.D;
MDP{1}.ID = GDP.id;
MDP{1}.chi = 512;

for i = 1:NR
    RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
    RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
    RDP.T = fix(NT / Ne);
    PDPg = spm_MDP_VB_XXX(RDP, OPTIONS, false, false);
    O = PDPg.Q.O{1};
    t = 0:(NT - Ne);
    for s = 1:Ne
        MDP = spm_merge_structure_learning(O(:, t + s), MDP);
    end
    MDP = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if mod(i, 8) == 0 || i == NR
        fprintf(1, '[DEMO2 dump] NR game %d/%d\n', i, NR);
    end
end

MDP_pre_post_nr = MDP;

meta = struct();
meta.capture_script = mfilename;
meta.rng_seed = 2;
meta.boundary = 'post_nr_loop_pre_call3_sort';
meta.GDP_T = GDP.T;
meta.NR = NR;
meta.NT = NT;
meta.NS = NS;
meta.timestamp = datestr(now, 31);
meta.matlab_release = version;

outMat = fullfile(outDir, 'DEMAtariIII_demo2_MDP_pre_call3_post_nr.mat');
save(outMat, 'MDP_pre_post_nr', 'GDP', 'C', 'Ne', 'Nm', 'NT', 'NR', 'NS', 'meta', '-v7');
fprintf(1, '[DEMO2 dump] wrote %s (Nm=%d Ne=%d NR=%d)\n', outMat, Nm, Ne, NR);
end
