function [G,P,F,id,Pa] = spm_forwards(O,P,A,B,C,H,K,W,I,t,T,N,m,id,pA,qa)
% deep tree search over policies or paths
%--------------------------------------------------------------------------
% FORMAT [G,Q,F] = spm_forwards(O,P,A,B,C,H,K,W,I,t,T,N,m,id,pA)
% O{m,g,t} - cell array of outcome probabilities for modality g
% P{m,f,t} - cell array of priors over states
% A{m,g}   - likelihood mappings from hidden states
% B{m,f,k} - belief propagators (policy-dependent probability transitions)
% C{m,g}   - priors over outcomes (cost or constraint)
% H{m,f}   - priors over final states
% K{m,g}   - likelihood ambiguity
% W{m,g}   - likelihood novelty
% I{m,f,k} - transition prior novelty
%
% t        - current time point
% T        - time horizon
% N        - policy horizon
% m        - model or agent to update
% id       - domains
% pA{m}    - prior (likelihood) models
% qa{m,g}  - posterior Dirichlet counts
%
% G(k,1)   - expected free energy over k policies
% Q{m,f,t} - posterior over states
% F        - variational free energy (negative or ELBO)
% id       - domains
% Pa{g}    - posterior over model priors pA{g}
%
% This subroutine performs a [deep] tree search over sequences of actions
% to evaluate the expected free energy over policies or paths. Crucially,
% it only searches likely policies under likely hidden states in the
% future. This search is sophisticated; in the sense that posterior beliefs
% are updated on the basis of future outcomes to evaluate the free energy
% under each outcome. The resulting  average is then accumulated to furnish
% a path integral of expected free energy for the next action. This routine
% operates recursively by updating predictive posteriors over hidden states
% and their most likely outcomes.
%
% In addition to overt policies this routine also considers covert policies
% specified in terms of selecting among subsets of outcomes for belief
% updating and planning. This can be regarded as attentional selection
% implemented using Bayesian model selection, where each model corresponds
% to a subset of selected outcome modalities (which could be the initial
% states and paths of a subordinate process). The marginal likelihood of
% each subset (specified in id.g{i}) is evaluated in terms of its expected
% free energy; associating each model with every combination of overt and
% covert policies. A covert policy id.gi is then selected on the basis of
% its marginal likelihood over overt policies.
%
%__________________________________________________________________________


% Posterior over hidden states based on likelihood (A) and priors (P)
%==========================================================================
Ni       = numel(id{m}.g);                  % number of covert policies
Nk       = size(B,3);                       % number of overt policies
Nf       = size(B,2);                       % number of factors
G        = zeros(Nk,Ni);                    % log priors over policies
Pa       = {};                              % priors over models

% variational (Bayesian) belief updating and free energy (ELBO)
%--------------------------------------------------------------------------
[Q,F]    = spm_VBX(O(m,:,t),P(m,:,t),A(m,:),id{m});
P(m,:,t) = Q;

% terminate search at time horizon, or if only one plausible policy
%--------------------------------------------------------------------------
if t > T || numel(G) == 1, return, end

% Constraints on next state (inductive inference)
%==========================================================================
[R,r] = spm_induction(B(m,:,:),H(m,:),P(m,:,t),(T - t),id{m});

if isvector(R)
    R = R(:)';
end

% Expected free energy (EFE) of subsequent action
%==========================================================================

% predictive posterior
%--------------------------------------------------------------------------
Q     = cell(1,Nf);
for f = id{m}.fp
    Q{f} = B{m,f,1}*P{m,f,t};
end

% search over policies
%--------------------------------------------------------------------------
for k = 1:Nk

    % predictive posterior
    %----------------------------------------------------------------------
    for f = id{m}.fu
        Q{f} = B{m,f,k}*P{m,f,t};
    end

    % G(k): risk over latent states
    %----------------------------------------------------------------------
    for f = id{m}.iH
        G(k,:) = G(k,:) - Q{f}'*(spm_log(Q{f}) - spm_log(H{m,f}));
    end

    % expected information gain (transition novelty) (B)
    %----------------------------------------------------------------------
    for f = id{m}.iI
        G(k,:) = G(k,:) + P{m,f,t}'*I{m,f,k}*Q{f};
    end

    % inductive constraints over states
    %----------------------------------------------------------------------
    if numel(R)
        G(k,:) = G(k,:) + spm_dot(R,Q(r));
    end

    % and outcomes
    %----------------------------------------------------------------------
    No    = zeros(1,Ni);                     % log number of outcomes
    for i = 1:Ni                             % covert policies
        gi     = id{m}.g{i};                 % for this partition
        if isfield(id{m},'ge')               % planning modlities
            gi = gi(ismember(gi,id{m}.ge));
        end
        for ig = gi

            % (state-dependent) domain of A{g}
            %--------------------------------------------------------------
            [j,gg] = spm_parents(id{m},ig,Q);

            for g = gg

                % predictive posterior and prior over outcomes
                %----------------------------------------------------------
                if isa(A{m,g},'function_handle')
                    qo = A{m,g}(Q(j));
                else
                    qo = spm_dot(A{m,g},Q(j));
                end

                % number of outcomes
                %----------------------------------------------------------
                No(i) = No(i) + spm_log(numel(qo));

                % G(k): risk over outcomes (entropy - expected cost)
                %----------------------------------------------------------
                G(k,i) = G(k,i) - qo'*spm_log(qo);

                % expected cost
                %----------------------------------------------------------
                if numel(C{m,g})

                    % state-dependent constraint
                    %------------------------------------------------------
                    if numel(id{m}.C{g})
                        f  = id{m}.C{g};
                        U  = spm_dot(spm_log(C{m,g}),Q(f));
                    else
                        U = spm_log(C{m,g});
                    end

                    G(k,i) = G(k,i) + qo'*U;
                end


                % G(k): ambiguity
                %----------------------------------------------------------
                if numel(K{m,g})
                    G(k,i) = G(k,i) + spm_dot(K{m,g},Q(j));
                end

                % expected information gain (likelihood novelty) (A)
                %----------------------------------------------------------
                if numel(W{m,g})
                    G(k,i) = G(k,i) + qo'*spm_dot(W{m,g},Q(j));
                end

                % expected information gain (likelihood priors) (pA)
                %----------------------------------------------------------
                if numel(pA{m}{g})

                    % update likelihood Dirichlet parameters
                    %------------------------------------------------------
                    da      = spm_cross(qo,Q(j));

                    % Bayesian model reduction
                    %------------------------------------------------------
                    Pa{g}  = spm_MDP_BMR(qa{m,g},     pA{m}{g});
                    Pg     = spm_MDP_BMR(qa{m,g} + da,pA{m}{g});
                    G(k,i) = G(k,i) + Pg'*(spm_log(Pg) - spm_log(Pa{g}));

                else
                    Pa{g}  = {};
                end

            end
        end
    end
