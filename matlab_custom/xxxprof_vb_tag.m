function xxxprof_vb_tag(tag, mode)
%XXXPROF_VB_TAG  Consolidated MATLAB-side XXX profiling driver (W2).
%
%   xxxprof_vb_tag()                  % call4, profile mode
%   xxxprof_vb_tag('call4','profile')
%   xxxprof_vb_tag('call2','monitor')
%   xxxprof_vb_tag('call4','count')   % requires instrument fork (see XXX_optim.md)
%
% Outputs under matlab_custom/ with prefix xxxprof_<tag>_*
% Authority: matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m (do not edit matlab_src for profiling).
%
% Modes:
%   profile — wall time + full function table + VB-hot filter + HTML + top-40
%   monitor — monitoring=true (12A–12H field inventory diary)
%   count   — operational step counters (instrument fork on path; not yet deployed)
%
% rng(2): structure / call-count runs only — not PDP parity vs Python vb_rand_buf.

if nargin < 1 || isempty(tag)
    tag = 'call4';
end
if nargin < 2 || isempty(mode)
    mode = 'profile';
end

tag = lower(strtrim(char(tag)));
mode = lower(strtrim(char(mode)));

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
fixDir = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures');

rdpName = sprintf('DEMAtariIII_XXX_12_rgms_atari_optim1full_%s_rdp.mat', tag);
rdpMat = fullfile(fixDir, rdpName);
if ~isfile(rdpMat)
    error('RGMs:MissingFixture', 'Missing RDP: %s', rdpMat);
end

prefix = fullfile(here, sprintf('xxxprof_%s', tag));
diaryPath = [prefix '_diary.txt'];
if isfile(diaryPath)
    delete(diaryPath);
end
diary(diaryPath);
diary on;

fprintf(1, '[xxxprof_vb_tag] tag=%s mode=%s matlab=%s\n', tag, mode, version);
fprintf(1, '[xxxprof_vb_tag] rdp=%s\n', rdpMat);

S = load(rdpMat, 'RDP');
if ~isfield(S, 'RDP')
    error('RGMs:BadFixture', 'Expected variable RDP in %s', rdpMat);
end
RDP = S.RDP;

rng(2);
fprintf(1, '[xxxprof_vb_tag] rng=2 dump_subentries=false\n');

switch mode
    case 'profile'
        xxxprof_run_profile_(here, repoRoot, tag, rdpMat, RDP);
    case 'monitor'
        xxxprof_run_monitor_(here, repoRoot, tag, RDP);
    case 'count'
        error('RGMs:NotDeployed', ...
            ['count mode needs matlab_custom/xxxprof/instrument/spm_MDP_VB_XXX.m ', ...
             'on path — see XXX_optim.md § MATLAB-first profiling.']);
    otherwise
        error('RGMs:BadMode', 'Unknown mode %s (use profile | monitor | count)', mode);
end

diary off;
fprintf(1, '[xxxprof_vb_tag] diary=%s\n', diaryPath);
end


function xxxprof_run_profile_(here, repoRoot, tag, rdpMat, RDP)
addpath(genpath(fullfile(repoRoot, 'matlab_src')));

prefix = fullfile(here, sprintf('xxxprof_%s', tag));
topPath = [prefix '_top40.txt'];
fullPath = [prefix '_functions.txt'];
hotPath = [prefix '_vb_hot.txt'];
htmlDir = [prefix '_html'];

if isfile(topPath), delete(topPath); end
if isfile(fullPath), delete(fullPath); end
if isfile(hotPath), delete(hotPath); end
if isfolder(htmlDir), rmdir(htmlDir, 's'); end

fprintf(1, '[xxxprof_vb_tag] monitoring=false\n');

profile clear;
profile('-timer', 'performance');
profile on;
t0 = tic;
spm_MDP_VB_XXX(RDP, struct(), false);
wall_s = toc(t0);
profile off;

fprintf(1, '[xxxprof_vb_tag] spm_MDP_VB_XXX wall_s=%.6f\n', wall_s);

