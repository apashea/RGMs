function [R,hif] = spm_induction(B,Q,N,id)
% Inductive inference about next state
% FORMAT [R,hif] = spm_induction(B,Q,N,id)
%--------------------------------------------------------------------------
% A{1,g}   - likelihood mappings from hidden states
% B{1,f,k} - belief propagators (policy-dependent probability transitions)
% Q{1,f}   - cell array of posteriors over states
%
% N      - induction depth
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
    hid   = id.hid;                           % intended states
    hif   = find(any(hid,2))';                % in hif factors
else
    hid   = [];
    hif   = [];
end

% Deal with constraints
%--------------------------------------------------------------------------
if isfield(id,'cid')
    cid   = id.cid;                           % contrained factors
    nid   = cid;                              % conditioning factors
    hif   = find(all(cid,2))';                % in hif factors
    nid(hif,:) = 0;

    % size of contrained factors
    %----------------------------------------------------------------------
    for f = hif
        Ns(f) = size(B{f},1);
    end
    Ns    = [Ns,1];

    % constraint tensor over hid factors
    %----------------------------------------------------------------------
    D     = true(Ns);                        % unconstrained states
    for i = 1:size(cid,2)

        % posterior of constraint violation
        %------------------------------------------------------------------
        q     = 1;
        for f = find(nid(:,i))'
            q = q*Q{f}(cid(f,i));
        end
        if q > (1 - 1/8)
            ind  = num2cell(cid(hif,i));
            j    = sub2ind(Ns,ind{:});
            D(j) = false;
        end
    end
else
    D = true;
end

% Return if there are no intended states or constraints
%--------------------------------------------------------------------------
if isempty(hif), R = false; return, end
if isempty(hid), R = 32*D;  return, end

% Threshold transition probabilities
%--------------------------------------------------------------------------
u     = 1/16;                            % probability threshold
b     = cell(1,numel(hif));
for f = hif
    b{f}  = false;
    for k = 1:size(B,3)
        b{f} = b{f} | gt(B{1,f,k}, max(B{1,f,k})*u);
    end
end

% Kronecker tensor products (sparse)
%--------------------------------------------------------------------------
Bf    = 1;
Qf    = 1;
for f = hif
    Ns(f) = size(B{f},1);                % numer of states for hif
    Bf    = spm_kron(b{f},Bf);           % unconstrained transitions
    Qf    = spm_kron(Q{f},Qf);           % posterior over states
end

% Expected cost in latent state space
%==========================================================================
Bf    = and(Bf,D(:));                    % constrained transitions


% Backwards induction: from end states
%==========================================================================

% hid are indices (of multiple endpoints)
%--------------------------------------------------------------------------
for i = 1:size(hid,2)
    for f = hif
        h{f} = false(Ns(f),1);
        h{f}(hid(f,i)) = true;
    end
    I     = true;
    for f = hif
        I = spm_kron(h{f},I);
    end
    Pf(:,i) = logical(I);
end


% Backwards induction: paths of least action
%==========================================================================
for i = 1:size(Pf,2)

    % for this end state
    %----------------------------------------------------------------------
    I = logical(Pf(:,i));

    % backwards protocol (for paths with a well-defined end state)
    %----------------------------------------------------------------------
    for n = 1:min(N,16)

        % any preceding states % & that have not been previously occupied
        %------------------------------------------------------------------
        I(:,n + 1) = any(Bf(I(:,n),:),1)'; % & ~any(I,2);
    end

    % Find most likely point on paths of least action
    %----------------------------------------------------------------------
    G(:,i) = I'*Qf;
    P{i}   = I;

end

% precise log prior over next state
%==========================================================================
G(1,:) = 0;                        % preclude current states
[d,n]  = max(G,[],1);              % next intended state
i      = d > u;                    % provided it exists
if any(i)

    % eliminate inaccessible end states
    %----------------------------------------------------------------------
    P     = P(i);
    n     = n(i);
    [n,i] = min(n);                % to the i-th end state

    % precise log prior over next state
    %----------------------------------------------------------------------
    P     = P{i}(:,max(n - 1,1));
    R     = single(reshape(full(P),[Ns 1]));
    R     = shiftdim(32*R,-1);
else
    R = false;
end

return
