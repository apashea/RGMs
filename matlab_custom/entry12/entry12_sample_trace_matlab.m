function varargout = entry12_sample_trace_matlab(cmd, varargin)
%ENTRY12_SAMPLE_TRACE_MATLAB Paired spm_sample trace during Entry 12 dump VB (1b).
%
%   entry12_sample_trace_matlab('reset')
%   entry12_sample_trace_matlab('set_t', t)
%   entry12_sample_trace_matlab('log', P, out_i)
%   path = entry12_sample_trace_matlab('finalize', tag, outDir)
%
% Rows match Python ``entry12_draw_index_audit.py`` schema (seq, site, pattern, …).
% ``n_draws`` = scalar ``rand()`` in native MATLAB ``spm_sample`` (logical → 0).
% ``n_draws_py_parity`` = draws Python ``_spm_sample`` would take on same ``P``.

global rgms_entry12_trace_rows rgms_entry12_trace_t_gen rgms_entry12_vb_depth
global rgms_entry12_trace_pu_len

if nargin < 1
    error('entry12_sample_trace_matlab: missing command');
end

switch lower(strtrim(cmd))
    case 'reset'
        global rgms_entry12_trace_active
        rgms_entry12_trace_rows = {};
        rgms_entry12_trace_t_gen = [];
        rgms_entry12_trace_pu_len = [];
        rgms_entry12_trace_active = true;
        if isempty(rgms_entry12_vb_depth)
            rgms_entry12_vb_depth = 0;
        end

    case 'set_t'
        rgms_entry12_trace_t_gen = double(varargin{1});

    case 'set_pu_len'
        rgms_entry12_trace_pu_len = double(varargin{1});

    case 'depth_incr'
        if isempty(rgms_entry12_vb_depth)
            rgms_entry12_vb_depth = 0;
        end
        rgms_entry12_vb_depth = rgms_entry12_vb_depth + 1;

    case 'depth_decr'
        if isempty(rgms_entry12_vb_depth) || rgms_entry12_vb_depth <= 0
            rgms_entry12_vb_depth = 0;
        else
            rgms_entry12_vb_depth = rgms_entry12_vb_depth - 1;
        end

    case 'log'
        if numel(varargin) < 2
            error('entry12_sample_trace_matlab log: need P, out_i');
        end
        P = varargin{1};
        out_i = double(varargin{2});
        if isempty(rgms_entry12_trace_rows)
            rgms_entry12_trace_rows = {};
        end
        seq = numel(rgms_entry12_trace_rows);
        [pat, kMask, kind] = entry12_classify_sample_pattern_(P);
        nMat = entry12_matlab_scalar_draws_(P);
        nPy = entry12_python_parity_draws_(P);
        desc = entry12_describe_sample_input_(P);
        site = entry12_infer_sample_site_();
        depth = 0;
        if ~isempty(rgms_entry12_vb_depth)
            depth = double(rgms_entry12_vb_depth);
        end
        if depth >= 2 && ~any(strcmp(site, {'vb_loop', 'vb_entry', 'unknown'}))
            site = ['nested_' site];
        end
        row = struct( ...
            'seq', seq, ...
            'site', site, ...
            'pattern', pat, ...
            'kind', kind, ...
            'k_mask', kMask, ...
            'draw_start', NaN, ...
            'draw_end', NaN, ...
            'n_draws', nMat, ...
            'n_draws_py_parity', nPy, ...
            'expected_n_draws', entry12_expected_draws_for_pattern_(pat), ...
            'pattern_draw_ok', nPy == entry12_expected_draws_for_pattern_(pat), ...
            'out', out_i, ...
            'depth', depth, ...
            't_gen', rgms_entry12_trace_t_gen);
        row = merge_struct_(row, desc);
        if strcmp(site, 'policy') || strcmp(site, 'nested_policy')
            row.pu_len = rgms_entry12_trace_pu_len;
        end
        rgms_entry12_trace_rows{end + 1} = row; %#ok<AGROW>

    case 'finalize'
        if numel(varargin) < 2
            error('entry12_sample_trace_matlab finalize: need tag, outDir');
        end
        tag = varargin{1};
        outDir = varargin{2};
        if isempty(rgms_entry12_trace_rows)
            rows = {};
        else
            rows = rgms_entry12_trace_rows;
        end
        byPat = struct();
        for k = 1:numel(rows)
            p = rows{k}.pattern;
            if isfield(byPat, p)
                byPat.(p) = byPat.(p) + 1;
            else
                byPat.(p) = 1;
            end
        end
        global rgms_entry12_trace_active
        rgms_entry12_trace_active = false;
        payload = struct();
        payload.tag = tag;
        payload.source = 'matlab_dump_native_spm_sample';
        payload.spm_sample_calls = numel(rows);
        if isempty(rows)
            payload.trace = [];
        else
            traceArr(1) = rows{1};
            for ii = 2:numel(rows)
                traceArr(ii) = rows{ii};
            end
            payload.trace = traceArr;
        end
        payload.trace_summary = struct('by_pattern', byPat);
        path = fullfile(outDir, sprintf('entry12_sample_trace_%s_mat.json', tag));
        txt = jsonencode(payload);
        fid = fopen(path, 'w');
        if fid < 0
            error('Could not write %s', path);
        end
        cleaner = onCleanup(@() fclose(fid));
        fprintf(fid, '%s', txt);
        fprintf(1, '[entry12 trace] tag=%s wrote %s (%d calls)\n', tag, path, numel(rows));
        if nargout > 0
            varargout{1} = path;
        end

    otherwise
        error('entry12_sample_trace_matlab: unknown command %s', cmd);
