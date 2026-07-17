function demo1_save_if_missing(matPath, varargin)
%DEMO1_SAVE_IF_MISSING  Save only when ``matPath`` does not exist (conditional dump).
%
% Variable names are resolved in the *caller* workspace (same as inline ``save``).
if ~isfile(matPath)
    n = numel(varargin);
    vars = cell(1, n);
    for k = 1:n
        vars{k} = evalin('caller', varargin{k});
    end
    S = cell2struct(vars, varargin, 2);
    save(matPath, '-struct', 'S', '-v7');
    fprintf(1, '[DEMO1 dump] wrote %s\n', matPath);
else
    fprintf(1, '[DEMO1 dump] skip write (exists): %s\n', matPath);
end
end
