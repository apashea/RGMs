% Read MATLAB-captured 12F out_tT MDP.F from canonical subentry mat.
tag = getenv('RGMS_ENTRY12_RUN_TAG');
if isempty(tag)
    tag = 'rgms_canonical';
end
p = fullfile(fileparts(mfilename('fullpath')), '..', 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures', ...
    sprintf('DEMAtariIII_entry12_%s_12F.mat', tag));
S = load(p);
% bundle layout: workspace.out_tT.MDP.F or similar
fprintf('top keys: %s\n', strjoin(fieldnames(S), ', '));
if isfield(S, 'workspace')
    W = S.workspace;
elseif isfield(S, 'F12')
    W = S.F12;
else
    W = S;
end
if isfield(W, 'out_tT')
    snap = W.out_tT;
else
    fn = fieldnames(W);
    snap = W.(fn{1});
end
F = snap.MDP.F;
fprintf('F size %s, class %s\n', mat2str(size(F)), class(F));
fprintf('F(1:5) = ');
disp(F(1:min(5,numel(F))));
