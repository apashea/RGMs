function [Q,P,qa,qb,F] = spm_backwards(O,P,Q,D,E,pa,pb,U,m,id)
% Backwards smoothing to evaluate posterior over initial states
%--------------------------------------------------------------------------
% O{m,g,t} - cell array of outcome probabilities for modality g
% P{m,k,t} - cell array of posteriors over paths
% Q{m,f,t} - cell array of posteriors over states
% D{m,f}   - cell array of priors over initial states
% E{m,k}   - belief propagators (action dependent probability transitions)
% pa{m,g}  - likelihood tensor  (Dirichlet parameters)
% pb{m,f}  - belief propagators (Dirichlet parameters)
% U{f}   - controllable factors
% m      - agent or model
%
% F      - Negative free energy (states, paths and parameters) ELBO
%
%  This subroutine performs Bayesian smoothing in the sense of a replay
%  using variational iterations to optimise posteriors over states, paths
%  and parameters, given the outcomes over an epoch. It effectively
%  implements the prior constraint that certain random variables (i.e., the
%  paths of uncontrollable factors and parameters) do not change with time
%__________________________________________________________________________

%  (iterative) variational scheme
%==========================================================================
tr    = @(A) pagetranspose(A);
T     = size(Q,3);
Nf    = size(Q,2);

