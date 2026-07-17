function optim1full_entry12_rewrite_in_sidecars_for_tag(tag, outDir)
%OPTIM1FULL_ENTRY12_REWRITE_IN_SIDECARS_FOR_TAG  Lean v7 ``*_in.mat`` sidecars (OPTIM1FULL lane).
%
% Shared dump fork saves **12D/12E/12F** ``in`` to v7.3 sidecars. For long-horizon
% Atari VB (OPTIM1FULL ``T=128``), ``F12.in`` retains live references to ``Q``/``P``/``MDP``
% that grow during the loop, producing multi-GB sidecars Python ``loadmat`` cannot read.
%
% This helper rewrites ``*_in.mat`` to a **lean v7** boundary snap (first time column,
% trimmed ``MDP``, inspection keys removed) without changing DEMO1/OPTIM1 dump fork code.
%
% See ``OPTIM1FULL.md`` § Entry 12 OPTIM1FULL forks.

if nargin < 2 || isempty(outDir)
    repoRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
    outDir = optim1full_fixtures_dir(repoRoot);
end
tag = strtrim(char(tag));
bands = {'12D', '12E', '12F'};
for k = 1:numel(bands)
    band = bands{k};
    sidecar = fullfile(outDir, sprintf('DEMAtariIII_entry12_%s_%s_in.mat', tag, band));
    if ~isfile(sidecar)
        fprintf(1, '[optim1full entry12 lean] skip missing %s\n', sidecar);
        continue;
    end
    bak = [sidecar(1:end-4) '_pre_lean_v73.mat'];
    srcPath = sidecar;
    if isfile(bak)
        srcPath = bak;
        fprintf(1, '[optim1full entry12 lean] source %s\n', bak);
    end
    S = load(srcPath);
    if ~isfield(S, 'in')
        fprintf(1, '[optim1full entry12 lean] skip no ''in'' in %s\n', sidecar);
        continue;
    end
    lean = optim1full_entry12_lean_in_snap_(S.in, band);
    in = lean; %#ok<NASGU>
    if ~isfile(bak)
        copyfile(sidecar, bak);
        fprintf(1, '[optim1full entry12 lean] backup %s\n', bak);
    end
    save(sidecar, 'in', '-v7');
    info = whos('-file', sidecar, 'in');
    fprintf(1, '[optim1full entry12 lean] tag=%s band=%s wrote %s (in bytes=%d class=%s)\n', ...
        tag, band, sidecar, info.bytes, info.class);
end
end


function lean = optim1full_entry12_lean_in_snap_(raw, bandCode)
% Reduce bloated pre-loop ``in`` to lean boundary (align with script **3** / Validation **12**).
lean = struct();
if isfield(raw, 't')
    lean.t = raw.t;
else
    lean.t = 0;
end
switch upper(strtrim(bandCode))
    case '12D'
        if isfield(raw, 'Mrow')
            lean.Mrow = raw.Mrow;
        end
        if isfield(raw, 'MDP')
            MdpIn = raw.MDP;
            lean.MDP = optim1full_entry12_trim_mdp_time_(MdpIn, 1);
            lean.MDP = optim1full_entry12_drop_mdp_fields_(lean.MDP, {'A', 'B', 'O', 'o'});
        end
    case '12E'
        % ``E12.in`` is typically ``t`` only at loop entry.
    case '12F'
        if isfield(raw, 'Q')
            Qin = raw.Q;
            lean.Q = optim1full_entry12_qp_at_time_(Qin, 1);
        end
        if isfield(raw, 'P')
            Pin = raw.P;
            lean.P = optim1full_entry12_qp_at_time_(Pin, 1);
        end
        for fn = {'R', 'v', 'w'}
            f = fn{1};
            if isfield(raw, f)
                Xin = raw.(f{1});
                lean.(f) = optim1full_entry12_qp_at_time_(Xin, 1);
            end
        end
        if isfield(raw, 'MDP')
            MdpIn = raw.MDP;
            lean.MDP = optim1full_entry12_drop_mdp_fields_(MdpIn, {'A'});
            lean.MDP = optim1full_entry12_strip_nested_mdp_q_(lean.MDP);
        end
    otherwise
        error('optim1full_entry12_lean_in_snap_: unknown band %s', bandCode);
