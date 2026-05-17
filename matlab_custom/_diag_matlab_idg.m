load('C:/Users/andre/.cursor/RGMs/tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat');
rdp = RDP;
rdp = spm_MDP_checkX(rdp);
fprintf('numel(rdp.id.g) = %d\n', numel(rdp.id.g));
if numel(rdp.id.g) >= 1
    fprintf('size(rdp.id.g{1}) = ');
    disp(size(rdp.id.g{1}));
end
