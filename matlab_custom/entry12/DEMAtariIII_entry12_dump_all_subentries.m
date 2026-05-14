function DEMAtariIII_entry12_dump_all_subentries()
%DEMATARIII_ENTRY12_DUMP_ALL_SUBENTRIES  Single MATLAB runner for Entry 12 spine capture.
%
% One execution writes **12A.mat … 12I.mat** (same runTag) under the output directory:
%
% * **12A** — post-``spm_MDP_checkX`` inputs to VB
% * **12B–12I** — emitted by ``spm_MDP_VB_XXX_entry12_dump`` (instrumented fork)
%
% Environment (optional):
%   RGMS_ENTRY12_CAPTURE_RUN_TAG   — filename token (default: default)
%   RGMS_ENTRY12_CAPTURE_OUT_DIR   — output directory (default: matlab_custom/entry12/out)
%   RGMS_ENTRY12_CAPTURE_RDP_MAT   — load RDP from this .mat (default: ../saved_rdp_DEM_AtariIII.mat)
%
% Prerequisites: SPM / ``matlab_src`` DEM toolbox on path; ``saved_rdp_DEM_AtariIII.mat``
% from ``matlab_custom/dump_rdp_DEM_AtariIII.m`` unless override path is set. Use that
% canonical dump as-is (no MATLAB-side mutation of ``RDP`` before ``spm_MDP_checkX``).

here = fileparts(mfilename('fullpath'));

tag = getenv('RGMS_ENTRY12_CAPTURE_RUN_TAG');
if isempty(tag)
    tag = 'default';
end

outDir = getenv('RGMS_ENTRY12_CAPTURE_OUT_DIR');
if isempty(outDir)
    outDir = fullfile(here, 'out');
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

rdpMat = getenv('RGMS_ENTRY12_CAPTURE_RDP_MAT');
if isempty(rdpMat)
    rdpMat = fullfile(fileparts(here), 'saved_rdp_DEM_AtariIII.mat');
end
if ~exist(rdpMat, 'file')
    error('RDP mat not found: %s\nSet RGMS_ENTRY12_CAPTURE_RDP_MAT or run dump_rdp_DEM_AtariIII.m', rdpMat);
end

S = load(rdpMat, 'RDP');
if ~isfield(S, 'RDP')
    error('File must contain variable RDP: %s', rdpMat);
end
RDP = S.RDP;

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

dumpSpec = struct('enabled', true, 'outDir', outDir, 'runTag', tag);

spm_MDP_VB_XXX_entry12_dump(MDP, OPTIONS, dumpSpec);

fprintf(1, '[entry12 dump] complete (12A–12I under %s, tag=%s)\n', outDir, tag);

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
