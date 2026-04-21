% How many rand() equivalents does randperm(n,1) advance the stream?
rng(0, 'twister');
s0 = rng;
a = randperm(10, 1);
s1 = rng;
rng(s0);
b = rand();
rng(s1);
c = rand();
