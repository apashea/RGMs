function [mdp,j] = oracle_spm_structure_fast(O)
% Verbatim copy of local spm_structure_fast from spm_faster_structure_learning.m
% for MATLAB Engine oracles only (subfunctions are not Engine-callable).

% discretise and return indices of unique outcomes
%--------------------------------------------------------------------------
[i,j] = spm_unique(O);

% reduction matrix
%--------------------------------------------------------------------------
R     = sparse(1:numel(j),j,1,numel(j),numel(i));

% Likelihood tensors
%--------------------------------------------------------------------------
Ng    = size(O,1);                          % number in group
a     = cell(Ng,1);
for g = 1:Ng
    a{g} = spm_cat(O(g,:))*R;
end

% Transition tensors
%--------------------------------------------------------------------------
Ns    = numel(i);                           % number of latent causes
Nt    = numel(j) - 1;
b     = zeros(Ns,Ns);
for t = 1:Nt

    % Is this an existing transition?
    %----------------------------------------------------------------------
    u  = find(b(j(t + 1),j(t),:),1,'first');
    if numel(u)

        % accumulate Dirichlet counts for this transition
        %------------------------------------------------------------------
        b(j(t + 1),j(t),u) = b(j(t + 1),j(t),u) + 1;

    else

        % find the first path that does not have a successor of j(t)
        %------------------------------------------------------------------
        u  = find(~any(b(:,j(t),:),1),1,'first');
        if numel(u)

            % equip this path with a successor
            %--------------------------------------------------------------
            b(j(t + 1),j(t),u) = 1;

        else

            % otherwise create a new path
            %--------------------------------------------------------------
            b(j(t + 1),j(t),end + 1) = 1;
        end
    end
end

% Vectorise cell array of likelihood tensors and place in structure
%--------------------------------------------------------------------------
mdp.a    = a;
mdp.b{1} = b;

% add probabilities over initial states and paths
%==========================================================================
Nu    = size(b,3);
X     = false(Ns,1);
mdp.X = cell(1,Nt);
mdp.P = cell(1,Nt);

% states
%--------------------------------------------------------------------------
for t = 1:(Nt + 1)
    s        = X;
    s(j(t))  = true;
    mdp.X{t} = s;
end

% paths
%--------------------------------------------------------------------------
for t = 1:Nt
    if Nu > 1
        mdp.P{t} = logical(squeeze(b(j(t + 1),j(t),:)));
    else
        mdp.P{t} = true;
    end
end
mdp.X = mdp.X(1:Nt);

return
