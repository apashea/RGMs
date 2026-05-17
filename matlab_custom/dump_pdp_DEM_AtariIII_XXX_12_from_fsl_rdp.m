% dump_pdp_DEM_AtariIII_XXX_12_from_fsl_rdp.m
%
% Ledger line (Atari_example.md staged fence): PDP = spm_MDP_VB_XXX(RDP);
% Input RDP: FSL 1-11 fixture (same file as Validation 1-11 MATLAB side).
%
% Input:  tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat  (variable RDP)
% Output: tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_pdp.mat    (PDP, meta), MAT v7
%
% Requires SPM on the MATLAB path (same as matlab_custom/dump_rdp_DEM_AtariIII_FSL_1_11.m).

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
fixtures = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
inMat = fullfile(fixtures, 'DEMAtariIII_fsl_1_11_rdp.mat');
if ~isfile(inMat)
    error('RGMs:MissingFixture', 'Missing FSL RDP mat: %s', inMat);
end
S = load(inMat, 'RDP');
if ~isfield(S, 'RDP')
    error('RGMs:BadFixture', 'Expected variable RDP in %s', inMat);
end
RDP = S.RDP;

tic;
PDP = spm_MDP_VB_XXX(RDP);
wall_s = toc;
fprintf(1, '[MATLAB PDP dump] spm_MDP_VB_XXX wall_s=%.6f\n', wall_s);

outMat = fullfile(fixtures, 'DEMAtariIII_XXX_12_pdp.mat');
meta = struct();
meta.capture_script = mfilename;
meta.source_rdp_mat = inMat;
meta.wall_s = wall_s;
meta.matlab_release = version;

save(outMat, 'PDP', 'meta', '-v7');
fprintf(1, '[MATLAB PDP dump] wrote %s\n', outMat);
