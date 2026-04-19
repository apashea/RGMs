% dump_rdp_DEM_chaos_compression.m
% Verbatim copy of spm12/toolbox/DEM/DEM_chaos_compression.m lines 25-96
% (through RDP = spm_RDP_O(RDP,S); ), then save RDP beside this file.
% Requires SPM on path the same way you run the stock demo.

%% set up and preliminaries
%--------------------------------------------------------------------------
rng(1)

% get model of stochastic chaos
%==========================================================================
M    = spm_DEM_M('Lorenz');

% create innovations & add causes
%--------------------------------------------------------------------------
N    = 1024;
U    = sparse(1,N);
DEM  = spm_DEM_generate(M,U);

% show realisation
%==========================================================================
spm_figure('GetWin','Lorenz'); clf
spm_DEM_qU(DEM.pU);

% create a pretty image of Lorenzian trajectories
%--------------------------------------------------------------------------
subplot(2,3,4), hold off
x     = DEM.pU.x{1};
plot(x(1,:),x(2,:),':','Color',[.9 .7 0]), hold on
h = plot(x(1,1),x(2,1),'.w','MarkerSize',64); set(gca,'Color','k')
axis image, axis([-24 24 -24 24])
for t = 1:N
    set(h,'Xdata',x(1,t),'Ydata',x(2,t))
    I(:,:,:,t) = frame2im(getframe(gca));
end

% Map from image to discrete state space (c.f., Amortisation) 
%--------------------------------------------------------------------------
RGB.nd    = 32;                    % Diameter of tiles in pixels
RGB.nb    = 5;                     % Number of discrete singular variates 
RGB.mm    = 16;                    % Maximum number of singular modes
RGB.su    = 16;                    % Variance threshold
RGB.R     = 2;                     % temporal resampling

T         = N/RGB.R;               % number of voxels             
i         = (1:(N/2));             % training set
[O,L,RGB] = spm_rgb2O(I(:,:,:,i),RGB);

% And show the images generated from a discrete representation
%--------------------------------------------------------------------------
subplot(2,2,3)
spm_imshow(I(:,:,:,1:16))
axis on, title('Original image','FontSize',12)
subplot(2,2,4)
spm_imshow(spm_O2rgb(O(:,1:8),RGB))
axis on, title('Discretised image','FontSize',12)

% Use the ensuing sequence for (RG) structure learning
%--------------------------------------------------------------------------
t     = 1:(T/2);
MDP   = spm_MB_structure_learning(O(:,t),L);

% learn from subsequent episodes
%==========================================================================
Nm    = numel(MDP);
FIX.A = 1;                             %  enable likelihood learning
FIX.B = 0;                             % disable transition learning

% active learning
%--------------------------------------------------------------------------
i     = (1:N/2) + N/2 - 64;
S     = spm_rgb2O(I(:,:,:,i),RGB);

RDP   = spm_mdp2rdp(MDP,0,1/512,2,FIX);
RDP.T = fix((T/2)/(2^(Nm - 1)));

RDP   = spm_RDP_O(RDP,S);

outMat = fullfile(fileparts(mfilename('fullpath')),'saved_rdp_DEM_chaos_compression.mat');
save(outMat,'RDP');
fprintf(1,'Saved: %s\n', outMat);