% variational iterations
%--------------------------------------------------------------------------
Z     = -Inf;
for v = 1:16

    % initialise free energy (ELBO) & posterior Dirichlet parameters
    %----------------------------------------------------------------------
    F    = zeros(1,T);
    qa   = pa;
    qb   = pb;

    % acccumulate posterior Dirichlet parameters
    %======================================================================
    for t = 1:T

        % likelihood mapping from hidden states to outcomes: a
        %------------------------------------------------------------------
        for g = spm_children(id{m})
            [j,i] = spm_parents(id{m},g,Q(m,:,t));
            for o = i
                qa{m,g} = qa{m,g} + spm_cross(O{m,o,t},Q{m,j,t});
            end
            qa{m,g} = qa{m,g}.*(pa{m,g} > 0);
        end

        % mapping from hidden states to hidden states: b(u)
        %------------------------------------------------------------------
        if t < T
            for f = 1:numel(qb)
                qb{m,f} = qb{m,f} + spm_cross(spm_cross(Q{m,f,t + 1},Q{m,f,t}),P{m,f,t});
                qb{m,f} = qb{m,f}.*(pb{m,f} > 0);
            end
        end

    end

    % inference (Bayesian filtering)
    %======================================================================
    for t = 1:T

        if isfield(id{m},'independent')

            %  conditionally independent factors
            %--------------------------------------------------------------
            L      = cell(1,Nf);
            [L{:}] = deal(0);

            % attended modalities
            %--------------------------------------------------------------
            for g = spm_children(id{m})
                [j,k] = spm_parents(id{m},g,Q(m,:,t));
                j     = unique(j,'stable');
                LL    = 0;
                for o = k
                    LL = LL + spm_log(spm_dot(spm_norm(qa{m,g}),O{m,o,t}));
                    %  = LL + spm_dot(spm_psi(qa{m,g}),O{m,o,t});
                end
                L{j} = L{j} + LL;
            end

            % posterior over hidden states
            %--------------------------------------------------------------
            for i = 1:Nf

                % log prior: smoothing
                %----------------------------------------------------------
                LP   = 0;
                if t == 1
                    LP = LP + spm_log(D{m,f});
                end
                if t < T
                    LP = LP + spm_dot(spm_psi(tr(qb{f})),P(m,f,t))*Q{m,f,t + 1};
                end
                if t > 1
                    LP = LP + spm_dot(spm_psi(qb{f}),P(m,f,t - 1))*Q{m,f,t - 1};
                end

                % posterior
                %----------------------------------------------------------
                Q{m,f,t} = spm_softmax(L{f} + LP);

                % ELBO free energy of states (accuracy and complexity)
                %----------------------------------------------------------
                F(t)     = F(t) + Q{m,f,t}'*(L{f} + LP - spm_log(Q{m,f,t}));

            end

        else

            %  conditionally dependent factors
            %--------------------------------------------------------------
            L     = 0;
            for g = spm_children(id{m})
                [j,k] = spm_parents(id{m},g,Q(m,:,t));
                j  = unique(j,'stable');
                LL    = 0;
                for o = k
                    LL = LL + spm_log(spm_dot(spm_norm(qa{m,g}),O{m,o,t}));
                    %  = LL + spm_dot(spm_psi(qa{m,g}),O{m,o,t});
                end
                if numel(j) > 1
                    [j,i] = sort(j);
                    LL    = permute(LL,i);
                end
                k  = ones(1,Nf + 1); k(j) = size(LL,1:numel(j));
                L  = plus(L, reshape(LL,k));
            end

            % factors to update
            %--------------------------------------------------------------
            i = size(L);
            r = find(i > 1);
            L = reshape(L,[i(r) 1 1]);

            % only one latent state
            %--------------------------------------------------------------
            if isempty(r), F(t) = L; end

            % posterior over hidden states
            %--------------------------------------------------------------
            for i = 1:numel(r)

                % log likelihood
                %----------------------------------------------------------
                f    = r(i);
                LL   = spm_vec(spm_dot(L,Q(m,r,t),i));

                % log prior: smoothing
                %----------------------------------------------------------
                LP   = 0;
                if t == 1
                    LP = LP + spm_log(D{m,f});
                end
                if t < T
                    LP = LP + spm_dot(spm_psi(tr(qb{f})),P(m,f,t))*Q{m,f,t + 1};
                end
                if t > 1
                    LP = LP + spm_dot(spm_psi(qb{f}),P(m,f,t - 1))*Q{m,f,t - 1};
                end

                % posterior
                %----------------------------------------------------------
                Q{m,f,t} = spm_softmax(LL + LP);

                % ELBO free energy of states (accuracy and complexity)
                %----------------------------------------------------------
                F(t)  = F(t) + Q{m,f,t}'*(LL + LP - spm_log(Q{m,f,t}));

            end
        end

    end

    % beliefs about paths
    %======================================================================
    for f = 1:numel(qb)

        % beliefs about (changing) paths
        %------------------------------------------------------------------
        if U{m}(f)

            for t = 2:T

                % log likelihood of control states
                %----------------------------------------------------------
                LL = spm_dot(spm_dot(spm_psi(qb{f}),Q{m,f,t}),Q{m,f,t - 1});

                % prior over control state
                %----------------------------------------------------------
                LP = spm_log(P{m,f,t - 1});

                % posterior over control states
                %----------------------------------------------------------
                P{m,f,t - 1} = spm_softmax(LL + LP);

                % ELBO free energy of paths (complexity)
                %----------------------------------------------------------
                F(t)  = F(t) + P{m,f,t - 1}'*(LL + LP - spm_log(P{m,f,t - 1}));

            end

        else  % beliefs about (unchanging) paths

            % accumulate log likelihood
            %--------------------------------------------------------------
            LL    = 0;
            for t = 2:T
                LL = LL + spm_dot(spm_dot(spm_psi(qb{f}),Q{m,f,t}),Q{m,f,t - 1});
            end

            % prior over control state
            %--------------------------------------------------------------
            LP = spm_log(E{m,f});

            % posterior over control states
            %--------------------------------------------------------------
            PP    = spm_softmax(LL + LP);
            for t = 1:T
                P{m,f,t} = PP;
            end

            % ELBO free energy of paths (complexity)
            %--------------------------------------------------------------
            F(t)  = F(t) + PP'*(LL + LP - spm_log(PP));

        end
    end

    % convergence
    %======================================================================
    dF = sum(F) - Z;

    % checks on ELBO
    %----------------------------------------------------------------------
    if sum(F) > 0
        warning('positive ELBO in spm_backwards')
    end
    if dF < 1/128
        break
    else
        Z = sum(F);
    end

end

return

function g = spm_children(id)
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


function A  = spm_norm(A)
% normalisation of a probability transition matrix (columns)
%--------------------------------------------------------------------------
if isnumeric(A)
    A           = rdivide(A,sum(A,1));
    A(isnan(A)) = 1/size(A,1);
end
