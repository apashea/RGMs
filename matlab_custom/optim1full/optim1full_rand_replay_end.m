function optim1full_rand_replay_end()
%OPTIM1FULL_RAND_REPLAY_END  Clear Model B ledger replay globals.

global rgms_optim1full_rand_buf rgms_optim1full_rand_idx rgms_optim1full_rand_active

rgms_optim1full_rand_buf = [];
rgms_optim1full_rand_idx = 1;
rgms_optim1full_rand_active = false;
end
