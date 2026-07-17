function DEMAtariIII_optim1full_post_sort_oracle_capture()
%DEMATARIII_OPTIM1FULL_POST_SORT_ORACLE_CAPTURE  Attractors post-sort plot oracle.
%
% Produces MATLAB-native ``u`` / ``I`` / ``HID`` + PNG for OPTIM1FULL §13
% ``dem_attractors_mdp_post_sort``. Mirrors ``DEM_AtariIII.m`` L188–206 on the
% authority payload (``b1``, ``hid``) — not PDP / 12PLOT.
%
% Inputs (paths via env, same keys as spine ``--refresh-oracle``):
%   RGMS_ENTRY12_12PLOT_PDP_MAT     — MATLAB-owned fence payload (``…_matlab_payload.mat``)
%   RGMS_ENTRY12_12PLOT_ORACLE_MAT  — output ``…_dem_attractors_mdp_post_sort_oracle.mat``
%   RGMS_ENTRY12_12PLOT_VIS_DIR     — optional PNG dir
%   RGMS_ENTRY12_12PLOT_FIGURE_TITLE — optional (default Attractors)
%
% See Atari_plotting.md § Plot porting contract and OPTIM1FULL.md policy B.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

payloadMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(payloadMat)
    error('RGMS_ENTRY12_12PLOT_PDP_MAT unset (need MATLAB-owned dem_attractors_mdp_post_sort payload).');
end
if ~exist(payloadMat, 'file')
    error('payload mat not found: %s', payloadMat);
end

outMat = getenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT');
if isempty(outMat)
    error('RGMS_ENTRY12_12PLOT_ORACLE_MAT unset (need dem_attractors_mdp_post_sort oracle path).');
end

visDir = getenv('RGMS_ENTRY12_12PLOT_VIS_DIR');
if isempty(visDir)
    visDir = fullfile(repoRoot, 'visualizations');
end
if ~exist(visDir, 'dir')
    mkdir(visDir);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));
% Prefer installed SPM for spm_svd / eig / figure helpers when present.
spmRoot = 'C:\Users\andre\Documents\MATLAB\spm-main';
if exist(spmRoot, 'dir')
    addpath(genpath(spmRoot));
end

S = load(payloadMat);
if ~isfield(S, 'b1') || ~isfield(S, 'hid')
    error('post_sort payload missing b1/hid: %s', payloadMat);
end
b1  = double(S.b1);
hid = double(S.hid(:))';

figTitle = getenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE');
if isempty(figTitle)
    figTitle = 'Attractors';
end
spm_figure('GetWin', figTitle);
clf
subplot(2, 2, 3)
u = spm_dir_orbits(b1, hid, 64);

% paths to hits (threshold > 0) — DEM_AtariIII.m L194–205
subplot(2, 2, 4)
B     = sum(b1, 3) > 0;
Ns    = size(B, 1);
Nt    = 32;
h     = sparse(1, hid, 1, 1, Ns);
I     = zeros(Nt, Ns);
for t = 1:Nt
    I(t, :) = h;
    h       = (h + h * B) > 0;
end
imagesc(I), hold on
plot(hid, zeros(size(hid)) + 1/2, 'or', 'MarkerSize', 8), hold off
title('Paths to hits', 'FontSize', 14)
xlabel('latent states'), ylabel('time steps'), axis square
drawnow

HID = hid(:)';

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
pngPath = fullfile(visDir, ['AtariIII_optim1full_post_sort_oracle_' ts '.png']);
try
    saveas(gcf, pngPath);
catch
    print(gcf, pngPath, '-dpng');
end
fprintf(1, '[post_sort oracle] wrote PNG %s\n', pngPath);

meta = struct();
meta.site_id = 'dem_attractors_mdp_post_sort';
meta.kind = 'post_sort_orbits';
meta.capture_script = mfilename('fullpath');
meta.payload_source_mat = payloadMat;
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
fprintf(1, '[post_sort oracle] wrote %s (u=%s I=%s HID=%d)\n', ...
    outMat, mat2str(size(u)), mat2str(size(I)), numel(HID));

end
