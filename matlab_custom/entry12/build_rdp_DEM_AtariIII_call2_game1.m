function build_rdp_DEM_AtariIII_call2_game1()
%BUILD_RDP_DEM_ATARIII_CALL2_GAME1  **Deprecated** — use ``DEMAtariIII_entry12_dump_all_subentries.m``.
%BUILD_RDP_DEM_ATARIII_CALL2_GAME1  Assemble ``RDP`` for DEM_AtariIII VB call 2 (game 1).
%
% Matches ``DEM_AtariIII.m`` through structure-learning preamble + active-inference
% setup, then the *first* loop iteration (~line 268) **before** ``spm_MDP_VB_XXX``.
%
% Writes ``tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_atari_call2_game1_rdp.mat``
% (variable ``RDP``) and a small ``meta`` struct (``T``, ``Ne``, ``NS``, ``NT``).
%
% Environment:
%   RGMS_ENTRY12_CAPTURE_OUT_DIR  — default: repo fixtures (see dump driver)

tRun = tic;
fprintf(1, '[call2 build] started %s\n', datestr(now, 31));

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

rng(2);

Nr = 12;
Nc = 9;
Sc = 3;
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

GDP.tau = 2;
GDP.T   = 10000;
PDP     = spm_MDP_generate(GDP);

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

NT_basin = 100;
for i = 1:128
    t = (0:(NT_basin + Ne)) + rem(i, 100 - 1) * NT_basin;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP.O(:, t + s), MDP);
    end
    [MDP, d] = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if all(d)
        break
    end
end

for q = 1:4
    MDP = spm_RDP_sort(MDP);
end

% Active inference — install generative process (DEM_AtariIII.m ~239–246)
MDP{1}.GA  = GDP.A;
MDP{1}.GB  = GDP.B;
MDP{1}.GU  = GDP.U;
MDP{1}.GD  = GDP.D;
MDP{1}.ID  = GDP.id;
MDP{1}.chi = 512;

NT = 256;
NS = 256;

RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = fix(NT / Ne);

meta = struct();
meta.call = 'DEM_AtariIII_call2_game1';
meta.dem_atari_line = 268;
meta.NT = NT;
meta.Ne = Ne;
meta.NS = NS;
meta.RDP_T = RDP.T;
meta.build_script = mfilename('fullpath');
meta.timestamp = datestr(now, 31);

outMat = fullfile(outDir, 'DEMAtariIII_atari_call2_game1_rdp.mat');
save(outMat, 'RDP', 'meta', '-v7');
fprintf(1, '[call2 build] wrote %s (RDP.T=%d, Ne=%d)\n', outMat, RDP.T, Ne);
fprintf(1, '[call2 build] elapsed %.1f s (%.2f min)\n', toc(tRun), toc(tRun) / 60);

end
