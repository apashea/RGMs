% Entry12 dump-fork spm_induction (from matlab_src/spm_MDP_VB_XXX.m local fn).
% Standalone for frozen oracle; keep aligned with spm_MDP_VB_XXX_entry12_dump.m

function [R,hif] = spm_induction(B,H,Q,N,id)
% Inductive inference about next state
% FORMAT [R,hif] = spm_induction(B,H,Q,N,id)
%--------------------------------------------------------------------------
% B{1,f,k} - belief propagators (policy-dependent probability transitions)
% H{1,f}   - cell array of priors over final state
% Q{1,f}   - cell array of posteriors over states
% N        - planning horizon
%
% id     - domain structure
%
%   id.hid(Nf,Ni)  - indices of Ni intended  states
%   id.cid(Nf,Ni)  - indices of Ni suprising states
%
% R      - tensor encoding unconstrained states over hif factors
% hif    - factors of tensor
%
% This subroutine returns constraints on the next state based upon
% backwards induction of a simple sort; i.e., using backwards propagators
% to identify paths of least action using logical operators.
%
% In addition, constraints can be specified in a small number of latent
% factors by supplying a matrix of constraints, where each column
% corresponds to a distinct constraint and the number of rows corresponds
% to the number of hidden factors. This constraint matrix contains the
% index of the costly state for each factor. If an index is zero, the
% constraint is taken to be independent of the corresponding factor;
% otherwise, this conditional factor has to have a high posterior over the
% next state, before the constraint is implemented.
%__________________________________________________________________________

% Preliminary checks (for no priors over end states)
%==========================================================================

% Convert marginals to indices and find factors
%--------------------------------------------------------------------------
if isfield(id,'hid')

    if isa(id.hid,'function_handle')

        % intended states (hid) in factors hif
        %------------------------------------------------------------------
        [hid,hif] = id.hid(Q);

    else
        hid   = id.hid;                           % intended states
        hif   = find(any(hid,2))';                % in hif factors
    end

else

    % intended state from marginals (H)
    %----------------------------------------------------------------------
    hid   = [];
    hif   = [];
    for f = 1:numel(H)
        if numel(H{f})
            [~,s]  = max(H{f});
            hid(end + 1,1) = s;
            hif(1,end + 1) = f;
        end
    end
end

% Deal with constraints
%--------------------------------------------------------------------------
if isfield(id,'cid')

    if isa(id.cid,'function_handle')

        % disallowed states (D) in factors hif
        %------------------------------------------------------------------
        [D,hif] = id.cid(Q);

    elseif isempty(id.cid)

        % no contraints
        %------------------------------------------------------------------
        D = true;

    else

        % assume cid is consistent with hid
        %------------------------------------------------------------------
        cid   = id.cid;                           % contrained factors
        nid   = cid;                              % conditioning factors
        hif   = find(all(cid,2))';                % in hif factors
        nid(hif,:) = 0;

        % size of contrained factors
        %------------------------------------------------------------------
        Ns    = ones(1,numel(hif) + 1);
        for f = hif
            Ns(f) = size(B{f},1);
        end

        % constraint tensor over hid factors
        %------------------------------------------------------------------
        D     = true(Ns);                        % unconstrained states
        for i = 1:size(cid,2)

            % posterior of constraint violation
            %--------------------------------------------------------------
            q     = 1;
            for f = find(nid(:,i))'
                q = q*Q{f}(cid(f,i));
            end
            if q > (1 - 1/8)
                ind  = num2cell(cid(hif,i));
                j    = spm_sub2ind(Ns,ind{:});
                D(j) = false;
            end
        end

    end
else
    D = true;
end

% Return if there are no intended states or constraints
%--------------------------------------------------------------------------
if isempty(hif), R = [];   return, end
if isempty(hid), R = 32*D;  return, end

% check for RGM
%--------------------------------------------------------------------------
N     = min(N,64);
if isfield(id,'D') && N < 4
    N = 64;
end

% Threshold transition probabilities
%--------------------------------------------------------------------------
u     = 1/32;                            % probability threshold
for f = hif
    b{f}  = false;
    for k = 1:size(B,3)
        try
            b{f} = b{f} | (B{1,f,k} > u);
        catch
            b{f} = b{f} | (B{1,f,1} > u);
        end
    end
end

% Kronecker tensor products (sparse)
%--------------------------------------------------------------------------
Bf    = 1;
Qf    = 1;
Ns    = [];
for f = hif
    Ns(end + 1) = size(B{f},1);          % number of states for hif
    Bf = spm_kron(b{f},Bf);           % unconstrained transitions
    Qf = spm_kron(Q{f},Qf);           % posterior over states
end
Bf        = and(Bf,D(:));                % constrained transitions
if size(Bf,2) > 512
    N = min(N,32);
end

% Backwards induction: from end states
%==========================================================================

% hid are indices (of multiple endpoints)
%--------------------------------------------------------------------------
Nh    = size(hid,2);
for i = 1:Nh
    I     = true;
    for f = 1:numel(hif)
        h           = false(Ns(f),1);
        h(hid(f,i)) = true;
        I           = spm_kron(h,I);
    end
    Pf(:,i) = logical(I);
end


% Backwards induction: paths of least action
%==========================================================================
G     = zeros(N,Nh);
for i = 1:Nh

    % for this end state
    %----------------------------------------------------------------------
    I = logical(Pf(:,i));

    % backwards protocol (for paths with a well-defined end state)
    %----------------------------------------------------------------------
    for n = 1:N

        % any preceding states %%% & that have not been previously occupied
        %------------------------------------------------------------------
        j          = any(Bf(I(:,n),:),1)';        %%% & ~any(I,2);
        I(:,n + 1) = j;

        if ~any(j), break, end
    end

    % Find most likely point on paths of least action
    %----------------------------------------------------------------------
    j      = 1:size(I,2);
    G(j,i) = I'*Qf;
    P{i}   = I;

end

% graphics for visualisation
%--------------------------------------------------------------------------
if false
    spm_figure('GetWin','Inductive inference');
    for i = 1:min(size(hid,2),8)
        subplot(4,4,i)
        imagesc(P{i})
        title(sprintf('Goal %i',i))
        xlabel('time'), ylabel('state')
    end
    subplot(2,1,2)
    imagesc(G), axis square, drawnow
    title('Paths'), xlabel('goal'), ylabel('time')
end

% precise log prior over next state
%==========================================================================
G(1,:) = 0;                        % preclude current states
[d,n]  = max(G,[],1);              % next intended state
i     = d > u;                     % provided it exists
if any(i)

    % eliminate inaccessible end states
    %----------------------------------------------------------------------
    P     = P(i);
    n     = n(i);
    [n,i] = min(n);                % to the i-th end state

    % precise log prior over next state
    %----------------------------------------------------------------------
    P     = P{i}(:,max(n - 1,1));
    R     = reshape(full(P),[Ns,1]);
    R     = 32*and(R,D);

else
    R     = [];
end

return


