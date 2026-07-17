function DEMAtariIII_entry12_12plot_capture()
%DEMATARIII_ENTRY12_12PLOT_CAPTURE  ENTRY 12PLOT MATLAB oracle (no VB re-run).
%
% Produces MATLAB-native outputs for validating translated 12PLOT / spm_show_RGB code.
% Does **not** call spm_MDP_VB_XXX — loads canonical Entry 12 ``PDP`` from disk (script 1b).
%
% Inputs (loaded):
%   DEMAtariIII_XXX_12_pdp.mat          — variable ``PDP`` (Entry 12 VB output)
%   DEMAtariIII_fsl_1_11_plot_ctx.mat   — ``RGB``, ``GDP``, ``Nm``, scalars
%
% Outputs:
%   tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_<tag>_12PLOT.mat
%     — ``J``, ``K`` (spm_show_RGB), ``h`` (spm_get_hits), ``meta``, source paths
%   visualizations/AtariIII_12plot_<yyyy-mm-dd-HH-MM-SS>.png — full 12PLOT figure
%
% Environment (optional):
%   RGMS_ENTRY12_CAPTURE_RUN_TAG       — default: rgms_canonical
%   RGMS_ENTRY12_CAPTURE_OUT_DIR       — default: tests/.../fixtures
%   RGMS_ENTRY12_12PLOT_PDP_MAT        — override ``DEMAtariIII_XXX_12_pdp.mat`` path
%   RGMS_ENTRY12_12PLOT_CTX_MAT        — override plot_ctx path
%   RGMS_ENTRY12_12PLOT_VIS_DIR        — default: repoRoot/visualizations
%   RGMS_ENTRY12_12PLOT_FIGURE_TITLE   — default: Generative AI (12PLOT)
%   RGMS_ENTRY12_12PLOT_NT             — optional; when set, pass to spm_show_RGB
%   RGMS_ENTRY12_12PLOT_MOVIE          — optional 0/1; default 1 when NT unset, else 0 if unset
%   RGMS_ENTRY12_12PLOT_HITS_Y         — hits plot y-offset (default 0)
%
% See Atari_plotting.md § Plot artifact registry and Atari_example.md § Entry 12PLOT.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

tag = getenv('RGMS_ENTRY12_CAPTURE_RUN_TAG');
if isempty(tag)
    tag = 'rgms_canonical';
end

outDir = getenv('RGMS_ENTRY12_CAPTURE_OUT_DIR');
if isempty(outDir)
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    outDir = demo1_fixtures_dir(repoRoot);
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

visDir = getenv('RGMS_ENTRY12_12PLOT_VIS_DIR');
if isempty(visDir)
    visDir = fullfile(repoRoot, 'visualizations');
end
if ~exist(visDir, 'dir')
    mkdir(visDir);
end

pdpMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(pdpMat)
    pdpMat = fullfile(outDir, 'DEMAtariIII_XXX_12_pdp.mat');
end
if ~exist(pdpMat, 'file')
    error('PDP mat not found: %s\nRun script 1b first (DEMAtariIII_entry12_dump_all_subentries).', pdpMat);
end

ctxMat = getenv('RGMS_ENTRY12_12PLOT_CTX_MAT');
if isempty(ctxMat)
    ctxMat = fullfile(outDir, 'DEMAtariIII_fsl_1_11_plot_ctx.mat');
end
if ~exist(ctxMat, 'file')
    error('plot_ctx mat not found: %s\nRun dump_rdp_DEM_AtariIII_FSL_1_11.m first.', ctxMat);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));

S_pdp = load(pdpMat, 'PDP');
PDP = S_pdp.PDP;

S_ctx = load(ctxMat, 'RGB', 'GDP', 'Nm');
RGB = S_ctx.RGB;
GDP = S_ctx.GDP;
Nm = S_ctx.Nm;

spm_get_hits = @(o,id) find(o(id.reward,:) > 1);

figTitle = getenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE');
if isempty(figTitle)
    figTitle = 'Generative AI';
end
ntStr = getenv('RGMS_ENTRY12_12PLOT_NT');
movieStr = getenv('RGMS_ENTRY12_12PLOT_MOVIE');
hitsYStr = getenv('RGMS_ENTRY12_12PLOT_HITS_Y');
if isempty(hitsYStr)
    hitsY = 0;
else
    hitsY = str2double(hitsYStr);
end

spm_figure('GetWin', figTitle);
clf
if isempty(ntStr)
    [J, K] = spm_show_RGB(PDP, RGB);
    ntUse = 4;
    movieUse = 1;
else
    ntUse = str2double(ntStr);
    if isempty(movieStr)
        movieUse = 0;
    else
        movieUse = logical(str2double(movieStr));
    end
    [J, K] = spm_show_RGB(PDP, RGB, ntUse, movieUse);
end
h = spm_get_hits(PDP.Q.o{1}, GDP.id);
subplot(Nm + 3, 2, 2*(Nm + 1))
plot(h, zeros(size(h)) + hitsY, '.r', 'MarkerSize', 16)
drawnow

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
pngPath = fullfile(visDir, ['AtariIII_12plot_' ts '.png']);
try
    saveas(gcf, pngPath);
catch
    print(gcf, pngPath, '-dpng');
end
fprintf(1, '[12PLOT capture] wrote PNG %s\n', pngPath);

outMat = fullfile(outDir, ['DEMAtariIII_entry12_' tag '_12PLOT.mat']);
oracleOverride = getenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT');
if ~isempty(oracleOverride)
    outMat = oracleOverride;
end
meta = struct();
meta.run_tag = tag;
meta.capture_script = mfilename('fullpath');
meta.pdp_source_mat = pdpMat;
meta.plot_ctx_mat = ctxMat;
meta.png_path = pngPath;
meta.timestamp = ts;
meta.matlab_release = version;
meta.figure_title = figTitle;
meta.Nt = ntUse;
meta.MOVIE = double(movieUse);
meta.hits_y_offset = hitsY;

save(outMat, 'J', 'K', 'h', 'Nm', 'meta', '-v7');
fprintf(1, '[12PLOT capture] wrote %s\n', outMat);

end
