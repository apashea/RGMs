% script for fully inspecting loaded MATLAB-native .mat objects


function inspect_RDP_PDP()
% Inspect RDP and PDP structures saved from DEM_AtariIII.
% Recursively prints all fields, sizes, and classes for deep understanding.

    %----------------------------------------------------------------------
    % 1. Filenames (edit if needed)
    %----------------------------------------------------------------------
    inspect_dir = fileparts(mfilename('fullpath'));
    rdp_mat  = fullfile(inspect_dir, 'DEMAtariIII_RDP_before_fourth_spm_MDP_VB_XXX_debug.mat');
    pdp_mat  = fullfile(inspect_dir, 'DEMAtariIII_PDP_after_fourth_spm_MDP_VB_XXX_debug.mat');

    fprintf('Working directory: %s\n', inspect_dir);
    fprintf('RDP MAT file:      %s\n', rdp_mat);
    fprintf('PDP MAT file:      %s\n\n', pdp_mat);

    %----------------------------------------------------------------------
    % 2. Load RDP and PDP
    %----------------------------------------------------------------------
    if ~isfile(rdp_mat)
        error('RDP MAT file not found: %s', rdp_mat);
    end
    if ~isfile(pdp_mat)
        error('PDP MAT file not found: %s', pdp_mat);
    end

    fprintf('Loading RDP from %s\n', rdp_mat);
    data_rdp = load(rdp_mat, 'RDP');
    RDP = data_rdp.RDP;

    fprintf('Loading PDP from %s\n\n', pdp_mat);
    data_pdp = load(pdp_mat, 'PDP');
    PDP = data_pdp.PDP;

    %----------------------------------------------------------------------
    % 3. Top-level summary via whos
    %----------------------------------------------------------------------
    fprintf('=== TOP-LEVEL SUMMARY ===\n');
    fprintf('RDP:\n');
    whos RDP
    fprintf('\nPDP:\n');
    whos PDP
    fprintf('\n');

    %----------------------------------------------------------------------
    % 4. Recursive inspection
    %----------------------------------------------------------------------
    maxDepth = 6;          % increase if you want deeper recursion
    maxArrayPrint = 5;     % only print size/class for arrays; not contents

    fprintf('=== RECURSIVE STRUCTURE OF RDP ===\n');
    inspect_any(RDP, 'RDP', 0, maxDepth, maxArrayPrint);
    fprintf('\n');

    fprintf('=== RECURSIVE STRUCTURE OF PDP ===\n');
    inspect_any(PDP, 'PDP', 0, maxDepth, maxArrayPrint);
    fprintf('\n');

end

%==========================================================================

function inspect_any(x, name, level, maxDepth, maxArrayPrint)
% Recursively inspect variable x, with given display name and indentation.
% - name:   string label to print
% - level:  current recursion depth
% - maxDepth: maximum depth to recurse
% - maxArrayPrint: controls behavior for large numeric arrays

    indent = repmat('  ', 1, level);

    % Basic info for this node
    sz = size(x);
    sz_str = sprintf('%dx', sz);
    sz_str = sz_str(1:end-1);  % remove trailing 'x'

    fprintf('%s%s: class=%s, size=%s\n', indent, name, class(x), sz_str);

    if level >= maxDepth
        fprintf('%s  [max depth reached]\n', indent);
        return;
    end

    % Struct
    if isstruct(x)
        fn = fieldnames(x);
        for i = 1:numel(x)
            idxName = '';
            if numel(x) > 1
                idxName = sprintf('(%d)', i);
            end
            for k = 1:numel(fn)
                fieldName = fn{k};
                fieldVal  = x(i).(fieldName);
                childName = sprintf('%s%s.%s', name, idxName, fieldName);
                inspect_any(fieldVal, childName, level+1, maxDepth, maxArrayPrint);
            end
        end

    % Cell array
    elseif iscell(x)
        for i = 1:numel(x)
            [i1, i2, i3] = ind2sub(size(x), i);
            if ndims(x) == 2
                idxName = sprintf('{%d,%d}', i1, i2);
            elseif ndims(x) == 1
                idxName = sprintf('{%d}', i1);
            else
                idxName = sprintf('{%d,%d,%d}', i1, i2, i3);
            end
            childName = sprintf('%s%s', name, idxName);
            inspect_any(x{i}, childName, level+1, maxDepth, maxArrayPrint);
        end

    % Numeric / logical / char / string: just show type/size
    elseif isnumeric(x) || islogical(x) || ischar(x) || isstring(x)
        % For dense arrays, we only printed size/class above.
        % You can uncomment below to peek at small ones:
        %
        % if numel(x) <= maxArrayPrint
        %     fprintf('%s  value: ', indent);
        %     disp(x);
        % end

    % Other types (e.g., function_handle, table, etc.)
    else
        % Already printed class/size; if you want more, extend here.
    end
end