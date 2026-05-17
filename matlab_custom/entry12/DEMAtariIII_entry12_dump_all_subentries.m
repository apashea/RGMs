function DEMAtariIII_entry12_dump_all_subentries()
%DEMATARIII_ENTRY12_DUMP_ALL_SUBENTRIES  Entry 12 MATLAB runner (subentry .mat capture).
%
% Loads ``RDP``, saves input ``RDP`` for Validation 12, saves post-checkX **12A**,
% then ``spm_MDP_VB_XXX(..., dump_subentries=true)`` for **12B**–**12I** (instrumented fork).
%
% Environment (optional):
%   RGMS_ENTRY12_CAPTURE_RUN_TAG   — filename token (default: rgms_canonical)
%   RGMS_ENTRY12_CAPTURE_OUT_DIR   — output directory (default: tests/.../fixtures)
%   RGMS_ENTRY12_CAPTURE_RDP_MAT   — load RDP from this .mat (required path)

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

tag = getenv('RGMS_ENTRY12_CAPTURE_RUN_TAG');
if isempty(tag)
    tag = 'rgms_canonical';
end

outDir = getenv('RGMS_ENTRY12_CAPTURE_OUT_DIR');
if isempty(outDir)
    outDir = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

rdpMat = getenv('RGMS_ENTRY12_CAPTURE_RDP_MAT');
if isempty(rdpMat)
    rdpMat = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures', 'DEMAtariIII_fsl_1_11_rdp.mat');
end
if ~exist(rdpMat, 'file')
    error('RDP mat not found: %s\nSet RGMS_ENTRY12_CAPTURE_RDP_MAT', rdpMat);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(here);

S = load(rdpMat, 'RDP');
if ~isfield(S, 'RDP')
    error('File must contain variable RDP: %s', rdpMat);
end
RDP = S.RDP;

rdpOut = fullfile(outDir, 'DEMAtariIII_XXX_12_rdp.mat');
save(rdpOut, 'RDP', '-v7');
fprintf(1, '[entry12 dump] wrote %s\n', rdpOut);

OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

meta = struct();
meta.run_tag = tag;
meta.rdp_source_mat = rdpMat;
meta.capture_script = mfilename('fullpath');
meta.matlab_release = version;
meta.timestamp = datestr(now, 31);
meta.subentry = '12A';

MDP = spm_MDP_checkX(RDP);

fname12A = fullfile(outDir, sprintf('DEMAtariIII_entry12_%s_12A.mat', tag));
save(fname12A, 'MDP', 'OPTIONS', 'meta', '-v7');
fprintf(1, '[entry12 dump] wrote %s\n', fname12A);

kPath = fullfile(outDir, 'entry12_vb_rand_K.mat');
if isfile(kPath)
    Sk = load(kPath);
    K = Sk.K(1);
else
    K = str2double(getenv('RGMS_ENTRY12_VB_RAND_K'));
end
if isnan(K) || K < 0
    error(['Missing VB draw count K. Run: python tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py ', ...
        'or set RGMS_ENTRY12_VB_RAND_K before dump.']);
end
capture_protocol = 'entry12_v5_preamble_rewind';
rgms_entry12_s_pre = rng;
PDP = spm_MDP_VB_XXX(MDP, OPTIONS, false, true);
rng(rgms_entry12_s_pre);
if K > 0
    vb_rand_buf = rand(K, 1);
else
    vb_rand_buf = zeros(0, 1);
end
randOut = fullfile(outDir, 'DEMAtariIII_entry12_vb_matlab_rand_buf.mat');
save(randOut, 'vb_rand_buf', 'K', 'rdpMat', 'tag', 'capture_protocol', '-v7');
fprintf(1, '[entry12 dump] wrote %s (K=%d)\n', randOut, K);

pdpOut = fullfile(outDir, 'DEMAtariIII_XXX_12_pdp.mat');
metaPdp = struct();
metaPdp.capture_script = mfilename;
metaPdp.source_rdp_mat = rdpMat;
metaPdp.run_tag = tag;
save(pdpOut, 'PDP', 'meta', '-v7');
fprintf(1, '[entry12 dump] wrote %s\n', pdpOut);

fprintf(1, '[entry12 dump] complete (12A–12I + RDP + PDP under %s, tag=%s)\n', outDir, tag);

end


function OPTIONS = entry12_default_options_sp_mdp_vb_xxx()
% Defaults aligned with ``spm_MDP_VB_XXX.m`` try/catch option block.

OPTIONS = struct();
try, OPTIONS.B; catch, OPTIONS.B = 0; end
try, OPTIONS.C; catch, OPTIONS.C = 0; end
try, OPTIONS.D; catch, OPTIONS.D = 0; end
try, OPTIONS.N; catch, OPTIONS.N = 0; end
try, OPTIONS.O; catch, OPTIONS.O = 1; end
try, OPTIONS.P; catch, OPTIONS.P = 0; end
try, OPTIONS.Y; catch, OPTIONS.Y = 1; end

end
