% dump_rdp_DEM_AtariIII.m
% Verbatim copy of spm12/toolbox/DEM/DEM_AtariIII.m lines 51-212
% (through RDP.T = 64; ), then save RDP beside this file.
% Requires SPM on path the same way you run the stock demo.

% set up and preliminaries
%--------------------------------------------------------------------------
rng(2)

% Get game: i.e., generative process (as a partially observed MDP)
%==========================================================================
Nr = 12;                                     % number of rows
Nc = 9;                                      % number of columns
Sc = 3;                                      % scaling
Nd = 4;                                      % random initial conditions
C  = 32;                                     % log cost

% get game in MDP form
%--------------------------------------------------------------------------
[GDP,~,~,~,RGB] = spm_MDP_pong(Nr,Nc,Nd,true,0);

% size of streams
%--------------------------------------------------------------------------
S      = ones(4,3);
S(1,:) = [Nr,Nc,1];                          % sensory stream
S(2,:) = [1 1 1];                            % reward  stream                 
S(3,:) = [1 1 1];                            % cost    stream
S(4,:) = [1 1 1];                            % policy  stream

% reward and cost functions [of outcomes]
%--------------------------------------------------------------------------
spm_get_hits = @(o,id) find(o(id.reward,:)    > 1);
spm_get_miss = @(o,id) find(o(id.contraint,:) > 1);

% Generate (probabilistic) outcomes under random actions
%==========================================================================
spm_figure('GetWin','Gameplay'); clf

GDP.tau = 2;                                 % smoothness of random paths
GDP.T   = 10000;                             % training length
PDP     = spm_MDP_generate(GDP);             % generate play

% illustrate sequence of random play
%---------------------------------------------------------------------------
con   = PDP.id.control;
for t = 1:128
    subplot(2,1,1)
    imshow(spm_O2rgb(PDP.O(:,t),RGB))
    subplot(4,3,8)
    imshow(PDP.O{con,t}')
    drawnow
end

% initial structure learning: grouping operators (iA,iB,iC,...)
%==========================================================================
MDP = spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc);

% forget parameters to select rewarded episodes
%--------------------------------------------------------------------------
Nm    = numel(MDP);
Ne    = max(2^(Nm - 1),1);
for n = 1:Nm
    for g = 1:numel(MDP{n}.a)
        MDP{n}.a{g} = [];
    end
    for f = 1:numel(MDP{n}.b)
        MDP{n}.b{f} = [];
    end
end

% find rewarded and costly events
%--------------------------------------------------------------------------
r     = spm_get_hits(PDP.o,GDP.id);
c     = spm_get_miss(PDP.o,GDP.id);
for i = 1:numel(r)

    % for each sequence ending with an intended outcome
    %----------------------------------------------------------------------
    s  = c(find(c < r(i),1,'last'));
    t  = (s + Ne):(r(i) + Ne);
    if numel(t)
       
        % assimilate this sequence
        %------------------------------------------------------------------
        for s = 1:Ne
            MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP);
        end
    end
end

% Step through training data to enlarge basins of attraction to goal states
%==========================================================================
spm_figure('GetWin','Attractors'); clf

NT = 100;                                    % number of outcomes
NS = [];                                     % number of states  
NU = [];                                     % number of paths 
NA = [];                                     % number of absorbing states
for i = 1:256

    % Accumulate these states under random play
    %----------------------------------------------------------------------
    q     = rem(i,100 - 1);
    t     = (0:(NT + Ne)) + q*NT;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP.O(:,t + s),MDP);
    end

    % test for NESS
    %----------------------------------------------------------------------
    [MDP,d] = spm_RDP_basin(MDP,[2,3],[C,-C]);

    NS(end + 1) = size(MDP{Nm}.b{1},2);    
    NU(end + 1) = size(MDP{Nm}.b{1},3);
    NA(end + 1) = sum(~d);

    subplot(2,3,1), plot(NS), title('Deep states'),      axis square
    subplot(2,3,2), plot(NU), title('Deep paths'),       axis square
    subplot(2,3,3), plot(NA), title('Absorbing states'), axis square
    drawnow

    % break if all (deep) states are transient (i.e., no absorbing states)
    %----------------------------------------------------------------------
    if all(d), break, end

end

% Retain (and sort) states with a high NESS probability
%--------------------------------------------------------------------------
for q = 1:4
    MDP = spm_RDP_sort(MDP);
end

% Illustrate transitions in deep (generalised) state space 
%-=========================================================================
MDP   = spm_set_goals(MDP,[2,3],[C,-C]);
hid   = MDP{Nm}.id.hid;

subplot(2,2,3)
spm_dir_orbits(MDP{Nm}.b{1},hid,128);

% paths to hits
%--------------------------------------------------------------------------
subplot(2,2,4)
B     = sum(MDP{Nm}.b{1},3) > 0;
Ns    = size(B,1);
Nt    = 32;
h     = sparse(1,hid,1,1,Ns);
P     = zeros(Nt,Ns);
for t = 1:Nt
    P(t,:) = h;
    h      = (h + h*B) > 0;
end
imagesc(P), hold on 
plot(hid,zeros(size(hid)) + 1/2,'or','MarkerSize',8), hold off
title('Paths to hits','FontSize',14)
xlabel('latent states'), ylabel('time steps'), axis square

% Generate play from recursive generative model
%==========================================================================

% assemble RGM
%--------------------------------------------------------------------------
RDP   = spm_set_goals(MDP,[2,3],[C,-C]);   % set intended states (hid/cid)
RDP   = spm_set_costs(RDP,[2,3],[C,-C]);   % set contraints (C)
RDP   = spm_mdp2rdp(RDP);                  % get nested model
RDP.T = 64;

outMat = fullfile(fileparts(mfilename('fullpath')),'saved_rdp_DEM_AtariIII.mat');
save(outMat,'RDP');
fprintf(1,'Saved: %s\n', outMat);
