tag = 'rgms_canonical';
p = fullfile('tests','oracle','toolbox','DEM','fixtures',sprintf('DEMAtariIII_entry12_%s_12F.mat',tag));
S = load(p);
snap = S.out_t1;
if iscell(snap), snap = snap{1}; end
par = snap.MDP;
if iscell(par), par = par{1}; end
ch = par.MDP;
if iscell(ch), ch = ch{1}; end
id = ch.id;
fprintf('isfield ff=%d fg=%d\n', isfield(id,'ff'), isfield(id,'fg'));
fprintf('id.A{2}='); disp(id.A{2});
fprintf('j{2,1}='); disp(ch.j{2,1});
Nf = numel(ch.X);
Qrow = cell(Nf,1);
for f = 1:Nf
    Qrow{f} = ch.X{f}(:,1);
end
[j,i] = spm_parents(id, 2, Qrow);
fprintf('spm_parents j='); disp(j);
Y21 = ch.Y{2,1};
[~,pk]=max(Y21(:)); fprintf('Y peak %d\n', pk);
