load('C:/Users/andre/.cursor/RGMs/tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_entry12_rgms_atari_call2_12F.mat', 'out_t1');
ch = out_t1.MDP.MDP;
disp(['numel_idg=' num2str(numel(ch.id.g))]);
disp(['child_F=' mat2str(ch.F(:)')]);
disp(['parent_F=' mat2str(out_t1.MDP.F(:)')]);
