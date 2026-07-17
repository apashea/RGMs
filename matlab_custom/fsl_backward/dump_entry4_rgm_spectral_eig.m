% dump_entry4_rgm_spectral_eig.m
%
% MATLAB authority dump for Entry 4 spectral ``eig(MI(i,i),'nobalance')`` steps.
% Uses instrumented spm_rgm_group in matlab_custom/fsl_backward/override/ (prepended on path).
%
% Input:  tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.mat
%         (PDP_O columns 1:1000 — same boundary as FSL Entry 4)
% Output: tests/oracle/toolbox/DEM/fixtures/
%   DEMAtariIII_fsl_backward_entry4_rgm_spectral_matlab_eig_records.mat
%   (variables: rgms_entry4_spectral_records, meta)
% Manifest: DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_dump_manifest.json (updated by Python dump)
% Report:   matlab_custom/fsl_backward_entry4_rgm_spectral_eig_dump_output.txt
%
% Does not rerun DEM Entries 1-3; uses ledger PDP_O from rng(2) authority mat.
% See eig.md §7.1.

function dump_entry4_rgm_spectral_eig()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
overrideDir = fullfile(thisDir, 'override');
outDir = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
matIn = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry10.mat');
matOut = fullfile(outDir, 'DEMAtariIII_fsl_backward_entry4_rgm_spectral_matlab_eig_records.mat');
reportPath = fullfile(repoRoot, 'matlab_custom', 'fsl_backward_entry4_rgm_spectral_eig_dump_output.txt');

if ~exist(matIn, 'file')
    error('dump_entry4:missing_input', ...
        'Missing %s — run dump_MDP_pre_entry10.m first.', matIn);
end
if exist(matOut, 'file')
    refresh = getenv('RGMS_ENTRY4_RGM_SPECTRAL_EIG_DUMP_REFRESH');
    if ~ismember(lower(strtrim(refresh)), {'1','true','yes','on'})
        error('dump_entry4:exists', ...
            ['Refusing to overwrite %s. Set RGMS_ENTRY4_RGM_SPECTRAL_EIG_DUMP_REFRESH=1.'], matOut);
    end
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

global rgms_entry4_spectral_records rgms_entry4_rgm_call_id
rgms_entry4_spectral_records = {};
rgms_entry4_rgm_call_id = 0;

% SPM paths first; instrumented spm_rgm_group MUST be last (shadows toolbox copy).
addpath(fullfile(repoRoot, 'matlab_src'));
addpath(fullfile(repoRoot, 'matlab_src', 'toolbox', 'DEM'));
spmDem = 'c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM';
if exist(spmDem, 'dir')
    addpath(spmDem);
end
addpath(overrideDir);
fprintf(1, '[entry4 spectral dump] override spm_rgm_group: %s\n', ...
    fullfile(overrideDir, 'spm_rgm_group.m'));

fprintf(1, '[entry4 spectral dump] load %s\n', matIn);
S = load(matIn, 'PDP_O');
PDP_O = S.PDP_O;

Nr = 12;
Nc = 9;
Sc = 9;
Smat = ones(4, 3);
Smat(1, :) = [Nr, Nc, 1];
Smat(2, :) = [1, 1, 1];
Smat(3, :) = [1, 1, 1];
Smat(4, :) = [1, 1, 1];

o_cols = 1000;
fprintf(1, '[entry4 spectral dump] spm_faster_structure_learning(PDP_O(:,1:%d), ...)\n', o_cols);
MDP = spm_faster_structure_learning(PDP_O(:, 1:o_cols), Smat, Sc);

nrec = numel(rgms_entry4_spectral_records);
fprintf(1, '[entry4 spectral dump] captured %d spectral records, Nm=%d\n', nrec, numel(MDP));

meta = struct();
meta.source = 'dump_entry4_rgm_spectral_eig.m';
meta.artifact_id = 'DEMAtariIII_fsl_backward_entry4_rgm_spectral_matlab_eig_records';
meta.input_mat = matIn;
meta.o_cols = o_cols;
meta.n_records = nrec;
meta.nm = numel(MDP);
meta.date = datestr(now, 31);

% v7 (not v7.3) so Python scipy.io.loadmat can read without h5py.
save(matOut, 'rgms_entry4_spectral_records', 'meta', '-v7');
fprintf(1, '[entry4 spectral dump] wrote %s\n', matOut);

fid = fopen(reportPath, 'a');
if fid > 0
    fprintf(fid, '=== MATLAB eig records dump %s ===\n', meta.date);
    fprintf(fid, 'records=%d Nm=%d\n', nrec, meta.nm);
    fprintf(fid, 'wrote_mat=%s\n', matOut);
    fclose(fid);
end

% Leave override off path after dump (avoid polluting later MATLAB sessions).
if exist('overrideDir', 'var') && exist(overrideDir, 'dir')
    rmpath(overrideDir);
end

end
