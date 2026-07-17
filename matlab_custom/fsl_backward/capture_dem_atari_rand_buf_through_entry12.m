% capture_dem_atari_rand_buf_through_entry12.m
%
% FSL backward 1b extension — MATLAB ``rng(2)`` ledger through Entry 12 preamble
% (through first ``RDP`` assembly; ``dem_atari_rand_buf`` finishes before VB).
%
% Writes:
%   tests/oracle/toolbox/DEM/fixtures/dem_atari_rand_buf_through_entry12.mat
%     dem_atari_rand_buf — scalar ``rand()`` via fsl_backward/rand.m (not vb_rand_buf)
%     K_12               — buffer length (expect match K_11 if no draws after Entry 11)
%     RDP_reference      — nested RDP for call 1 (T=64)
%     PDP_reference      — optional cross-check after first illustrate VB
%     meta
%
% VB draws use Entry 12 ``vb_rand_buf`` lane — not logged here.
%
%   matlab -batch "cd('...\matlab_custom\fsl_backward'); capture_dem_atari_rand_buf_through_entry12;"

function capture_dem_atari_rand_buf_through_entry12()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
outDir = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
entry12Dir = fullfile(repoRoot, 'matlab_custom', 'entry12');
demDir = fullfile(repoRoot, 'matlab_src', 'toolbox', 'DEM');
addpath(genpath(fullfile(repoRoot, 'matlab_src')), '-begin');
addpath(demDir, '-begin');
addpath(thisDir, '-begin');
addpath(entry12Dir, '-begin');
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

rng(2);
rgms_fsl_rand_log_begin();
fprintf(1, '[FSL backward 1b] rng(2) — ledger through Entry 12 preamble (FSL rand log)\n');

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
PDP_train = spm_MDP_generate(GDP);

MDP = spm_faster_structure_learning(PDP_train.O(:, 1:1000), S, Sc);

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

r = spm_get_hits(PDP_train.o, GDP.id);
c = spm_get_miss(PDP_train.o, GDP.id);
for i = 1:numel(r)
    s = c(find(c < r(i), 1, 'last'));
    t = (s + Ne):(r(i) + Ne);
    if numel(t)
        for s = 1:Ne
            MDP = spm_merge_structure_learning(PDP_train.O(:, t + s), MDP);
        end
    end
end

NT = 100;
for i = 1:128
    q = rem(i, 100 - 1);
    t = (0:(NT + Ne)) + q * NT;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP_train.O(:, t + s), MDP);
    end
    [MDP, d] = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if all(d)
        break;
    end
end

MDP = spm_RDP_sort(MDP);
MDP = spm_set_goals(MDP, [2, 3], [C, -C]);

RDP_reference = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP_reference = spm_set_costs(RDP_reference, [2, 3], [C, -C]);
RDP_reference = spm_mdp2rdp(RDP_reference);
RDP_reference.T = 64;

% Finish dem_atari stream before VB (VB uses entry12 rand lane).
[dem_atari_rand_buf, K_12] = rgms_fsl_rand_log_finish();

% Cross-check: first illustrate VB (not appended to dem_atari_rand_buf).
OPTIONS = struct('std', 1, 'tol', 1/128, 'Nmax', 16, 'n', 4, 'noprint', true);
PDP_reference = spm_MDP_VB_XXX(RDP_reference, OPTIONS, false, false);

meta = struct();
meta.capture_script = mfilename;
meta.rng_seed = 2;
meta.K_12 = K_12;
meta.rand_buf_phase = 'scalar_rand_log_through_entry12_preamble';
meta.boundary = 'post_entry11_pre_active_inference';
meta.note = ['dem_atari_rand_buf ends before call-1 VB; vb_rand_buf is separate (rgms_canonical).'];
meta.timestamp = datestr(now, 31);
meta.matlab_release = version;

outMat = fullfile(outDir, 'dem_atari_rand_buf_through_entry12.mat');
save(outMat, 'dem_atari_rand_buf', 'K_12', 'RDP_reference', 'PDP_reference', 'meta', '-v7');
fprintf(1, '[FSL backward 1b] wrote %s (K_12=%d)\n', outMat, K_12);
end
