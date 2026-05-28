function DEMAtariIII_entry12_dump_all_subentries(mode)
%DEMATARIII_ENTRY12_DUMP_ALL_SUBENTRIES  Entry 12 MATLAB runner (script **1b**).
% Optional ``mode``:
%   ``'refresh_call2'`` — call-2 VB capture only (``RDP`` + ``K`` mats on disk).
%   ``'capture_call3'`` — ledger + NR active-inference loop + call-3 VB oracle
%      (``rgms_atari_call3``, post-loop ``spm_RDP_sort`` / ``T=128``).
%   ``'capture_call4'`` — same NR loop + call-4 VB oracle
%      (``rgms_atari_call4``, post-loop sort + ``spm_RDP_MI`` / ``T=128``).
%
% One ``rng(2)`` session: FSL 1--11 ledger (inline), VB capture **call 1**
% (``rgms_canonical``), continue ``DEM_AtariIII.m`` through active-inference game 1,
% VB capture **call 2** (``rgms_atari_call2``). Same ``vb_rand_buf`` preamble-rewind
% per call. No separate RDP-build scripts.
%
% Optional (legacy call-1-only refresh from existing FSL ``.mat``):
%   RGMS_ENTRY12_CAPTURE_LEGACY_LOAD=1
%   RGMS_ENTRY12_CAPTURE_RDP_MAT=<path>   (default FSL fixture)
%   RGMS_ENTRY12_CAPTURE_SKIP_CALL2=1
%
% Environment (optional):
%   RGMS_ENTRY12_CAPTURE_RUN_TAG       — used only for legacy single-call load path
%   RGMS_ENTRY12_CAPTURE_OUT_DIR
%   RGMS_ENTRY12_CAPTURE_Y_PROBE
%
% Before **1b**: run **1a** ``entry12_preflight_vb_rand_k.py`` for ``rgms_canonical``.
% Call 2 ``K`` is counted inside this script (same draw sites as **1a**) before call-2 VB.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

