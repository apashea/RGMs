# 1. Plan

We are translating and validating the non-visual structure-learning path of this MATLAB pipeline:

- `spm_MDP_pong` to build the Pong generative process and stream metadata.
- `spm_MDP_generate` to produce probabilistic outcomes under random actions.
- `spm_faster_structure_learning(PDP.O(:,1:1000), S, Sc)` as the main target.
- Internal dependencies in this path, especially `spm_rgm_group` and `spm_dir_MI`.

The immediate translation goal is Python-native parity for this chain, with MATLAB Engine used only as provisional diagnostic scaffolding where native byte parity is currently blocked by investigated numerical issues.


# 2. Purpose of code

`spm_MDP_pong` constructs a partially observed MDP describing the game world, including observation mappings, transition structure, and identifiers used by later stages. In this workflow it defines the shape and semantics of streams (sensory/reward/cost/policy) and provides consistent inputs to generation and downstream structure learning. Conceptually, this is the source model from which sample trajectories are generated; if this stage is wrong, every later parity check becomes hard to interpret.

`spm_MDP_generate` rolls that model forward stochastically and emits the outcome sequence (`PDP.O`) used by structure learning. Here we enforce replay-controlled comparability (MATLAB `twister` + buffered random draws) so generated windows can be compared before any SL internals are blamed. In other words, this stage isolates whether disagreement originates in generation versus later interpretation of generated outcomes.

`spm_faster_structure_learning` is the core learner under test. It groups outcome channels, builds hierarchical linked structures, and populates nested MDP fields including stream-link metadata (`ss.D`, `ss.E`, `ss.ID`, `ss.IE`). Inside this function, `spm_rgm_group` performs MI-driven grouping with spectral partitioning; later, link assembly computes link-level MI scores through `spm_dir_MI` and stores them into `ss.ID/ss.IE`. The current residual native bottlenecks are located in these two adjacent internal regions.

`spm_rgm_group` computes MI structure over selected stream slices and performs eigensystem-based grouping decisions. In this project, one known bottleneck is spectral ordering sensitivity (MATLAB vs SciPy eig behavior under near-ties), and another is MI assembly parity on runtime `o_sub` slices. These are distinct but coupled: MI values determine eig inputs, and eig ordering determines selected group partitions.

`spm_dir_MI` computes expected information gain for Dirichlet parameters, including the entropy-style core term `H(row) + H(col) - H(joint)`. In the link-storage lane this is where we currently see near-cancellation behavior (Python exact `0.0` vs MATLAB tiny nonzero `~1e-16`) on a matrix that otherwise matches MATLAB bytes. This bottleneck is numerically subtle and currently treated as a separate lane from spectral grouping.


# 3. Current setup and issues

Ordered execution path (current harness) from start to finish:

1. Build MATLAB reference inputs and run MATLAB reference `spm_faster_structure_learning` for oracle comparison.  
   - Status: **validated harness pattern** (reference side).
   - Note: This is oracle construction, not target runtime design.

2. Rebuild Python `PDP.O` with replay-controlled randomness and compare pre-SL windows.  
   - Status: **validated** (generation/slice parity gates pass in current setup).

3. Enter Python `spm_faster_structure_learning` and evaluate grouping internals (`spm_rgm_group`).  
   - Native issue A: spectral lane mismatch in grouping (Step-6-style checkpoint context), associated with eig ordering/tie sensitivity under MATLAB vs SciPy numerics.
   - Temporary bypass flag: `RGMS_FSL_RGM_MATLAB_EIG=1` (inject MATLAB eig for grouping calls).
   - Temporary bypass flag: `RGMS_FSL_RGM_MATLAB_MI_PUSH=1` (rebuild MI in MATLAB per runtime `o_sub`; can be used with or without EIG for lane isolation).

4. Continue through linking and write `ss.ID/ss.IE` via `spm_dir_MI(a_mat)`.  
   - Native issue B: on the failing linked matrix, Python computes exact `0.0` while MATLAB keeps `~8.88e-16`, despite linked `a` matching bytes.
   - Diagnostic evidence: `[SS-LINK-DIAG]` confirms this is not `_link_streams` matrix assembly.
   - Temporary bypass flag: `RGMS_FSL_LINK_DIR_MI_MATLAB=1` (MATLAB `spm_dir_MI` only at link storage).

5. Exhaustive nested canonical-byte compare.  
   - Checkpoint system (`RGMS_FSL_USE_CHECKPOINT`, optional refresh) reduces rerun cost by reusing prepared `O_fsl_sx`/`S_fsl_sx` + `o_sl` artifacts.
   - Purpose of checkpoint: speed and reproducibility during bottleneck isolation, not behavior change.

What is already validated in practice:

- Pre-SL replay-controlled generation/slice gates are validated.
- Lane-B vs Lane-C separation is validated (MI-only does not clear spectral bottleneck; adding eig bridge advances the failure boundary).
- Link-lane isolation is validated (with MI+EIG+LINK bridge, exhaustive checkpoint passes).

What remains unresolved natively:

- Spectral grouping parity without MATLAB eig bridge.
- Link `spm_dir_MI` near-cancellation parity without MATLAB link bridge.


# 4. Test Lanes and current evaluation

Lane configurations:

- **Lane A:** exhaustive test with `EIG=0, MI_PUSH=0, LINK=0` (native baseline lane).
- **Lane B:** exhaustive test with `EIG=0, MI_PUSH=1, LINK=0` (MATLAB MI, Python eig).
- **Lane C:** exhaustive test with `EIG=1, MI_PUSH=1, LINK=0` (MATLAB MI + MATLAB eig, native link `spm_dir_MI`).
- **Lane D:** exhaustive test with `EIG=1, MI_PUSH=1, LINK=1` (MATLAB MI + MATLAB eig + MATLAB link `spm_dir_MI`).
- **Lane E:** non-exhaustive subset in this file via `-k "not exhaustive_exact_oracle"` (fast regression lane; not a bottleneck-classification lane).

Current progress toward end goal is substantial but intentionally staged. The harness can now move bottlenecks forward in a controlled way, and lane definitions are stable enough to avoid the prior ambiguity around what is native vs temporarily bridged. In practical terms, we are no longer searching blindly; we can deliberately select a lane and know what class of issue it is expected to expose.

At a broad level, the first unresolved class is spectral grouping parity (native eig path) and the second unresolved class is link-time `spm_dir_MI` near-cancellation. These are adjacent in the pipeline but analytically separable, and the lane outcomes already prove that separation: Lane B remains blocked in grouping, Lane C advances to link MI, and Lane D clears the tree under full provisional bridging.

Going forward, the main work is to convert this lane-based diagnostic certainty into Python-native closure decisions: either achieve stricter numeric equivalence in those two lanes or settle explicit numeric policy where 1:1 float64 parity is not realistically recoverable. The key guardrail is unchanged: temporary Engine hooks remain investigative scaffolding and must not be mistaken for final architecture.