end
end


function n = entry12_matlab_scalar_draws_(P)
P = entry12_sample_input_full_(P);
if islogical(P)
    n = 0;
else
    n = 1;
end
end


function n = entry12_python_parity_draws_(P)
P = entry12_sample_input_full_(P);
if islogical(P)
    k = nnz(P(:));
    if k == 1
        n = 0;
    elseif k >= 2 && k <= 4
        n = 2;
    else
        n = 1;
    end
else
    n = 1;
end
end


function e = entry12_expected_draws_for_pattern_(pat)
switch pat
    case 'L0'
        e = 0;
    case 'L2'
        e = 2;
    case 'L1'
        e = 1;
    otherwise
        e = 1;
end
end


function Pfull = entry12_sample_input_full_(P)
if issparse(P)
    Pfull = full(P);
else
    Pfull = P;
end
end


function [pat, kMask, kind] = entry12_classify_sample_pattern_(P)
P = entry12_sample_input_full_(P);
if islogical(P)
    kMask = nnz(P(:));
    kind = 'logical';
    if kMask == 1
        pat = 'L0';
    elseif kMask >= 2 && kMask <= 4
        pat = 'L2';
    else
        pat = 'L1';
    end
    return;
end
Pv = double(P(:));
kMask = nnz(Pv);
kind = 'numeric';
total = sum(Pv);
if ~isfinite(total) || total <= 0
    pat = 'N0';
else
    pat = 'N1';
end
end


function desc = entry12_describe_sample_input_(P)
P = entry12_sample_input_full_(P);
desc = struct();
if islogical(P)
    desc.dtype = 'bool';
    desc.is_bool = true;
    desc.is_01_numeric = false;
else
    desc.dtype = class(P);
    desc.is_bool = false;
    Pv = double(P(:));
    desc.is_01_numeric = all((Pv == 0) | (Pv == 1));
end
desc.shape = size(P);
desc.nz = nnz(P);
vh = double(P(1:min(8, numel(P))));
desc.vals_head = vh(:).';
end


function site = entry12_infer_sample_site_()
site = 'unknown';
st = dbstack('-completenames');
for k = 1:min(24, numel(st))
    if ~contains(st(k).file, 'spm_MDP_VB_XXX_entry12_dump.m')
        continue;
    end
    ln = st(k).line;
    if ln >= 875 && ln <= 882
        site = 'policy';
        return;
    end
    if ln >= 860 && ln <= 870
        site = 'gp_path_E';
        return;
    end
    if ln >= 918 && ln <= 926
        site = 'control_P';
        return;
    end
    if ln >= 945 && ln <= 952
        site = 'state_ps';
        return;
    end
    if ln >= 1010 && ln <= 1020
        site = 'outcome_softmax';
        return;
    end
    if ln >= 1038 && ln <= 1048
        site = 'outcome_GP_A';
        return;
    end
    if ln >= 1074 && ln <= 1084
        site = 'outcome_shared_po';
        return;
    end
    if ln >= 755 && ln <= 766
        site = 'outcome_GP_A';
        return;
    end
    if ln >= 1214 && ln <= 1222
        site = 'child_GD';
        return;
    end
    if ln >= 1226 && ln <= 1234
        if ln == 1230
            site = 'child_E';
        else
            site = 'child_D';
        end
        return;
    end
    if ln >= 3455 && ln <= 3465
        site = 'child_spm_action';
        return;
    end
end
end


function s = merge_struct_(a, b)
s = a;
fn = fieldnames(b);
for i = 1:numel(fn)
    s.(fn{i}) = b.(fn{i});
end
end
