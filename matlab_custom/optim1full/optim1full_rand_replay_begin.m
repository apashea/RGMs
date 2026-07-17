function optim1full_rand_replay_begin(buf, start_index)
%OPTIM1FULL_RAND_REPLAY_BEGIN  Replay scalar ``rand()`` from frozen Model B ledger.
%
% ``buf`` — column vector from ``optim1full_dem_atari_rand_buf.mat``.
% ``start_index`` — 0-based index into ``buf`` (first draw is ``buf(start_index+1)``).

global rgms_optim1full_rand_buf rgms_optim1full_rand_idx rgms_optim1full_rand_active

if nargin < 2
    start_index = 0;
end
rgms_optim1full_rand_buf = buf(:);
rgms_optim1full_rand_idx = double(start_index) + 1;
rgms_optim1full_rand_active = true;
end
