function DEMAtariIII_optim1full_gameplay_oracle_capture()
%DEMATARIII_OPTIM1FULL_GAMEPLAY_ORACLE_CAPTURE  Gameplay plot oracle (final t only).
%
% Produces MATLAB-native ``frame_rgb`` + ``control`` for OPTIM1FULL §13 ``dem_gameplay``.
% Does **not** call ``spm_show_RGB`` / 12PLOT ``J``/``K``/``h`` — mirrors ``DEM_AtariIII.m``
% Gameplay illustrate numerics at one time index (default ``t=128``):
%   frame_rgb = spm_O2rgb(PDP.O(:,t), RGB)
%   control   = PDP.O{con,t}'
%
% Inputs (paths via env, same keys as spine ``--refresh-oracle``):
%   RGMS_ENTRY12_12PLOT_PDP_MAT     — MATLAB-owned fence PDP (``…_matlab_pdp.mat``)
%   RGMS_ENTRY12_12PLOT_CTX_MAT     — ``plot_ctx`` with ``RGB``
%   RGMS_ENTRY12_12PLOT_ORACLE_MAT  — output ``…_dem_gameplay_oracle.mat``
%   RGMS_OPTIM1FULL_GAMEPLAY_FINAL_T — optional 1-based t (default 128)
%   RGMS_ENTRY12_12PLOT_VIS_DIR     — optional PNG dir
%
% See Atari_plotting.md § Plot porting contract (``dem_gameplay``) and OPTIM1FULL.md W1.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

pdpMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(pdpMat)
    error('RGMS_ENTRY12_12PLOT_PDP_MAT unset (need MATLAB-owned dem_gameplay fence PDP).');
end
if ~exist(pdpMat, 'file')
    error('PDP mat not found: %s', pdpMat);
end

ctxMat = getenv('RGMS_ENTRY12_12PLOT_CTX_MAT');
if isempty(ctxMat)
    error('RGMS_ENTRY12_12PLOT_CTX_MAT unset (need optim1full plot_ctx).');
end
if ~exist(ctxMat, 'file')
    error('plot_ctx mat not found: %s', ctxMat);
end

outMat = getenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT');
if isempty(outMat)
    error('RGMS_ENTRY12_12PLOT_ORACLE_MAT unset (need dem_gameplay oracle path).');
end

finalTStr = getenv('RGMS_OPTIM1FULL_GAMEPLAY_FINAL_T');
if isempty(finalTStr)
    finalT = 128;
else
    finalT = str2double(finalTStr);
end
if ~(isfinite(finalT) && finalT >= 1)
    error('invalid RGMS_OPTIM1FULL_GAMEPLAY_FINAL_T=%s', finalTStr);
end
finalT = round(finalT);

visDir = getenv('RGMS_ENTRY12_12PLOT_VIS_DIR');
if isempty(visDir)
    visDir = fullfile(repoRoot, 'visualizations');
end
if ~exist(visDir, 'dir')
    mkdir(visDir);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));

S_pdp = load(pdpMat, 'PDP');
PDP = S_pdp.PDP;
S_ctx = load(ctxMat, 'RGB');
RGB = S_ctx.RGB;

con = PDP.id.control;
t = finalT;
frame_rgb = spm_O2rgb(PDP.O(:, t), RGB);
control = PDP.O{con, t}';

figTitle = getenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE');
if isempty(figTitle)
    figTitle = 'Gameplay';
end
spm_figure('GetWin', figTitle);
clf
subplot(2, 1, 1)
imshow(frame_rgb)
subplot(4, 3, 8)
imshow(control)
drawnow

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
pngPath = fullfile(visDir, ['AtariIII_optim1full_gameplay_oracle_' ts '.png']);
try
    saveas(gcf, pngPath);
catch
    print(gcf, pngPath, '-dpng');
end
fprintf(1, '[gameplay oracle] wrote PNG %s\n', pngPath);

meta = struct();
meta.site_id = 'dem_gameplay';
meta.kind = 'gameplay_o2rgb';
meta.capture_script = mfilename('fullpath');
meta.pdp_source_mat = pdpMat;
meta.plot_ctx_mat = ctxMat;
meta.png_path = pngPath;
meta.timestamp = ts;
meta.matlab_release = version;
meta.figure_title = figTitle;
meta.final_t = finalT;
meta.control_index = double(con);
meta.numeric_keys = {'frame_rgb'; 'control'};

outDir = fileparts(outMat);
if ~isempty(outDir) && ~exist(outDir, 'dir')
    mkdir(outDir);
end
save(outMat, 'frame_rgb', 'control', 'meta', '-v7');
fprintf(1, '[gameplay oracle] wrote %s (t=%d)\n', outMat, finalT);

end
