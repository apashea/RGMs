function DEMAtariIII_optim1full_structure_learning_oracle_capture()
%DEMATARIII_OPTIM1FULL_STRUCTURE_LEARNING_ORACLE_CAPTURE  Structure F plot oracle.
%
% Produces MATLAB-native ``F`` + PNG for OPTIM1FULL §13 ``dem_structure_learning``.
% Mirrors ``DEM_AtariIII.m`` L309–323 on the MATLAB-owned payload (``F`` 6×NR).
%
% Env (same keys as spine ``--refresh-oracle``):
%   RGMS_ENTRY12_12PLOT_PDP_MAT      — ``…_matlab_payload.mat`` (payload, not PDP)
%   RGMS_ENTRY12_12PLOT_ORACLE_MAT   — output ``…_dem_structure_learning_oracle.mat``
%   RGMS_ENTRY12_12PLOT_VIS_DIR
%   RGMS_ENTRY12_12PLOT_FIGURE_TITLE — optional (default Structure learning)
%   RGMS_OPTIM1FULL_STRUCTURE_NT     — optional frames scale (default 256)

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

payloadMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(payloadMat)
    error('RGMS_ENTRY12_12PLOT_PDP_MAT unset (need dem_structure_learning payload).');
end
if ~exist(payloadMat, 'file')
    error('payload mat not found: %s', payloadMat);
end

outMat = getenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT');
if isempty(outMat)
    error('RGMS_ENTRY12_12PLOT_ORACLE_MAT unset.');
end

visDir = getenv('RGMS_ENTRY12_12PLOT_VIS_DIR');
if isempty(visDir)
    visDir = fullfile(repoRoot, 'visualizations');
end
if ~exist(visDir, 'dir')
    mkdir(visDir);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));
spmRoot = 'C:\Users\andre\Documents\MATLAB\spm-main';
if exist(spmRoot, 'dir')
    addpath(genpath(spmRoot));
end

S = load(payloadMat);
if ~isfield(S, 'F')
    error('structure payload missing F: %s', payloadMat);
end
F = double(S.F);

ntStr = getenv('RGMS_OPTIM1FULL_STRUCTURE_NT');
if isempty(ntStr)
    NT = 256;
else
    NT = str2double(ntStr);
end

figTitle = getenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE');
if isempty(figTitle)
    figTitle = 'Structure learning';
end
spm_figure('GetWin', figTitle);
clf
str = {'Latent states', 'Latent paths', 'ELBO', 'Reward count'};
for f = 1:numel(str)
    subplot(3, 2, f)
    plot(F(f, :)), axis square
    title(str{f}, 'FontSize', 14), xlabel('game')
end
i = size(F, 2);
t = (1:i) * NT;
subplot(3, 2, 4)
plot(t, F(4, 1:i)), axis square
title(str{4}, 'FontSize', 14), xlabel('frames')
drawnow

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
pngPath = fullfile(visDir, ['AtariIII_optim1full_structure_learning_oracle_' ts '.png']);
try
    saveas(gcf, pngPath);
catch
    print(gcf, pngPath, '-dpng');
end
fprintf(1, '[structure oracle] wrote PNG %s\n', pngPath);

meta = struct();
meta.site_id = 'dem_structure_learning';
meta.kind = 'structure_f';
meta.capture_script = mfilename('fullpath');
meta.payload_source_mat = payloadMat;
meta.png_path = pngPath;
meta.timestamp = ts;
meta.matlab_release = version;
meta.figure_title = figTitle;
meta.numeric_keys = {'F'};
meta.NT = NT;

outDir = fileparts(outMat);
if ~isempty(outDir) && ~exist(outDir, 'dir')
    mkdir(outDir);
end
save(outMat, 'F', 'meta', '-v7');
fprintf(1, '[structure oracle] wrote %s (F=%s)\n', outMat, mat2str(size(F)));

end