info = profile('info');
n = numel(info.FunctionTable);
totalTime = zeros(n, 1);
selfTime = zeros(n, 1);
numCalls = zeros(n, 1);
names = cell(n, 1);
for i = 1:n
    row = info.FunctionTable(i);
    totalTime(i) = row.TotalTime;
    if isfield(row, 'SelfTime') && ~isempty(row.SelfTime)
        selfTime(i) = row.SelfTime;
    else
        selfTime(i) = totalTime(i);
    end
    numCalls(i) = row.NumCalls;
    names{i} = row.FunctionName;
end
[~, ord] = sort(totalTime, 'descend');

xxxprof_write_table_(topPath, wall_s, rdpMat, ord, totalTime, selfTime, numCalls, names, min(n, 40), 'top-40');
xxxprof_write_table_(fullPath, wall_s, rdpMat, ord, totalTime, selfTime, numCalls, names, n, 'all functions');

hotMask = false(n, 1);
needles = {'spm_MDP_VB_XXX', 'spm_forwards', 'spm_VBX', 'spm_induction', ...
    'spm_dot', 'spm_parents', 'spm_MDP_checkX', 'spm_MDP_get_M', 'spm_kron', ...
    'spm_softmax', 'spm_sample', 'spm_action'};
for i = 1:n
    nm = names{i};
    for j = 1:numel(needles)
        if contains(nm, needles{j})
            hotMask(i) = true;
            break;
        end
    end
end
hotIdx = find(hotMask);
[~, hotOrdLocal] = sort(totalTime(hotIdx), 'descend');
hotOrd = hotIdx(hotOrdLocal);
xxxprof_write_table_(hotPath, wall_s, rdpMat, hotOrd, totalTime, selfTime, numCalls, names, numel(hotOrd), 'VB-hot filter');

if ~isfolder(htmlDir), mkdir(htmlDir); end
profsave(info, htmlDir);

fprintf(1, '[xxxprof_vb_tag] wrote %s\n', topPath);
fprintf(1, '[xxxprof_vb_tag] wrote %s\n', fullPath);
fprintf(1, '[xxxprof_vb_tag] wrote %s\n', hotPath);
fprintf(1, '[xxxprof_vb_tag] wrote html %s\n', htmlDir);
end


function xxxprof_run_monitor_(here, repoRoot, tag, RDP)
addpath(genpath(fullfile(repoRoot, 'matlab_src')));

prefix = fullfile(here, sprintf('xxxprof_%s', tag));
monPath = [prefix '_monitor.txt'];
if isfile(monPath), delete(monPath); end

fprintf(1, '[xxxprof_vb_tag] monitoring=true (12A–12H inventory)\n');

diary off;
diary(monPath);
diary on;

t0 = tic;
spm_MDP_VB_XXX(RDP, struct(), true);
wall_s = toc(t0);

fprintf(1, '[xxxprof_vb_tag] monitor wall_s=%.6f\n', wall_s);
fprintf(1, '[xxxprof_vb_tag] monitor log=%s\n', monPath);

diary off;
diary on;
end


function xxxprof_write_table_(path, wall_s, rdpMat, ord, totalTime, selfTime, numCalls, names, K, label)
fid = fopen(path, 'w');
if fid < 0
    error('RGMs:IO', 'Cannot write %s', path);
end
c = onCleanup(@() fclose(fid));
fprintf(fid, '# xxxprof_vb_tag %s (sort=TotalTime desc)\n', label);
fprintf(fid, '# wall_s=%.6f matlab_release=%s\n', wall_s, version);
fprintf(fid, '# rdp_mat=%s\n', rdpMat);
fprintf(fid, '#\n');
fprintf(fid, '# %-8s %-14s %-14s %-10s  %s\n', 'rank', 'total_s', 'self_s', 'ncalls', 'function');
for r = 1:K
    i = ord(r);
    fprintf(fid, '  %-8d %-14.6f %-14.6f %-10d  %s\n', ...
        r, totalTime(i), selfTime(i), numCalls(i), names{i});
end
end
