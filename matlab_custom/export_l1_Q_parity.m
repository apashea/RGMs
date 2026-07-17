addpath(genpath('C:/Users/andre/.cursor/RGMs/matlab_src'));
S = load('C:/Users/andre/.cursor/RGMs/tests/demo1/fixtures/DEMAtariIII_XXX_12_pdp.mat', 'PDP');
PDP = S.PDP;
Y = {};
qy = PDP.Q.Y;
for i = 1:numel(qy)
    Y{i} = qy{i};
end
Y{end+1} = PDP.Y;
O = {};
qo = PDP.Q.O;
for i = 1:numel(qo)
    O{i} = qo{i};
end
O{end+1} = PDP.O;
Nm = numel(O);
n = Nm;
L = Nm - n + 1;
y = Y{L};
iD = (1:size(y, 1))';
Q = spm_cat(y(iD, :));
save('C:/Users/andre/.cursor/RGMs/misc/_tmp_l1_Q.mat', 'Q');