outDir = getenv('RGMS_ENTRY12_CAPTURE_OUT_DIR');
if isempty(outDir)
    outDir = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(here);

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'refresh_call2')
    rdpPath = entry12_xxx12_rdp_mat_(outDir, 'rgms_atari_call2');
    if ~isfile(rdpPath)
        error('Missing call-2 RDP mat: %s', rdpPath);
    end
    S = load(rdpPath, 'RDP');
    fprintf(1, '[entry12 dump] refresh_call2 started %s\n', datestr(now, 31));
    entry12_dump_one_vb_call_(S.RDP, 'rgms_atari_call2', outDir, rdpPath);
    fprintf(1, '[entry12 dump] refresh_call2 done\n');
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_call3')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_call3 started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    NT = 256;
    NS = 256;
    NR = 32;
    MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR);
    RDP3 = entry12_dem_call3_rdp_post_loop_(MDP, C, NS);
    entry12_count_and_save_vb_rand_k_(RDP3, outDir, 'rgms_atari_call3');
    entry12_dump_one_vb_call_(RDP3, 'rgms_atari_call3', outDir, 'inline_nr_loop_post_call3');
    fprintf(1, '[entry12 dump] capture_call3 finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_call4')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_call4 started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    NT = 256;
    NS = 256;
    NR = 32;
    MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR);
    RDP4 = entry12_dem_call4_rdp_post_loop_(MDP, C, NS);
    entry12_count_and_save_vb_rand_k_(RDP4, outDir, 'rgms_atari_call4');
    entry12_dump_one_vb_call_(RDP4, 'rgms_atari_call4', outDir, 'inline_nr_loop_post_call4');
    fprintf(1, '[entry12 dump] capture_call4 finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

tRun = tic;
fprintf(1, '[entry12 dump] started %s\n', datestr(now, 31));

legacyLoad = entry12_env_truthy_('RGMS_ENTRY12_CAPTURE_LEGACY_LOAD');
skipCall2 = entry12_env_truthy_('RGMS_ENTRY12_CAPTURE_SKIP_CALL2');

if legacyLoad
    rdpMat = getenv('RGMS_ENTRY12_CAPTURE_RDP_MAT');
    if isempty(rdpMat)
        rdpMat = fullfile(outDir, 'DEMAtariIII_fsl_1_11_rdp.mat');
    end
    if ~exist(rdpMat, 'file')
        error('RDP mat not found: %s', rdpMat);
    end
    S = load(rdpMat, 'RDP');
    RDP = S.RDP;
    rdpSource = rdpMat;
    fprintf(1, '[entry12 dump] legacy load call 1 RDP from %s\n', rdpMat);
    entry12_dump_one_vb_call_(RDP, 'rgms_canonical', outDir, rdpSource);
    if skipCall2
        fprintf(1, '[entry12 dump] SKIP_CALL2 — finished legacy call 1 only\n');
        return;
    end
    error(['Legacy load cannot continue to call 2 (MDP workspace missing). ', ...
        'Omit RGMS_ENTRY12_CAPTURE_LEGACY_LOAD for full inline ledger + call 2.']);
end

% Inline ``rng(2)`` ledger through Entry 11 (``dump_rdp_DEM_AtariIII_FSL_1_11.m`` lane).
rng(2);
[MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP);
RDP.T = 64;
rdpSource = 'inline_rng2_DEM_AtariIII_entry11';

entry12_dump_one_vb_call_(RDP, 'rgms_canonical', outDir, rdpSource);

if ~skipCall2
    fprintf(1, '[entry12 dump] elapsed %.1f s — continue DEM_AtariIII active inference (game 1)\n', toc(tRun));
    RDP2 = entry12_dem_call2_rdp_game1_(MDP, GDP, Ne, C);
    entry12_count_and_save_vb_rand_k_(RDP2, outDir, 'rgms_atari_call2');
    entry12_dump_one_vb_call_(RDP2, 'rgms_atari_call2', outDir, 'inline_after_call1_game1');
end

fprintf(1, '[entry12 dump] finished %s — total elapsed %.1f s (%.2f min)\n', ...
    datestr(now, 31), toc(tRun), toc(tRun) / 60);
end


function entry12_dump_one_vb_call_(RDP, tag, outDir, rdpSource)
% One VB invocation + Entry 12 subentry capture for ``tag``.

setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', tag);

rdpOut = entry12_xxx12_rdp_mat_(outDir, tag);
save(rdpOut, 'RDP', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, rdpOut);

OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

meta = struct();
meta.run_tag = tag;
meta.rdp_source = rdpSource;
meta.capture_script = which('DEMAtariIII_entry12_dump_all_subentries');
meta.matlab_release = version;
meta.timestamp = datestr(now, 31);
meta.subentry = '12A';

MDP = spm_MDP_checkX(RDP);

fname12A = fullfile(outDir, sprintf('DEMAtariIII_entry12_%s_12A.mat', tag));
save(fname12A, 'MDP', 'OPTIONS', 'meta', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, fname12A);

kPath = entry12_vb_rand_k_mat_(outDir, tag);
if ~isfile(kPath)
    error('Missing VB draw count K: %s\nRun entry12_preflight_vb_rand_k.py for tag %s first, or use inline count (call 2).', kPath, tag);
end
Sk = load(kPath);
K = Sk.K(1);

capture_protocol = 'entry12_v5_preamble_rewind';
entry12_sample_trace_matlab('reset');
rgms_entry12_s_pre = rng;
fprintf(1, '[entry12 dump] tag=%s starting VB + subentry dump (12B–12I)\n', tag);
PDP = spm_MDP_VB_XXX(MDP, OPTIONS, false, true);
entry12_sample_trace_matlab('finalize', tag, outDir);
rng(rgms_entry12_s_pre);
fprintf(1, '[entry12 dump] tag=%s VB + subentry dump done\n', tag);

if K > 0
    vb_rand_buf = rand(K, 1);
else
    vb_rand_buf = zeros(0, 1);
end
randOut = entry12_vb_rand_buf_mat_(outDir, tag);
rdpMat = rdpSource;
save(randOut, 'vb_rand_buf', 'K', 'rdpMat', 'tag', 'capture_protocol', 'rdpSource', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s (K=%d)\n', tag, randOut, K);

pdpOut = entry12_xxx12_pdp_mat_(outDir, tag);
metaPdp = struct();
metaPdp.capture_script = which('DEMAtariIII_entry12_dump_all_subentries');
metaPdp.source_rdp_mat = rdpOut;
metaPdp.run_tag = tag;
save(pdpOut, 'PDP', 'meta', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, pdpOut);
end


function [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_()
% Entries 1--11 (FSL oracle lane): ``rng(2)`` already set by caller.

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
fprintf(1, '[entry12 dump] inline ledger through Entry 10 (Nm=%d Ne=%d)\n', Nm, Ne);
end


function MDP = entry12_dem_attach_generative_process_(MDP, GDP)
% Install Atari generative process on ``MDP{1}`` (~``DEM_AtariIII.m`` 241--246).

MDP{1}.GA = GDP.A;
MDP{1}.GB = GDP.B;
MDP{1}.GU = GDP.U;
MDP{1}.GD = GDP.D;
MDP{1}.ID = GDP.id;
MDP{1}.chi = 512;
end


function MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR)
% Active-inference game loop (~``DEM_AtariIII.m`` 254--325); updates ``MDP`` in place.

OPTIONS = entry12_default_options_sp_mdp_vb_xxx();
for i = 1:NR
    RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
    RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
    RDP.T = fix(NT / Ne);
    PDP = spm_MDP_VB_XXX(RDP, OPTIONS, false, false);
    O = PDP.Q.O{1};
    t = 0:(NT - Ne);
    for s = 1:Ne
        MDP = spm_merge_structure_learning(O(:, t + s), MDP);
    end
    MDP = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if mod(i, 8) == 0 || i == NR
        fprintf(1, '[entry12 dump] active-inference game %d/%d (T=%d)\n', i, NR, RDP.T);
    end
end
fprintf(1, '[entry12 dump] NR loop finished (Nm=%d Ne=%d)\n', Nm, Ne);
end


function RDP = entry12_dem_call3_rdp_post_loop_(MDP, C, NS)
% Third VB appearance (~``DEM_AtariIII.m`` 330--339): post-loop ``spm_RDP_sort``, ``T=128``.

RDP = spm_RDP_sort(MDP);
RDP = spm_set_goals(RDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = 128;
fprintf(1, '[entry12 dump] call-3 RDP assembled (T=%d, NS=%g)\n', RDP.T, NS);
end


function RDP = entry12_dem_call4_rdp_post_loop_(MDP, C, NS)
% Fourth VB appearance (~``DEM_AtariIII.m`` 381--389): sort + ``spm_RDP_MI``, ``T=128``.

RDP = spm_RDP_sort(MDP);
RDP = spm_RDP_MI(RDP);
RDP = spm_set_goals(RDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = 128;
fprintf(1, '[entry12 dump] call-4 RDP assembled (T=%d, NS=%g)\n', RDP.T, NS);
end


function RDP = entry12_dem_call2_rdp_game1_(MDP, GDP, Ne, C)
% ``DEM_AtariIII.m`` active inference, first game only (~lines 239--267).

MDP = entry12_dem_attach_generative_process_(MDP, GDP);

NT = 256;
NS = 256;

RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = fix(NT / Ne);
fprintf(1, '[entry12 dump] call-2 RDP assembled (T=%d, Ne=%d, NS=%d)\n', RDP.T, Ne, NS);
end


function entry12_count_and_save_vb_rand_k_(RDP, outDir, tag)
% Count scalar ``rand()`` during VB (``matlab_custom/entry12/rand.m`` shadow).

global rgms_entry12_rand_count rgms_entry12_use_replay rgms_entry12_buf

MDP = spm_MDP_checkX(RDP);
OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

rgms_entry12_buf = [];
rgms_entry12_use_replay = true;
rgms_entry12_rand_count = 0;

% Count only — do not dump subentries (tag env may still be call 1).
spm_MDP_VB_XXX(MDP, OPTIONS, false, false);

K = rgms_entry12_rand_count;
rgms_entry12_use_replay = false;
rgms_entry12_rand_count = 0;

kPath = entry12_vb_rand_k_mat_(outDir, tag);
save(kPath, 'K', '-v7');
fprintf(1, '[entry12 dump] tag=%s counted K=%d -> %s\n', tag, K, kPath);
end


function p = entry12_vb_rand_k_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'entry12_vb_rand_K.mat');
else
    p = fullfile(outDir, sprintf('entry12_vb_rand_K_%s.mat', tag));
end
end


function p = entry12_vb_rand_buf_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'DEMAtariIII_entry12_vb_matlab_rand_buf.mat');
else
    p = fullfile(outDir, sprintf('DEMAtariIII_entry12_vb_matlab_rand_buf_%s.mat', tag));
end
end


function p = entry12_xxx12_rdp_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'DEMAtariIII_XXX_12_rdp.mat');
else
    p = fullfile(outDir, sprintf('DEMAtariIII_XXX_12_%s_rdp.mat', tag));
end
end


function p = entry12_xxx12_pdp_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'DEMAtariIII_XXX_12_pdp.mat');
else
    p = fullfile(outDir, sprintf('DEMAtariIII_XXX_12_%s_pdp.mat', tag));
end
end


function tf = entry12_env_truthy_(name)
v = getenv(name);
tf = ~isempty(v) && any(strcmpi(strtrim(v), {'1', 'true', 'yes', 'on'}));
end


function OPTIONS = entry12_default_options_sp_mdp_vb_xxx()
OPTIONS = struct();
try, OPTIONS.B; catch, OPTIONS.B = 0; end
try, OPTIONS.C; catch, OPTIONS.C = 0; end
try, OPTIONS.D; catch, OPTIONS.D = 0; end
try, OPTIONS.N; catch, OPTIONS.N = 0; end
try, OPTIONS.O; catch, OPTIONS.O = 1; end
try, OPTIONS.P; catch, OPTIONS.P = 0; end
try, OPTIONS.Y; catch, OPTIONS.Y = 1; end
end
