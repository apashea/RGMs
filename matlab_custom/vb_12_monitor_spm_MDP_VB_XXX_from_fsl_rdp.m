% vb_12_monitor_spm_MDP_VB_XXX_from_fsl_rdp.m
%
% One FSL RDP run of spm_MDP_VB_XXX with monitoring=true. All fprintf(1,...)
% from VB subentry bands 12A-12H are captured via diary to:
%   matlab_custom/vb_12_monitor_spm_MDP_VB_XXX_from_fsl_rdp_output.txt
%
% Input:  tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat (RDP)
% Does not write PDP .mat (use dump_pdp_DEM_AtariIII_XXX_12_from_fsl_rdp.m for that).

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(genpath(fullfile(repoRoot, 'matlab_custom')));

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

outTxt = fullfile(here, [mfilename '_output.txt']);
if isfile(outTxt)
    delete(outTxt);
end
diary(outTxt);
diary on;
fprintf(1, '[VB monitor run] script=%s\n', mfilename);
fprintf(1, '[VB monitor run] source_rdp_mat=%s\n', inMat);
fprintf(1, '[VB monitor run] matlab_release=%s\n', version);

tic;
PDP = spm_MDP_VB_XXX(RDP, [], true);
wall_s = toc;
fprintf(1, '[VB monitor run] spm_MDP_VB_XXX wall_s=%.6f\n', wall_s);

diary off;

fprintf(1, '[VB monitor run] wrote log: %s\n', outTxt);
