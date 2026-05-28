% dump_rdp_DEM_AtariIII_FSL_1_11.m
%
% Build nested RDP at the same boundary as Python:
%   python_src/toolbox/DEM/DEM_AtariIII.py :: run_dem_atariiii(entry_stop=11)
% with harness defaults RGMS_ATARI_ENTRY8_OUTER=128, RGMS_ATARI_TRAINING_T=10000
% (i.e. FSL 1-11), NOT a verbatim copy of matlab_custom/dump_rdp_DEM_AtariIII.m
% (which uses GDP.tau=2, 256 basin outer iterations, and four spm_RDP_sort passes).
%
% Divergences from dump_rdp_DEM_AtariIII.m (intentional, Python / FSL driver parity):
%   - GDP.tau = 1  (Python Entry 3 overwrites tau before spm_MDP_generate)
%   - for i = 1:128  (Python _entry8_outer_loop_count default max 128)
%   - Single MDP = spm_RDP_sort(MDP)  (Python Entry 10 calls spm_RDP_sort once)
% Entry 11 matches DEM_AtariIII.m ``assemble RGM`` block (lines ~213--216):
%   RDP = spm_set_goals(MDP,...);  % MATLAB names the MDP-stage output ``RDP`` here
%   RDP = spm_set_costs(RDP,...); RDP = spm_mdp2rdp(RDP); RDP.T = 64;
%
% Output: tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat
%   Variables: RDP (nested), meta (struct). MAT-file v7 for scipy.io.loadmat.
%
% Also writes tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_plot_ctx.mat
%   Variables: RGB, GDP, Nm, Nr, Nc, Nd, C, Sc, plot_meta — MATLAB-native plot inputs
%   (see Atari_plotting.md § Plot artifact registry).
%
% Requires SPM on path the same way you run the stock demo.

rng(2)

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C  = 32;

[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);

S      = ones(4,3);
S(1,:) = [Nr,Nc,1];
S(2,:) = [1 1 1];
S(3,:) = [1 1 1];
S(4,:) = [1 1 1];

spm_get_hits = @(o,id) find(o(id.reward,:)    > 1);
spm_get_miss = @(o,id) find(o(id.contraint,:) > 1);

spm_figure('GetWin','Gameplay'); clf

GDP.tau = 1;
GDP.T   = 10000;
PDP     = spm_MDP_generate(GDP);

con   = PDP.id.control;
for t = 1:128
    subplot(2,1,1)
    imshow(spm_O2rgb(PDP.O(:,t),RGB))
    subplot(4,3,8)
    imshow(PDP.O{con,t}')
    drawnow
end

MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);

Nm    = numel(MDP);
Ne    = max(2^(Nm - 1),1);
for n = 1:Nm
    for g = 1:numel(MDP{n}.a)
        MDP{n}.a{g} = [];
    end
    for f = 1:numel(MDP{n}.b)
        MDP{n}.b{f} = [];
    end
end

r     = spm_get_hits(PDP.o,GDP.id);
c     = spm_get_miss(PDP.o,GDP.id);
for i = 1:numel(r)
    s  = c(find(c < r(i),1,'last'));
    t  = (s + Ne):(r(i) + Ne);
    if numel(t)
        for s = 1:Ne
            MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP);
        end
    end
end

spm_figure('GetWin','Attractors'); clf

NT = 100;
NS = [];
NU = [];
NA = [];
for i = 1:128
    q     = rem(i,100 - 1);
    t     = (0:(NT + Ne)) + q*NT;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP);
    end
    [MDP,d] = spm_RDP_basin(MDP,[2,3],[C,-C]);
    NS(end + 1) = size(MDP{Nm}.b{1},2);
    NU(end + 1) = size(MDP{Nm}.b{1},3);
    NA(end + 1) = sum(~d);
    subplot(2,3,1), plot(NS), title('Deep states'),      axis square
    subplot(2,3,2), plot(NU), title('Deep paths'),       axis square
    subplot(2,3,3), plot(NA), title('Absorbing states'), axis square
    drawnow
    if all(d), break, end
end

MDP = spm_RDP_sort(MDP);

MDP   = spm_set_goals(MDP,[2,3],[C,-C]);
hid   = MDP{Nm}.id.hid;

subplot(2,2,3)
spm_dir_orbits(MDP{Nm}.b{1},hid,128);

subplot(2,2,4)
B     = sum(MDP{Nm}.b{1},3) > 0;
Ns    = size(B,1);
Nt    = 32;
h     = sparse(1,hid,1,1,Ns);
P     = zeros(Nt,Ns);
for t = 1:Nt
    P(t,:) = h;
    h      = (h + h*B) > 0;
end
imagesc(P), hold on
plot(hid,zeros(size(hid)) + 1/2,'or','MarkerSize',8), hold off
title('Paths to hits','FontSize',14)
xlabel('latent states'), ylabel('time steps'), axis square

% assemble RGM (DEM_AtariIII.m; Entry 11 ledger)
RDP   = spm_set_goals(MDP,[2,3],[C,-C]);
RDP   = spm_set_costs(RDP,[2,3],[C,-C]);
RDP   = spm_mdp2rdp(RDP);
RDP.T = 64;

thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(thisDir);
outDir = fullfile(repoRoot,'tests','oracle','toolbox','DEM','fixtures');
if ~exist(outDir,'dir')
    mkdir(outDir);
end
outMat = fullfile(outDir,'DEMAtariIII_fsl_1_11_rdp.mat');

meta = struct();
meta.capture_script = mfilename;
meta.rng_seed = 2;
meta.GDP_tau = GDP.tau;
meta.GDP_T = GDP.T;
meta.Sc = Sc;
meta.n_outer_fsl = 128;
meta.rdp_sort_passes = 1;
meta.matlab_release = version;

save(outMat,'RDP','meta','-v7');
fprintf(1,'Saved FSL 1-11 oracle: %s\n', outMat);

% Plot context for *PLOT entries (12PLOT and later); same run as RDP above.
plotCtxMat = fullfile(outDir,'DEMAtariIII_fsl_1_11_plot_ctx.mat');
plot_meta = struct();
plot_meta.capture_script = mfilename;
plot_meta.rng_seed = 2;
plot_meta.rdp_mat = outMat;
plot_meta.purpose = 'MATLAB-native inputs for Atari plotting oracles (RGB, GDP, Nm); see Atari_plotting.md';
save(plotCtxMat,'RGB','GDP','Nm','Nr','Nc','Nd','C','Sc','plot_meta','-v7');
fprintf(1,'Saved FSL 1-11 plot context: %s\n', plotCtxMat);
