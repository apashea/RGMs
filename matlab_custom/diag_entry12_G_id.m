p = 'C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\fixtures\DEMAtariIII_entry12_rgms_canonical_12H.mat';
S = load(p);
ch = S.PDP.MDP;
disp('id.D');
if isfield(ch,'id') && isfield(ch.id,'D'), disp(ch.id.D); end
disp('id.E');
if isfield(ch,'id') && isfield(ch.id,'E'), disp(ch.id.E); end
disp('numel G');
if isfield(ch,'G'), disp(numel(ch.G)); end
