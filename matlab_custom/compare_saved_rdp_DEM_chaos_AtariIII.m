% compare_saved_rdp_DEM_chaos_AtariIII.m
% Loads RDP saved by dump_rdp_DEM_chaos_compression.m and dump_rdp_DEM_AtariIII.m
% and prints a side-by-side structural summary (no SPM edits).

d = fileparts(mfilename('fullpath'));
f1 = fullfile(d,'saved_rdp_DEM_chaos_compression.mat');
f2 = fullfile(d,'saved_rdp_DEM_AtariIII.mat');
if ~isfile(f1)
    error('Missing %s (run dump_rdp_DEM_chaos_compression first)', f1);
end
if ~isfile(f2)
    error('Missing %s (run dump_rdp_DEM_AtariIII first)', f2);
end

S1 = load(f1,'RDP');
S2 = load(f2,'RDP');
R1 = S1.RDP;
R2 = S2.RDP;

fprintf('Loaded chaos: %s\n', f1);
fprintf('Loaded atari: %s\n', f2);

L = 0;
M1 = R1;
M2 = R2;
while true
    L = L + 1;
    fprintf('\n===== Level %i =====\n', L);

    fprintf('[chaos] isfield C=%i c=%i a=%i b=%i A=%i B=%i id=%i L=%i T=%i\n', ...
        isfield(M1,'C'), isfield(M1,'c'), isfield(M1,'a'), isfield(M1,'b'), ...
        isfield(M1,'A'), isfield(M1,'B'), isfield(M1,'id'), isfield(M1,'L'), isfield(M1,'T'));
    if isfield(M1,'T'), fprintf('  T=%g\n', M1.T); end
    if isfield(M1,'A')
        Ng1 = numel(M1.A);
        fprintf('  Ng=%i\n', Ng1);
        if isfield(M1,'C')
            for g = 1:Ng1
                fprintf('  MDP.C{%i} numel=%i class=%s\n', g, numel(M1.C{g}), class(M1.C{g}));
            end
        end
        if isfield(M1,'id')
            fprintf('  id fields: %s\n', strjoin(fieldnames(M1.id), ', '));
            fprintf('  isfield(id,C)=%i\n', isfield(M1.id,'C'));
            if isfield(M1.id,'C')
                for g = 1:numel(M1.id.C)
                    fprintf('  MDP.id.C{%i} numel=%i\n', g, numel(M1.id.C{g}));
                end
            end
        end
    end

    fprintf('[atari] isfield C=%i c=%i a=%i b=%i A=%i B=%i id=%i L=%i T=%i\n', ...
        isfield(M2,'C'), isfield(M2,'c'), isfield(M2,'a'), isfield(M2,'b'), ...
        isfield(M2,'A'), isfield(M2,'B'), isfield(M2,'id'), isfield(M2,'L'), isfield(M2,'T'));
    if isfield(M2,'T'), fprintf('  T=%g\n', M2.T); end
    if isfield(M2,'A')
        Ng2 = numel(M2.A);
        fprintf('  Ng=%i\n', Ng2);
        if isfield(M2,'C')
            for g = 1:Ng2
                fprintf('  MDP.C{%i} numel=%i class=%s\n', g, numel(M2.C{g}), class(M2.C{g}));
            end
        end
        if isfield(M2,'id')
            fprintf('  id fields: %s\n', strjoin(fieldnames(M2.id), ', '));
            fprintf('  isfield(id,C)=%i\n', isfield(M2.id,'C'));
            if isfield(M2.id,'C')
                for g = 1:numel(M2.id.C)
                    fprintf('  MDP.id.C{%i} numel=%i\n', g, numel(M2.id.C{g}));
                end
            end
        end
    end

    h1 = isfield(M1,'MDP') && ~isempty(M1.MDP);
    h2 = isfield(M2,'MDP') && ~isempty(M2.MDP);
    if h1 ~= h2
        fprintf('DIFF: nested MDP presence chaos=%i atari=%i\n', h1, h2);
    end
    if ~h1 && ~h2
        break;
    end
    if h1 && ~h2
        fprintf('DIFF: chaos has deeper nested MDP than atari at this step.\n');
        break;
    end
    if ~h1 && h2
        fprintf('DIFF: atari has deeper nested MDP than chaos at this step.\n');
        break;
    end
    M1 = M1.MDP(1);
    M2 = M2.MDP(1);
end

fprintf('\nCompare script finished.\n');
