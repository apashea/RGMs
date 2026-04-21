% Compare randperm(k,1) vs floor(k*rand)+1 after rng(0)
rng(0,'twister');
for k = [1 2 3 5 10 100]
    rng(0,'twister');
    rp = randperm(k,1);
    rng(0,'twister');
    r = rand();
    j = floor(k*r)+1;
    fprintf('k=%d rp=%d floor+1=%d match=%d\n', k, rp, j, rp==j);
end
