% Print id.iH proxy after H init on FSL RDP.
addpath('C:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM', '-begin');
addpath('C:/Users/andre/.cursor/Atari_spm_dependencies', '-begin');
addpath('C:/Users/andre/.cursor/RGMs/matlab_src/toolbox/DEM', '-begin');
load('C:/Users/andre/.cursor/RGMs/tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_rdp.mat');
rdp = spm_MDP_checkX(RDP);
MDP = rdp;
m = 1;
f = 1;
hasH = isfield(MDP, 'H');
hash = isfield(MDP(m), 'h');
disp(['isfield(MDP,H)=', num2str(hasH)]);
disp(['isfield(MDP(m),h)=', num2str(hash)]);
if hash
    qh = MDP(m).h{f};
elseif hasH
    qh = MDP(m).H{f} * 512;
else
    qh = [];
end
Hn = spm_norm(qh);
disp(['numel(qh)=', num2str(numel(qh)), ' numel(Hn)=', num2str(numel(Hn))]);
id_iH = find(arrayfun(@(ff) numel(Hn), 1));
disp(['id_iH=', mat2str(id_iH)]);
