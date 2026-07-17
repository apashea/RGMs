function DEMO1_dump_all_fixtures()
%DEMO1_DUMP_ALL_FIXTURES  Single ``rng(2)`` ledger; conditional writes only (§8.4).
%
% Produces FSL authority mats, FSL rand buf, plot ctx, and Entry 12 input RDP under
% ``demo1_fixtures_dir``. Full ledger code always runs when any target is missing.
% Entry 12 VB bands / PDP use ``DEMAtariIII_entry12_dump_all_subentries`` (legacy load)
% after Python **1a** — orchestrator calls that separately.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
addpath(fullfile(repoRoot, 'matlab_custom', 'fsl_backward'), '-begin');
demo1_add_matlab_src(repoRoot);
outDir = demo1_fixtures_dir(repoRoot);

pre10Mat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry10.mat');
pre11Mat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry11.mat');
randMat = fullfile(outDir, 'dem_atari_rand_buf_through_entry11.mat');
plotCtxMat = fullfile(outDir, 'DEMAtariIII_fsl_1_11_plot_ctx.mat');
rdpMat = fullfile(outDir, 'DEMAtariIII_XXX_12_rdp.mat');

needPre10 = ~isfile(pre10Mat);
needPre11 = ~isfile(pre11Mat);
needRand = ~isfile(randMat);
needPlot = ~isfile(plotCtxMat);
needRdp = ~isfile(rdpMat);

if ~(needPre10 || needPre11 || needRand || needPlot || needRdp)
    fprintf(1, '[DEMO1 dump] all FSL/RDP fixtures present — skip ledger\n');
    return;
end

fprintf(1, '[DEMO1 dump] rng(2) — single ledger (conditional writes only)\n');
rng(2);
if needRand
    rgms_fsl_rand_log_begin();
end

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C = 32;

entry1_Nr = Nr;
entry1_Nc = Nc;
entry1_Sc = Sc;
entry1_Nd = Nd;
entry1_C = C;

[GDP, hid_post_entry2, cid_post_entry2, con_post_entry2, RGB, ~] = spm_MDP_pong(Nr, Nc, Nd, true, 0);
GDP_post_entry2 = GDP;
RGB_post_entry2 = RGB;
S_post_entry2 = ones(4, 3);
S_post_entry2(1, :) = [Nr, Nc, 1];

S = ones(4, 3);
S(1, :) = [Nr, Nc, 1];
S(2, :) = [1, 1, 1];
S(3, :) = [1, 1, 1];
S(4, :) = [1, 1, 1];

spm_get_hits = @(o, id) find(o(id.reward, :) > 1);
spm_get_miss = @(o, id) find(o(id.contraint, :) > 1);

GDP.tau = 1;
GDP.T = 10000;
PDP = spm_MDP_generate(GDP);

MDP = spm_faster_structure_learning(PDP.O(:, 1:1000), S, Sc);
MDP_pre_entry5 = MDP;
Nm = numel(MDP);
Ne = max(2^(Nm - 1), 1);

if needPlot
    plot_meta = struct();
    plot_meta.capture_script = mfilename;
    plot_meta.rng_seed = 2;
    plot_meta.purpose = 'MATLAB-native plot inputs for 12PLOT oracles';
    demo1_save_if_missing(plotCtxMat, 'RGB', 'GDP', 'Nm', 'Nr', 'Nc', 'Nd', 'C', 'Sc', 'plot_meta');
end

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

meta10 = struct();
meta10.capture_script = mfilename;
meta10.rng_seed = 2;
meta10.boundary = 'post_entry9_pre_entry10';
meta10.timestamp = datestr(now, 31);

if needPre10
    save(pre10Mat, 'MDP_pre_entry5', 'MDP_pre_entry7', 'MDP_pre_entry9', 'MDP_post_entry8', ...
        'MDP_pre_entry10', 'PDP_O', 'PDP_o', 'GDP_id_reward', 'GDP_id_contraint', ...
        'entry1_Nr', 'entry1_Nc', 'entry1_Sc', 'entry1_Nd', 'entry1_C', ...
        'GDP_post_entry2', 'RGB_post_entry2', 'S_post_entry2', ...
        'hid_post_entry2', 'cid_post_entry2', 'con_post_entry2', ...
        'entry6_r', 'entry6_c', 'entry6_t_windows', ...
        'C', 'Ne', 'Nm', 'NT', 'meta10', '-v7');
    fprintf(1, '[DEMO1 dump] wrote %s\n', pre10Mat);
else
    fprintf(1, '[DEMO1 dump] skip write (exists): %s\n', pre10Mat);
end

try
    delete(snapPath);
catch
end

MDP = spm_RDP_sort(MDP);
MDP_pre_entry11 = spm_set_goals(MDP, [2, 3], [C, -C]);

meta11 = struct();
meta11.capture_script = mfilename;
meta11.rng_seed = 2;
meta11.boundary = 'post_entry10_pre_entry11';
meta11.timestamp = datestr(now, 31);

demo1_save_if_missing(pre11Mat, 'MDP_pre_entry11', 'C', 'Ne', 'Nm', 'meta11');

if needRand
    [dem_atari_rand_buf, K_11] = rgms_fsl_rand_log_finish();
    metaRand = struct();
    metaRand.capture_script = mfilename;
    metaRand.rng_seed = 2;
    metaRand.K_11 = K_11;
    metaRand.timestamp = datestr(now, 31);
    RDP_reference = spm_set_costs(MDP_pre_entry11, [2, 3], [C, -C]);
    RDP_reference = spm_mdp2rdp(RDP_reference);
    RDP_reference.T = 64;
    demo1_save_if_missing(randMat, 'dem_atari_rand_buf', 'K_11', 'RDP_reference', 'metaRand');
end

if needRdp
    RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
    RDP = spm_mdp2rdp(RDP);
    RDP.T = 64;
    demo1_save_if_missing(rdpMat, 'RDP');
end

fprintf(1, '[DEMO1 dump] single ledger complete\n');
end