end
lean = optim1full_entry12_strip_inspection_fields_(lean);
end


function ws = optim1full_entry12_qp_at_time_(ws, tCol)
% ``Q``/``P``/``R``/``v``/``w`` workspace — keep column ``tCol`` when 2-D+.
if iscell(ws)
    out = cell(size(ws));
    for ri = 1:size(ws, 1)
        for ci = 1:size(ws, 2)
            out{ri, ci} = optim1full_entry12_one_qp_at_time_(ws{ri, ci}, tCol);
        end
    end
    ws = out;
else
    ws = optim1full_entry12_one_qp_at_time_(ws, tCol);
end
end


function arr = optim1full_entry12_one_qp_at_time_(arr, tCol)
if isnumeric(arr) || islogical(arr)
    if size(arr, 2) > 1
        j = min(max(tCol, 1), size(arr, 2));
        arr = arr(:, j);
    end
elseif iscell(arr)
    arr = optim1full_entry12_qp_at_time_(arr, tCol);
end
end


function mdp = optim1full_entry12_trim_mdp_time_(mdp, tCol)
% Trim time-indexed **2-D** MDP fields (``o`` modalities × ``T``). Keep ``u``/``s`` full
% horizon vectors — row ``1×T`` must not collapse to a scalar (Validation **12** compare).
if ~iscell(mdp)
    mdp = {mdp};
end
for m = 1:numel(mdp)
    if ~isstruct(mdp{m})
        continue;
    end
    if isfield(mdp{m}, 'o')
        x = mdp{m}.o;
        if isnumeric(x) && ndims(x) == 2 && size(x, 1) > 1 && size(x, 2) > 1
            j = min(max(tCol, 1), size(x, 2));
            mdp{m}.o = x(:, j);
        end
    end
    if isfield(mdp{m}, 'MDP')
        mdp{m}.MDP = optim1full_entry12_trim_mdp_time_(mdp{m}.MDP, tCol);
    end
end
end


function mdp = optim1full_entry12_drop_mdp_fields_(mdp, dropNames)
if ~iscell(mdp)
    mdp = {mdp};
end
for m = 1:numel(mdp)
    if ~isstruct(mdp{m})
        continue;
    end
    for k = 1:numel(dropNames)
        f = dropNames{k};
        if isfield(mdp{m}, f)
            mdp{m} = rmfield(mdp{m}, f);
        end
    end
    if isfield(mdp{m}, 'MDP')
        mdp{m}.MDP = optim1full_entry12_drop_mdp_fields_(mdp{m}.MDP, dropNames);
    end
end
end


function mdp = optim1full_entry12_strip_nested_mdp_q_(mdp)
if ~iscell(mdp)
    mdp = {mdp};
end
for m = 1:numel(mdp)
    if ~isstruct(mdp{m}) || ~isfield(mdp{m}, 'MDP')
        continue;
    end
    child = mdp{m}.MDP;
    if iscell(child)
        for c = 1:numel(child)
            if isstruct(child{c}) && isfield(child{c}, 'Q')
                child{c} = rmfield(child{c}, 'Q');
            end
        end
    elseif isstruct(child) && isfield(child, 'Q')
        child = rmfield(child, 'Q');
    end
    mdp{m}.MDP = child;
end
end


function snap = optim1full_entry12_strip_inspection_fields_(snap)
% Match Python ``ENTRY12_INSPECTION_ONLY_SNAP_KEYS`` (not causal gates).
for f = {'nested_y_summary', 'entry12_prechild', 'entry12_phase_log', ...
        'entry12_forwards', 'entry12_generation'}
    if isfield(snap, f{1})
        snap = rmfield(snap, f{1});
    end
end
end
