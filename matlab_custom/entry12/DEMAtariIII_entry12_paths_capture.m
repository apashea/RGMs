function DEMAtariIII_entry12_paths_capture()
%DEMATARIII_ENTRY12_PATHS_CAPTURE  Paths-to-hits panel oracle (no VB re-run).
%
% Produces ``I`` (reachability matrix) and ``HID`` for validating Python paths
% panel code on frozen Entry **12** ``PDP`` fixtures.
%
% Environment (optional — same PDP/out roots as ``DEMAtariIII_entry12_12plot_capture``):
%   RGMS_ENTRY12_CAPTURE_RUN_TAG
%   RGMS_ENTRY12_CAPTURE_OUT_DIR
%   RGMS_ENTRY12_12PLOT_PDP_MAT
%   RGMS_ENTRY12_PATHS_NT              — default 32
%   RGMS_ENTRY12_PATHS_B_THRESHOLD     — default 1/32
%   RGMS_ENTRY12_PATHS_PANEL_TITLE     — stored in meta only
%   RGMS_ENTRY12_PATHS_OUT_MAT         — optional explicit output .mat path
%
% Output: ``DEMAtariIII_entry12_<tag>_PATHS.mat`` — ``I``, ``HID``, ``meta``

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

pdpMat = getenv('RGMS_ENTRY12_12PLOT_PDP_MAT');
if isempty(pdpMat)
    pdpMat = fullfile(outDir, 'DEMAtariIII_XXX_12_pdp.mat');
end
if ~exist(pdpMat, 'file')
    error('PDP mat not found: %s', pdpMat);
end

ntStr = getenv('RGMS_ENTRY12_PATHS_NT');
if isempty(ntStr)
    ntUse = 32;
else
    ntUse = str2double(ntStr);
end

thrStr = getenv('RGMS_ENTRY12_PATHS_B_THRESHOLD');
if isempty(thrStr)
    thrUse = 1/32;
else
    thrUse = str2double(thrStr);
end

panelTitle = getenv('RGMS_ENTRY12_PATHS_PANEL_TITLE');
if isempty(panelTitle)
    panelTitle = 'Paths to hits';
end

S_pdp = load(pdpMat, 'PDP');
PDP = S_pdp.PDP;

B = sum(PDP.B{1}, 3) > thrUse;
Ns = size(B, 1);
HID = PDP.id.hid;
if iscell(HID)
    if numel(HID) == 1
        HID = HID{1};
    else
        HID = cell2mat(HID(:)');
    end
end
HID = double(HID(:))';
h = sparse(1, HID, 1, 1, Ns);
I = zeros(ntUse, Ns);
for t = 1:ntUse
    I(t, :) = h;
    h = (h + h * B) > 0;
end

ts = datestr(now, 'yyyy-mm-dd-HH-MM-SS');
outMatEnv = getenv('RGMS_ENTRY12_PATHS_OUT_MAT');
if ~isempty(outMatEnv)
    outMat = outMatEnv;
else
    outMat = fullfile(outDir, ['DEMAtariIII_entry12_' tag '_PATHS.mat']);
end
meta = struct();
meta.run_tag = tag;
meta.capture_script = mfilename('fullpath');
meta.pdp_source_mat = pdpMat;
meta.timestamp = ts;
meta.matlab_release = version;
meta.paths_nt = ntUse;
meta.paths_b_threshold = thrUse;
meta.paths_panel_title = panelTitle;

save(outMat, 'I', 'HID', 'meta', '-v7');
fprintf(1, '[paths capture] wrote %s\n', outMat);

end
