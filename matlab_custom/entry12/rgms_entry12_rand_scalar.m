function r = rgms_entry12_rand_scalar()
%RGMS_ENTRY12_RAND_SCALAR Next scalar from global vb_rand_buf replay lane.
global rgms_entry12_buf rgms_entry12_i
if isempty(rgms_entry12_buf)
    error('rgms_entry12_buf not initialised');
end
if rgms_entry12_i > numel(rgms_entry12_buf)
    error('rgms_entry12_buf exhausted at index %d (numel=%d)', ...
        rgms_entry12_i, numel(rgms_entry12_buf));
end
r = rgms_entry12_buf(rgms_entry12_i);
rgms_entry12_i = rgms_entry12_i + 1;
end
