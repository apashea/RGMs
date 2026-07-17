% dump_MDP_pre_entry10.m
%
% One-time MATLAB authority for FSL backward Entry 10 input (after Entry 9, before Entry 10).
% Same ``rng(2)`` ledger scale as ``dump_MDP_pre_entry11.m`` / Entry 12 Call 1 (outer 128, T=10000).
%
% Output: tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat
%   MDP_pre_entry5  — cell MDP after Entry 4 structure learning (pre Entry 5 forget)
%   MDP_pre_entry7  — cell MDP after Entry 5 forget (pre Entry 7 hit/miss merges)
%   MDP_pre_entry9  — cell MDP after Entry 7 assimilations (input to Entry 8 / Entry 9 loops)
%   MDP_post_entry8 — cell MDP after Entry 8 only (128× merge, no ``spm_RDP_basin``)
%   MDP_pre_entry10 — cell MDP after Entry 9 basin loop (pre ``spm_RDP_sort``)
%   PDP_O           — ``PDP.O`` columns covering Entry 7 + Entry 8/9 merge indices
%   PDP_o           — outcome matrix for Entry 6 event/window discovery
%   GDP_id_reward, GDP_id_contraint — ``GDP.id`` indices for ``spm_get_hits`` / ``spm_get_miss``
%   C, Ne, Nm, NT, meta
%
% Then (once): python tests/oracle/toolbox/DEM/fsl_backward_materialize_mdp_pre_entry10_pkl.py
%
% See Atari_example.md § FSL backward validation (Entry 11 → 1).

function dump_MDP_pre_entry10()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
demo1_add_matlab_src(repoRoot);
outDir = demo1_fixtures_dir(repoRoot);

rng(2);
fprintf(1, '[FSL backward dump] rng(2) — ledger through Entry 9 (pre-Entry-10 boundary)\n');

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

MDP_pre_entry5 = MDP;

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

MDP_pre_entry7 = MDP;

r = spm_get_hits(PDP.o, GDP.id);
c = spm_get_miss(PDP.o, GDP.id);
PDP_o = PDP.o;
GDP_id_reward = GDP.id.reward;
GDP_id_contraint = GDP.id.contraint;

entry6_r = r;
entry6_c = c;
entry6_t_windows = {};
wi = 0;
for i = 1:numel(r)
    s = c(find(c < r(i), 1, 'last'));
    t = (s + Ne):(r(i) + Ne);
    if numel(t)
        wi = wi + 1;
        entry6_t_windows{wi} = t;
    end
end
fprintf(1, '[FSL backward dump] Entry 6: n_windows=%d\n', wi);

maxCol = 1000;
for i = 1:numel(r)
    s = c(find(c < r(i), 1, 'last'));
    t = (s + Ne):(r(i) + Ne);
    if numel(t)
        maxCol = max(maxCol, max(t + Ne));
    end
end
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
MDP_pre_entry9 = MDP;
for ii = 1:128
    q = rem(ii, 100 - 1);
    t = (0:(NT + Ne)) + q * NT;
    maxCol = max(maxCol, max(t + Ne));
end
nPDP = size(PDP.O, 2);
maxCol = min(maxCol, nPDP);
PDP_O = PDP.O(:, 1:maxCol);
fprintf(1, '[FSL backward dump] PDP_O columns 1:%d (of %d); Entry7 max from hits\n', maxCol, nPDP);

snapPath = fullfile(outDir, 'rgms_fsl_backward_snap_mdp_pre_entry9.mat');
save(snapPath, 'MDP', '-v7');

S8 = load(snapPath);
MDP8 = S8.MDP;
for i = 1:128
    q = rem(i, 100 - 1);
    t = (0:(NT + Ne)) + q * NT;
    for s = 1:Ne
        MDP8 = spm_merge_structure_learning(PDP.O(:, t + s), MDP8);
    end
end
MDP_post_entry8 = MDP8;
fprintf(1, '[FSL backward dump] Entry 8 merge-only loop done\n');

S9 = load(snapPath);
MDP = S9.MDP;
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

MDP_pre_entry10 = MDP;

meta = struct();
meta.capture_script = mfilename;
meta.rng_seed = 2;
meta.GDP_T = GDP.T;
meta.GDP_tau = GDP.tau;
meta.n_outer = 128;
meta.boundary = 'post_entry9_pre_entry10';
meta.boundary_pre_entry9 = 'post_entry7_pre_entry8_9_loop';
meta.boundary_pre_entry7 = 'post_entry5_pre_entry7_hit_miss';
meta.PDP_O_maxCol = maxCol;
meta.PDP_O_width = nPDP;
meta.timestamp = datestr(now, 31);
meta.matlab_release = version;

outMat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry10.mat');
save(outMat, 'MDP_pre_entry5', 'MDP_pre_entry7', 'MDP_pre_entry9', 'MDP_post_entry8', 'MDP_pre_entry10', ...
    'PDP_O', 'PDP_o', 'GDP_id_reward', 'GDP_id_contraint', ...
    'entry6_r', 'entry6_c', 'entry6_t_windows', ...
    'C', 'Ne', 'Nm', 'NT', 'meta', '-v7');
try
    delete(snapPath);
catch
end
fprintf(1, '[FSL backward dump] wrote %s (Nm=%d Ne=%d NT=%d)\n', outMat, Nm, Ne, NT);
end
