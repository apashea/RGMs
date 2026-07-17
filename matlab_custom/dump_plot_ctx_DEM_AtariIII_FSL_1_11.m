% dump_plot_ctx_DEM_AtariIII_FSL_1_11.m
%
% Produce DEMAtariIII_fsl_1_11_plot_ctx.mat only (RGB, GDP, Nm, scalars).
% Same FSL-lane preamble as dump_rdp_DEM_AtariIII_FSL_1_11.m through Nm = numel(MDP)
% after spm_faster_structure_learning — does NOT rebuild/save RDP or run outer loops.
%
% Use when DEMAtariIII_fsl_1_11_rdp.mat already exists and only plot inputs are missing.
% Full FSL dump (RDP + plot_ctx) remains dump_rdp_DEM_AtariIII_FSL_1_11.m.
%
% Output: <DEMO1 fixture root>/DEMAtariIII_fsl_1_11_plot_ctx.mat

thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(thisDir);
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
demo1_add_matlab_src(repoRoot);

rng(2)

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C  = 32;

[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);

GDP.tau = 1;
GDP.T   = 10000;
PDP     = spm_MDP_generate(GDP);

S      = ones(4,3);
S(1,:) = [Nr,Nc,1];
S(2,:) = [1 1 1];
S(3,:) = [1 1 1];
S(4,:) = [1 1 1];

MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);
Nm  = numel(MDP);

outDir = demo1_fixtures_dir(repoRoot);
plotCtxMat = fullfile(outDir,'DEMAtariIII_fsl_1_11_plot_ctx.mat');

plot_meta = struct();
plot_meta.capture_script = mfilename;
plot_meta.rng_seed = 2;
plot_meta.purpose = 'MATLAB-native plot inputs for Atari *PLOT oracles; see Atari_plotting.md';
plot_meta.note = 'Nm from spm_faster_structure_learning on training PDP.O(:,1:1000)';

save(plotCtxMat,'RGB','GDP','Nm','Nr','Nc','Nd','C','Sc','plot_meta','-v7');
fprintf(1,'Saved plot context: %s\n', plotCtxMat);
