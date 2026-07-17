function DEMAtariIII_optim1full_basin_oracle_capture()
%DEMATARIII_OPTIM1FULL_BASIN_ORACLE_CAPTURE  Attractors basin plot oracle (final series).
%
% Produces MATLAB-native ``NS``…``NH`` + PNG for OPTIM1FULL §13 ``dem_attractors_basin``.
% Does **not** call ``spm_show_RGB`` / 12PLOT — mirrors ``DEM_AtariIII.m`` Attractors
% illustrate numerics on the final accumulated series (authority payload, not PDP):
%   subplot(4,2,1), plot(NS) ... subplot(4,2,4), plot(NO)
%
% Inputs (paths via env, same keys as spine ``--refresh-oracle`` where applicable):
%   RGMS_ENTRY12_12PLOT_PDP_MAT     — MATLAB-owned fence payload (``…_matlab_payload.mat``)
%                                     (env name reused; file is payload, not PDP)
%   RGMS_ENTRY12_12PLOT_ORACLE_MAT  — output ``…_dem_attractors_basin_oracle.mat``
%   RGMS_ENTRY12_12PLOT_VIS_DIR     — optional PNG dir
%   RGMS_ENTRY12_12PLOT_FIGURE_TITLE — optional (default Attractors)
%
% See Atari_plotting.md § Plot porting contract (``dem_attractors_basin``) and OPTIM1FULL.md W1.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

payloadMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(payloadMat)
    error('RGMS_ENTRY12_12PLOT_PDP_MAT unset (need MATLAB-owned dem_attractors_basin payload).');
end
if ~exist(payloadMat, 'file')
    error('payload mat not found: %s', payloadMat);
end

outMat = getenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT');
if isempty(outMat)
    error('RGMS_ENTRY12_12PLOT_ORACLE_MAT unset (need dem_attractors_basin oracle path).');
end

visDir = getenv('RGMS_ENTRY12_12PLOT_VIS_DIR');
if isempty(visDir)
    visDir = fullfile(repoRoot, 'visualizations');
end
if ~exist(visDir, 'dir')
    mkdir(visDir);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));

S = load(payloadMat);
for key = {'NS', 'NU', 'NA', 'NO', 'NH'}
    if ~isfield(S, key{1})
        error('basin payload missing %s: %s', key{1}, payloadMat);
    end
end
NS = S.NS(:).';
NU = S.NU(:).';
NA = S.NA(:).';
NO = S.NO(:).';
NH = S.NH(:).';

figTitle = getenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE');
if isempty(figTitle)
    figTitle = 'Attractors';
end
spm_figure('GetWin', figTitle);
clf
subplot(4, 2, 1), plot(NS), title('Deep states'),      axis square
subplot(4, 2, 2), plot(NU), title('Deep paths'),       axis square
subplot(4, 2, 3), plot(NA), title('Childless states'), axis square, hold on
subplot(4, 2, 3), plot(NH), title('Childless states'), axis square, hold off
subplot(4, 2, 4), plot(NO), title('Orphan states'),    axis square
drawnow

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
pngPath = fullfile(visDir, ['AtariIII_optim1full_basin_oracle_' ts '.png']);
try
    saveas(gcf, pngPath);
catch
    print(gcf, pngPath, '-dpng');
end
fprintf(1, '[basin oracle] wrote PNG %s\n', pngPath);

meta = struct();
meta.site_id = 'dem_attractors_basin';
meta.kind = 'basin_series';
meta.capture_script = mfilename('fullpath');
meta.payload_source_mat = payloadMat;
meta.png_path = pngPath;
meta.timestamp = ts;
meta.matlab_release = version;
meta.figure_title = figTitle;
meta.numeric_keys = {'NS', 'NU', 'NA', 'NO', 'NH'};

outDir = fileparts(outMat);
if ~isempty(outDir) && ~exist(outDir, 'dir')
    mkdir(outDir);
end
save(outMat, 'NS', 'NU', 'NA', 'NO', 'NH', 'meta', '-v7');
fprintf(1, '[basin oracle] wrote %s (len=%d)\n', outMat, numel(NS));

end
