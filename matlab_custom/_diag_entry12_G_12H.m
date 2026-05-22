% Inspect PDP.G vs PDP.MDP.G at 12H fixture (rgms_canonical).
repo = fileparts(fileparts(mfilename('fullpath')));
p = fullfile(repo, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures', ...
    'DEMAtariIII_entry12_rgms_canonical_12H.mat');
S = load(p);
PDP = S.PDP;
fprintf('class(PDP)=%s\n', class(PDP));
if isfield(PDP, 'T'), fprintf('PDP.T=%g\n', double(PDP.T)); end
if isfield(PDP, 'L'), fprintf('PDP.L=%g\n', double(PDP.L)); end
if isfield(PDP, 'G')
    fprintf('top G: class=%s\n', class(PDP.G));
    disp(size(PDP.G));
    if iscell(PDP.G) && ~isempty(PDP.G)
        g1 = PDP.G{1};
        fprintf('G{1} class=%s size=', class(g1));
        disp(size(g1));
        disp(g1(1:min(3, numel(g1))));
    end
end
if isfield(PDP, 'MDP')
    ch = PDP.MDP;
    fprintf('child MDP class=%s\n', class(ch));
    if isfield(ch, 'G')
        fprintf('child G class=%s\n', class(ch.G));
        disp(size(ch.G));
        if iscell(ch.G)
            for k = 1:min(4, numel(ch.G))
                fprintf('child G{%d}:\n', k);
                disp(ch.G{k});
            end
        end
    end
    if isfield(ch, 'T'), fprintf('child T=%g\n', double(ch.T)); end
end
