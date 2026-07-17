% capture_dem_atari_rand_buf_through_entry11.m
%
% FSL backward 1b (phase A) — MATLAB ``rng(2)`` ledger through Entry 11.
%
% Writes:
%   tests/oracle/toolbox/DEM/fixtures/dem_atari_rand_buf_through_entry11.mat
%     RDP_reference — nested RDP after Entry 11 (cross-check vs DEMAtariIII_XXX_12_rdp.mat)
%     meta          — capture metadata
%
% Logs scalar ``rand()`` via ``matlab_custom/fsl_backward/rand.m`` on path (not Entry 12
% ``vb_rand_buf``). **FSL backward 3** replays ``dem_atari_rand_buf`` when
% ``RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS=1``.
%
% Requires SPM on path (same as dump_rdp_DEM_AtariIII_FSL_1_11.m).
% See Atari_example.md § FSL backward validation (Entry 11 → 1).

function capture_dem_atari_rand_buf_through_entry11()
thisDir = fileparts(mfilename('fullpath'));
addpath(thisDir, '-begin');
repoRoot = fileparts(fileparts(thisDir));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
demo1_add_matlab_src(repoRoot);
outDir = demo1_fixtures_dir(repoRoot);

rng(2);
rgms_fsl_rand_log_begin();
fprintf(1, '[FSL backward 1b] rng(2) — ledger through Entry 11 (FSL rand log; not Entry 12 vb_rand_buf)\n');

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
MDP = spm_set_goals(MDP, [2, 3], [C, -C]);

RDP_reference = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP_reference = spm_set_costs(RDP_reference, [2, 3], [C, -C]);
RDP_reference = spm_mdp2rdp(RDP_reference);
RDP_reference.T = 64;

[dem_atari_rand_buf, K_11] = rgms_fsl_rand_log_finish();

meta = struct();
meta.capture_script = mfilename;
meta.rng_seed = 2;
meta.K_11 = K_11;
meta.rand_buf_phase = 'scalar_rand_log';
meta.timestamp = datestr(now, 31);
meta.matlab_release = version;
meta.note = ['FSL backward dem_atari_rand_buf — not Entry 12 vb_rand_buf; ', ...
    'scalar rand() only via matlab_custom/fsl_backward/rand.m shadow.'];

outMat = fullfile(outDir, 'dem_atari_rand_buf_through_entry11.mat');
save(outMat, 'dem_atari_rand_buf', 'K_11', 'RDP_reference', 'meta', '-v7');
fprintf(1, '[FSL backward 1b] wrote %s (K_11=%d, RDP_reference)\n', outMat, K_11);
end
