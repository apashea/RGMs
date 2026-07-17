function DEMAtariIII_optim1full_orbits_oracle_capture()
%DEMATARIII_OPTIM1FULL_ORBITS_ORACLE_CAPTURE  Orbits before/after plot oracle.
%
% Produces MATLAB-native ``u`` / ``I`` / ``HID`` + PNG for OPTIM1FULL §13
% ``dem_orbits_before`` or ``dem_orbits_after``. Mirrors ``DEM_AtariIII.m``
% L354–373 / L406–425 on the MATLAB-owned call3/call4 fence PDP.
%
% Inputs (env, same keys as spine ``--refresh-oracle``):
%   RGMS_ENTRY12_12PLOT_PDP_MAT      — MATLAB-owned fence PDP (sibling rgb matlab_pdp)
%   RGMS_ENTRY12_12PLOT_ORACLE_MAT   — output ``…_dem_orbits_{before,after}_oracle.mat``
%   RGMS_ENTRY12_12PLOT_VIS_DIR      — optional PNG dir
%   RGMS_ENTRY12_12PLOT_FIGURE_TITLE — optional (default Orbits)
%   RGMS_OPTIM1FULL_ORBITS_SITE_ID   — ``dem_orbits_before`` or ``dem_orbits_after``
%
% See Atari_plotting.md § Plot porting contract and OPTIM1FULL.md policy B.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

siteId = getenv('RGMS_OPTIM1FULL_ORBITS_SITE_ID');
if isempty(siteId)
    error('RGMS_OPTIM1FULL_ORBITS_SITE_ID unset (need dem_orbits_before or dem_orbits_after).');
end
siteId = strtrim(siteId);

pdpMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(pdpMat)
    error('RGMS_ENTRY12_12PLOT_PDP_MAT unset (need MATLAB-owned orbits fence PDP).');
end
if ~exist(pdpMat, 'file')
    error('PDP mat not found: %s', pdpMat);
end

outMat = getenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT');
if isempty(outMat)
    error('RGMS_ENTRY12_12PLOT_ORACLE_MAT unset (need dem_orbits_* oracle path).');
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

    S_pdp = load(pdpMat, 'PDP');
    PDP = S_pdp.PDP;

HID = PDP.id.hid(:);
B1  = double(PDP.B{1});

figTitle = getenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE');
if isempty(figTitle)
    figTitle = 'Orbits';
end
spm_figure('GetWin', figTitle);
clf

if strcmp(siteId, 'dem_orbits_before')
    orbitsSub = 1;
    pathsSub  = 3;
    pathsTitle = 'Paths to hits (before)';
elseif strcmp(siteId, 'dem_orbits_after')
    orbitsSub = 2;
    pathsSub  = 4;
    pathsTitle = 'Paths to hits (after)';
else
    error('unsupported orbits site_id: %s', siteId);
end

subplot(2, 2, orbitsSub)
u = spm_dir_orbits(B1, HID, 64);

% paths to hits (threshold 1/32) — DEM_AtariIII.m L360–372 / L412–424
subplot(2, 2, pathsSub)
B     = sum(B1, 3) > 1/32;
Ns    = size(B, 1);
Nt    = 32;
h     = sparse(1, HID, 1, 1, Ns);
I     = zeros(Nt, Ns);
for t = 1:Nt
    I(t, :) = h;
    h       = (h + h * B) > 0;
end
imagesc(I), hold on
plot(HID, zeros(size(HID)) + 1/2, 'or', 'MarkerSize', 8), hold off
title(pathsTitle, 'FontSize', 14)
xlabel('latent states'), ylabel('time steps'), axis square
drawnow

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
pngPath = fullfile(visDir, ['AtariIII_optim1full_' siteId '_oracle_' ts '.png']);
try
    saveas(gcf, pngPath);
catch
    print(gcf, pngPath, '-dpng');
end
fprintf(1, '[orbits oracle] wrote PNG %s\n', pngPath);

meta = struct();
meta.site_id = siteId;
meta.kind = 'orbits_figure';
meta.capture_script = mfilename('fullpath');
meta.payload_source_mat = pdpMat;
meta.png_path = pngPath;
meta.timestamp = ts;
meta.matlab_release = version;
meta.figure_title = figTitle;
meta.numeric_keys = {'u', 'I', 'HID'};

outDir = fileparts(outMat);
if ~isempty(outDir) && ~exist(outDir, 'dir')
    mkdir(outDir);
end
save(outMat, 'u', 'I', 'HID', 'meta', '-v7');
fprintf(1, '[orbits oracle] wrote %s (u=%s I=%s HID=%d)\n', ...
    outMat, mat2str(size(u)), mat2str(size(I)), numel(HID));

end