end

% Covert policy (attentional selection of likelihood modalities)
%--------------------------------------------------------------------------
G     = plus(G,No);
if isfield(id{m},'i')

    % max expected free energy over outcome partition
    %----------------------------------------------------------------------
    [~,i] = max(max(G,[],1));
    G     = G(:,i);

    % update next covert policy
    %----------------------------------------------------------------------
    id{m}.i = i;

else

    % sum expected free energy over outcome partition
    %----------------------------------------------------------------------
    G     = sum(G,2);
    i     = 1;
end


% deep (recursive) search over action sequences ( i.e., paths)
%==========================================================================
if t < N

    % disable prior over models for future time steps
    %--------------------------------------------------------------------------
    pA{m} = cell(size(pA{m}));

    % probability over action (terminating search at a suitable threshold)
    %----------------------------------------------------------------------
    ig    = id{m}.g{i};                          % modalities
    u     = spm_softmax(G);                      % predictive prior
    k     = u > max(u)/16;                       % plausible states
    u(~k) = 0;
    G(~k) = max(G) - 512;

    % accumulate the path integral of expected free energy
    %----------------------------------------------------------------------
    for k = 1:Nk                                 % search over policies
        if u(k)                                  % and plausible states

            % predictive posterior
            %--------------------------------------------------------------
            for f = id{m}.fu
                Q{f} = B{m,f,k}*P{m,f,t};
            end

            % get hidden factors for sampled modalities
            %--------------------------------------------------------------
            j     = [];
            for g = ig
                j = unique([j,spm_parents(id{m},g,Q)]);
            end

            %  find plausible combinations of hidden states
            %--------------------------------------------------------------
            s     = cell(size(j));
            S     = cell(size(j));
            n     = cell(size(j));
            for f = 1:numel(j)
                s{f} = find(Q{j(f)} > exp(-8));
                S{f} = Q{j(f)}(s{f});
                n{f} = numel(s{f});
            end

            % restrict tree search to (4) most likely combinations
            %--------------------------------------------------------------
            q     = spm_cross(S);
            q     = reshape(q,n{:},1);
            [~,i] = sort(q(:),'descend');
            i     = i(4 + 1:end);
            q(i)  = 0;
            q     = q/sum(q,'all');

            % Evaluate expected free energy for these hidden states
            %--------------------------------------------------------------
            EFE   = zeros(size(q));
            for i = 1:numel(q)

                if q(i)

                    % indices of i-th combination of hidden states
                    %------------------------------------------------------
                    ind  = [spm_index(size(q),i), ones(1,numel(j))];
                    fi    = zeros(1,Nf);
                    for f = 1:numel(j)
                        fi(j(f)) = s{f}(ind(f));
                    end

                    % outcomes under this hidden state
                    %------------------------------------------------------
                    for g = ig
                        [f,gg] = spm_parents(id{m},g,Q);
                        ind    = num2cell(fi(f));
                        for o = gg
                            if isa(A{m,g},'function_handle')
                                O{m,o,t + 1} = A{m,g}([ind{:}]); %%%%
                            else
                                O{m,o,t + 1} = A{m,g}(:,ind{:});
                            end
                        end
                    end

                    % prior over subsequent states under this action
                    %------------------------------------------------------
                    P(m,:,t + 1) = Q;
                    E = spm_forwards(O,P,A,B,C,H,K,W,I,t + 1,T,N,m,id,pA);

                    % expected free energy marginalised over action
                    %------------------------------------------------------
                    EFE(i) = spm_softmax(E)'*E;

                end

            end % end search over plausible states

            % accumulate expected free energy marginalised over states
            %--------------------------------------------------------------
            G(k) = G(k) + sum(EFE.*q,'all');

        end % search over plausible states

    end % search over actions

end % search over the future


return

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

function g  = spm_children(id)
% Returns subset of likelihood mappings
% id.g  -  partition of modalities (cell array)
% id.i  -  index selected subset (i.e., attended modalities)
%--------------------------------------------------------------------------
if isfield(id,'g')
    if isfield(id,'i')
        g = id.g{id.i};
    else
        g = unique(spm_vec(id.g));
    end
else
    g = 1:numel(id.A);
end

% ensure g is a row vector
%--------------------------------------------------------------------------
g = g(:)';
