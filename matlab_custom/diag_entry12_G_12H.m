p = 'C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\fixtures\DEMAtariIII_entry12_rgms_canonical_12H.mat';
S = load(p);
PDP = S.PDP;
disp(class(PDP));
if isfield(PDP,'T'), fprintf('PDP.T=%g\n',PDP.T); end
if isfield(PDP,'L'), fprintf('PDP.L=%g\n',PDP.L); end
if isfield(PDP,'G')
  disp('top G');
  disp(size(PDP.G));
  if iscell(PDP.G)
    disp(PDP.G{1}(1:min(3,end)));
  end
end
if isfield(PDP,'MDP')
  ch = PDP.MDP;
  disp('child');
  if isfield(ch,'G')
    disp('child G');
    disp(size(ch.G));
    if iscell(ch.G)
      for k=1:min(4,numel(ch.G))
        disp(ch.G{k});
      end
    end
  end
  if isfield(ch,'T'), fprintf('child T=%g\n',ch.T); end
end
