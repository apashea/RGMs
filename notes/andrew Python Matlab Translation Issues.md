# Python MATLAB Translation Issues — Andrew branch

This file records settled corner-case decisions for faithful MATLAB-to-Python
translation on branch `andrew`. It includes the same settled material as the
repo-root `Python Matlab Translation Issues.md` (copied here for convenience)
plus additional decisions recorded only in this branch notes file.

Future agents should read the repo-root `Python Matlab Translation Issues.md` and
this file before translating or changing tests. If a new MATLAB/Python corner
case appears, ask the user first; after a decision is settled, add it here (for
branch-specific policy) or in the repo-root file (for shared policy), as your
workflow defines.

## Raw 1-D NumPy Arrays

Decision: treat raw 1-D numeric NumPy arrays as MATLAB row vectors.

MATLAB numeric vectors have orientation. A literal like `[1 2 3]` is a row
vector, while `[1; 2; 3]` is a column vector. NumPy arrays with shape `(n,)`
have no orientation, so translated functions should interpret them as row
vectors with shape `(1, n)`. Column vectors must be passed explicitly with
shape `(n, 1)`.

This policy matters for shape-sensitive functions including `spm_log.py`,
`spm_softmax.py`, `spm_psi.py`, `spm_betaln.py`, `spm_cat.py`,
`spm_cross.py`, `spm_dot.py`, `spm_cov2corr.py`, and new translations such as
`spm_sum.py` and `spm_MDP_size.py`.

## `spm_log`: MATLAB transliteration vs `log` ULP (Bottleneck #1)

**MATLAB source (`matlab_src/spm_log.m`, matches SPM):** `islogical(A)` branch
uses `A = -32*(~A);`; numeric branch uses `A = max(log(A),-32);` (no extra
epsilon inside `log`).

**Python Pass 1 (`python_src/spm_log.py`):** After `as_matlab_array`, the same
control flow applies on non-logical arrays using `np.fmax(np.log(A), -32.0)`.
`np.fmax` is used (not `np.maximum`) because MATLAB `max(log(NaN), -32)` returns
`-32`, while NumPy `maximum` would preserve `NaN` from `log(NaN)` and would
incorrectly poison downstream expressions such as `spm_MDP_MI`’s `dEdA`
construction.

**IEEE / libm note:** `np.log` on `float64` is not guaranteed to be bitwise
identical to MATLAB’s `log` on every host, even when the real mathematical
results round to the same IEEE value—different C runtimes / vectorized kernels
can differ by a **small number of ULPs**. This matters for byte-exact MI
pipelines that multiply many `log` outputs and accumulate.

**Measured guardrail (2026-04-28, Windows, MATLAB Engine vs Python `spm_log`):**
On the **234** distinct `float64` values in the multiset built from the
captured Bottleneck #1 MI workload (`A = p/sum(p)`, `sum(A,1)`, `sum(A,2)` over
all `p` in `fsl_rgm_mi_workload_full_native_mi.pkl`), worst-case ULP distance
vs MATLAB `spm_log` was **3**; **19** of **234** entries were not bitwise-equal.
`tests/oracle/test_spm_log.py::test_spm_log_mi_workload_reference_max_ulp_oracle`
locks in that ceiling so libm regressions are caught.

**Diagnostic-only:** `RGMS_SPM_LOG_EXPERIMENT_KERNEL=log2_ln2` is **not**
MATLAB-faithful; use only for controlled Bottleneck #1 experiments, never as
the default translation.

## `spm_MDP_MI` workload replay: one MATLAB truth (Engine)

The fast replay test `tests/oracle/test_spm_MDP_MI.py::test_spm_MDP_MI_rgm_workload_fast_replay_oracle`
loads **inputs** (`p_mat`) from `fsl_rgm_mi_workload*.pkl` and compares Python
scalar `E` to **live** MATLAB Engine `spm_MDP_MI(p)` by default.

Checkpoint field `matlab_mi` is **capture-time metadata** and can drift from a
later Engine run (path/version/order); it is **not** a second co-equal MATLAB
oracle unless explicitly opted in:

- Default: live Engine gate only (`RGMS_MDP_MI_REPLAY_LEGACY_CAPTURED_MATLAB` unset).
- Legacy opt-in: set `RGMS_MDP_MI_REPLAY_LEGACY_CAPTURED_MATLAB=1` to assert against
  stored `matlab_mi` instead (harness regression against a frozen capture only).

Measured on `fsl_rgm_mi_workload_full_native_mi.pkl` (1711 pair records), current
faithful default gives `py_vs_live=907` while all mismatch magnitudes are
ULP-scale: max `6.6613381477509392e-16`, p50 `1.3877787807814457e-17`,
p90 `2.2204460492503131e-16`, p99 `4.4408920985006262e-16` (all `<=1e-15`).
Experimental regrouping (`RGMS_MDP_MI_EXPERIMENT_SUB_ASSOC=t1_minus_sum23`) can
lower mismatch count to `873`, but this is a non-faithful arithmetic-association
variant and is retained for diagnostics only.

Term-level replay diagnostics (first live mismatches) decompose
`E = t1 - t2 - t3` with:

- `t1 = A(:)' * spm_log(A(:))`
- `t2 = sum(A,1) * spm_log(sum(A,1)')`
- `t3 = sum(A,2)' * spm_log(sum(A,2))`

On sampled mismatches, `|dE|` is explained by `t1` and/or `t2` ULP drift, while
`t3` has been `0` in the sampled set. This supports the current hypothesis that
remaining byte-exact misses are log/dot-product rounding at the joint/column
marginal terms, not a broad algebraic shape/control-flow mismatch.

Additional diagnostics (`RGMS_MDP_MI_EXPERIMENT_LOG_SITES`) allow selective
`log2*ln(2)` use in `_spm_MI` terms (`t1`, `t2`, `t3`) while default remains
MATLAB-faithful. On live replay (`1711` pairs), no selective subset beat the
faithful baseline by much (`t2` alone gave `900` vs baseline `907`), and several
subsets regressed heavily (`t1`-involving subsets). Best count still required
switching **all** MI log sites together (`all_log2_ln2` gave `874`) and remains
diagnostic-only because it is not MATLAB-faithful.

Term-ULP profile oracle (`test_spm_MDP_MI_rgm_workload_term_ulp_profile_live_oracle`)
shows per-term MATLAB vs Python drift on this workload:

- `t1` max ULP: `2` (p99 `1`)
- `t2` max ULP: `2` (p99 `2`)
- `t3` max ULP: `2` (p99 `2`)
- recomposed `te=t1-t2-t3` max absolute drift: `6.6613381477509392e-16`

Despite tiny per-term ULP drift, `te` ULP distance itself can be very large due
subtractive cancellation and local spacing effects; use `abs(py_te-mat_te)` for
the recomposed scalar guardrail, and reserve ULP checks for the individual terms.

Additional reduction-order probes in `_spm_MI`:

- `RGMS_MDP_MI_EXPERIMENT_TERM_ORDER=dot_fwd` (explicit `np.dot`) reproduces the
  default replay profile exactly (`py_self=0`, `py_vs_live=907`), suggesting the
  default matrix-expression path and dot reduction are effectively equivalent here.
- `...=scalar_rev` improves live mismatch count (`py_vs_live=884`) but introduces
  substantial self drift (`py_self=314`), so it is diagnostic-only and not a
  faithful replacement.
- `...=dot_rev` regresses strongly (`py_vs_live=1050`), further indicating that
  reverse-order summation is not MATLAB-faithful on this workload.

Cancellation-band profiling on the same replay workload (`1711` pairs) shows no
extreme near-zero cancellation regime in this corpus (`|t1-(t2+t3)| <= 1e-6` had
zero rows). The observed bands and mismatch rates were:

- `(1e-6,1e-3]`: `695/1370` mismatches (`~0.507`)
- `>1e-3`: `212/341` mismatches (`~0.622`)

This indicates current mismatches are not concentrated in a tiny cancellation tail;
they remain spread across ordinary-scale MI magnitudes, consistent with broad
ULP-level log/dot rounding effects rather than a narrow pathological subset.

Stratified mismatch signatures (sampled rows from both `(1e-6,1e-3]` and `>1e-3`
bands) show the same pattern:

- `ulp(t1)` / `ulp(t2)` are tiny (`0..2` in sampled rows),
- `ulp(t3)` is often `0`,
- recomposed `E` can have larger ULP counts in lower-magnitude `E` rows even when
  absolute error stays around `1e-16 .. 2e-16`.

Representative examples include:

- mid band `(1e-6,1e-3]`: `ulpE` up to `4096` while `|dE| <= 2.22e-16`
- high band `>1e-3`: `ulpE` small (`4..16`) with similar absolute `|dE|`

This reinforces that absolute-delta gating is the stable progress metric for the
recomposed scalar, while per-term ULPs remain the right place to constrain bit-level
drift component-wise.

To accelerate byte-exact iteration without rescanning all `1711` pairs every run,
the harness now supports a persisted stratified mismatch corpus:

- file: `tests/oracle/toolbox/DEM/_checkpoint_data/fsl_rgm_mi_mismatch_corpus_live.pkl`
- refresh: run
  `RGMS_MDP_MI_MISMATCH_CORPUS_REFRESH=1 pytest tests/oracle/test_spm_MDP_MI.py -k mismatch_corpus_micro_replay_oracle -s -q`
- micro replay test:
  `test_spm_MDP_MI_rgm_mismatch_corpus_micro_replay_oracle`

Current corpus characteristics:

- selected records: `48` (`24` mid-band + `24` high-band)
- deterministic selection rank:
  `ulpE desc, abs_dE desc, ulp_t1 desc, ulp_t2 desc, then stream/i/j asc`
- replay on current faithful path:
  - `py_self=0` (no Python drift on this corpus)
  - `py_vs_live=48` (all are known mismatch exemplars by construction)
  - `max_abs=4.5796699765787707e-16` (still within the `1e-15` envelope)

This corpus is for fast, high-signal candidate screening; full workload replay
remains the authoritative gate for broad behavior.

Compensated-reduction experiments (`RGMS_MDP_MI_EXPERIMENT_REDUCTION`) were added
for `_spm_MI` scalar reductions (`t1`, `t2`, `t3`) with modes:
`kahan_t1`, `kahan_t2`, `kahan_t3`, `kahan_t1_t2`, `kahan_all` (diagnostics-only;
default behavior unchanged).

Observed sweep outcomes (with `RGMS_MDP_MI_EXPERIMENT_TERM_ORDER=scalar_fwd`):

- Baseline scalar-fwd/default reduction: `py_vs_live=905` (full), `py_self=109`.
- `kahan_t2` was the best full-workload reduction-only candidate:
  - full replay: `py_vs_live=890`, `py_self=94`
  - corpus replay: `py_vs_live=46/48`, `py_self=20/48`
- `kahan_t1`, `kahan_t1_t2`, and `kahan_all` improved corpus mismatch counts but
  regressed full-workload `py_vs_live` and/or increased `py_self` substantially.

Recomposition sweep on top of `kahan_t2`:

- `sub_assoc=default`: `py_vs_live=890`, `py_self=94`
- `sub_assoc=t1_minus_sum23`: `py_vs_live=875`, but `py_self=788` (too unstable)
- `sub_assoc=t1_minus_t3_minus_t2`: `py_vs_live=1040` (regression)

Interpretation: compensated reduction on `t2` is the strongest currently observed
numerical lever, but still not faithful enough for adoption because self drift
remains non-zero on both corpus and full workload.

Refinement: micro-corpus oracle now reports **`py_repeat`** (same-runtime repeat
evaluation on identical `p`) separately from `py_self` (drift vs captured
historical Python value). This avoids conflating deterministic candidate behavior
with baseline drift from the stored checkpoint.

`math.fsum` reduction experiments (`RGMS_MDP_MI_EXPERIMENT_REDUCTION=fsum_*`) were
added as a second general-purpose, non-tailored family:

- `fsum_t2` currently gives the best observed full-workload live mismatch count in
  this family: `py_vs_live=874` (vs default `907`, scalar_fwd baseline `905`).
- It remains deterministic in-run (`py_repeat=0` on corpus), but still differs from
  captured Python baseline (`py_self=120` on full replay), so it is not adopted as
  default yet.
- `fsum_t1_t2` / `fsum_all` reduce some corpus mismatches but regress full-workload
  parity and/or increase baseline drift materially.

This keeps candidate evaluation faithful to MATLAB while preserving extensibility:
we test general numerical reduction strategies, then promote only if they improve
live MATLAB parity without introducing unacceptable global regression signals.

Cross-lane safety check (Bottleneck #2 spectral replay, tag `initial`) with
`fsum_t2` enabled showed **no change** from baseline:

- spectral fast replay: `py_vs_mat(order/chosen)=7/6`
- blocker micro: `order=5`, `chosen=5`

Because this spectral replay path recomputes grouping from captured `sub_mi`
workload records, the MI reduction experiment does not alter these specific
stored-block outcomes. This is useful as a non-regression signal: enabling
`fsum_t2` did not introduce new Bottleneck #2 divergence in this lane.

## Shared `matlab_compat.py`

Decision: repo-root `matlab_compat.py` is an approved narrow exception to the
default rule against shared runtime translation helpers.

This file may contain only mechanical MATLAB compatibility primitives that are
used by multiple translated files, such as row-vector normalization, sparse
`full` conversion, MATLAB-like scalar unwrapping, and size/ndims behavior. Do
not move file-specific translation logic such as cell-array interpretation,
tensor products, concatenation rules, or MDP field access into this helper.

Add new helpers there only after the behavior is repeated across multiple
translations and settled against MATLAB oracle behavior.

## `spm_cat` Scalar Zero Partitions

Decision: follow the repository MATLAB `.m` source, not the docstring text, for
scalar zero partitions.

The `spm_cat.m` docstring says single `0` entries are expanded, but the fallback
MATLAB source in this repository only replaces empty cells. The expression
`spm_cat({eye(2), []; 0, [1 1; 1 1]})` errors in the `.m` fallback with
inconsistent concatenation dimensions. Python should not implement scalar-zero
expansion unless the MATLAB source used as oracle changes.

## MATLAB cells: naïve `np.asarray` and same-shaped `ndarray` elements

Decision: when preserving MATLAB cell semantics in Python, do not rely on
naïve `np.asarray(...)` (including `np.asarray(..., dtype=object)`) for a Python
`list` (or similar sequence) whose elements are multiple NumPy `ndarray` values
with the **same shape**. NumPy may interpret that input as a request to stack
those arrays into a single numeric tensor (higher-dimensional `ndarray`), not
as a MATLAB-style cell vector of separate matrices.

When true MATLAB-cell behavior is required (each stored element remains its own
container entry, iterated in MATLAB `numel` / column-major order as in
`spm_dir_norm.m`), preserve the elements in an **explicit object container**
(for example, a preallocated `numpy.ndarray` with `dtype=object` and per-index
assignment, or another structure that cannot silently merge same-shaped
arrays). Apply the same care anywhere cell recursion must mirror MATLAB without
collapsing distinct `ndarray` cells into one stacked array.

This issue surfaced during the `spm_dir_norm` translation and oracle tests: a
flat Python list of two `2×2` matrices must behave like a `1×2` MATLAB cell,
not like a `2×2×2` numeric array.

## MATLAB Engine `eval`, struct arrays, `MDP.B` shape, and 1×1 scalars

These points were settled while closing **T5 `spm_MDP_checkX`** oracle tests.

**Identifiers in strings passed to `matlab.engine.MatlabEngine.eval` must be
valid MATLAB names.** In particular, a temporary variable must **not** start
with an underscore (`_tmp` fails with MATLAB’s “Invalid text character”
message). Use a name that starts with a letter (for example `rgms_tmp_mx`).

**Struct arrays vs cell arrays:** For a vertical stack of per-trial structs
such as `G_out = spm_MDP_checkX([t1; t2])`, `G_out` is a **struct array**. Index
the trial with **parentheses** (`G_out(1,1).A{1}`), not brace indexing
(`G_out{1,1}`, which errors with “Brace indexing is not supported for variables
of this type”).

**`MDP.B{f}` trailing `Nu = 1` dimension:** In MATLAB, `ones(n,n,1)` is stored
with `ndims == 2` and `size == [n n]` (trailing singleton dimensions are not
materialised the same way as in NumPy). After `spm_dir_norm`, Python should drop
a **singleton third** axis when present (`(n,n,1) → (n,n)`) so shapes match
MATLAB. When **`B` is synthesised** from missing `B` (`eye` branch in
`spm_MDP_checkX.m`), MATLAB uses **2-D** `eye(Ns(f),Ns(f))` only — not
`(n,n,1)`.

**1×1 arrays from the Engine:** A MATLAB `1×1` numeric matrix may arrive in
Python as a **0-dimensional** `ndarray` when pulled through `eval`. Oracle
comparisons against Python `(1,1)` fields can use `np.atleast_2d` on both sides
where this mismatch appears.

## `spm_dir_MI` multimodal cell + `h`

Staged `spm_dir_MI.m` line 25 calls `spm_dir_MI(a{g},c{g},h)` with the **full**
multimodal cell `h` on every `g`, not `h{g}`. That breaks `sum(A,1)*H` when
`numel(h) > 1` (inner `spm_cat(h(:))` stacks the wrong modalities). The Python
port passes **`h[g]`** per modality, consistent with `a{g}` and `c{g}`. Oracle
coverage for multimodal + `h` compares Python to the MATLAB **sum of
per-modality** calls `spm_dir_MI(a1,c1,h1) + spm_dir_MI(a2,c2,h2)`.

Local `spm_H` uses SciPy **`psi`** (digamma) to mirror MATLAB **`psi`**, not the
repo’s separate `spm_psi` helper (which implements a different expression).
**`spm_psi` vs `spm_dir_MI`:** `spm_psi.m` / `spm_psi.py` implement
**`psi(a) - psi(sum(a,1))`** (log-normalised Dirichlet **columns**, capped at
`-32`) — the **expectation of log marginals** path, **not** the `spm_H` entropy
formula inside `spm_dir_MI` (`psi(a0+1) - sum(a.*psi(a+1))/a0`). So **`spm_psi`
is not a drop-in substitute** for `spm_dir_MI`’s digamma usage; any `psi`
parity work targets **`scipy.special.psi`** vs MATLAB **`psi`** on the
**`a0+1`** and **`a_i+1`** arguments in **`spm_H`** only.

**Checkpoint probe (`test_spm_dir_MI_checkpoint_link_a_psi_vs_scipy`):** on
`MDP{2}.a{21}` from the snippet checkpoint MATLAB `MDP`, MATLAB vs SciPy
**`psi`** on every argument used by the three `spm_H` evaluations agrees to
**`<1e-14`**, and MATLAB **`sum(v.*psi(v+1))`** matches both NumPy vector sum
and Python’s sequential inner loop for the column marginal — so the observed
**Python `spm_dir_MI==0` vs MATLAB `~1e-16`** on that **`a`** is **not** explained
by SciPy vs MATLAB **`psi`** on sampled scalars nor by a simple inner-sum order
bug on that marginal alone; the probe’s recombined `H` terms still left a gap
until the **production** MI path matched MATLAB’s **sequential** marginal **`sum`**.

**Update (2026-04-24):** `python_src/spm_dir_MI.py` had defined
`_marginals_sum_matlab_like` / `_sum_all_matlab_like` but the **core**
`spm_dir_MI` MI term still used **`np.sum`** for **`sum(a,2)`** / **`sum(a,1)`**
and **`np.sum`** for **`sum(a,'all')`**. Wiring the core path to those helpers
restores MATLAB–Python agreement on checkpoint **`MDP{2}.a{21}`** in
`test_spm_dir_MI_checkpoint_link_a_psi_vs_scipy` **once that test mirrors the
exhaustive harness MATLAB path** (`addpath(matlab_src)`, **`cd` to
`matlab_src/toolbox/DEM`**, workspace name `MDP_fsl_snip_exact`). Without that
`cd`/path alignment, the checkpoint probe could pull a **different** linked
`a{21}` than the exhaustive reference while still “passing” an oracle.

**Open (2026-04-24):** exhaustive Lane C still shows **`spm_dir_MI(Python a)=0`**
while **`spm_dir_MI(MATLAB on Python a)`** matches MATLAB’s stored **`ss.ID`**
on the **same** `a_p` with **`np.array_equal(a_m, a_p)`** true — so the remaining
gap is **not** `_link_streams` matrix assembly; next step is to **diff** the
numeric `a` pulled inside **`_stream_link_mi`** at store time vs the `a_p`
extracted at compare time (e.g. optional `a_mat` dump under a debug env flag) or
run **`spm_dir_MI` under a debugger** mid-`spm_faster_structure_learning` to
rule out subtle **view / dtype / thread** interactions.

## `spm_dir_MI` near-zero MI on linked `a` (`ss.ID` / `ss.IE` bytes)

On the snippet T1000 exhaustive checkpoint with MATLAB EIG + MI_PUSH, the first
canonical-byte mismatch **had** sat in **`MDP{1}.ss.ID`** (e.g. key `(1, 58)`).
**`[SS-LINK-DIAG]`** showed: linked **`MDP{2}.a{gi}`** matches MATLAB **byte-for-byte**;
MATLAB’s stored **`ss.ID`** equals MATLAB **`spm_dir_MI`** on Python’s **`a`**;
Python **`spm_dir_MI`** **previously** returned **exact `0.0`** while MATLAB kept
**`~1e-16`** — isolating **`spm_dir_MI` / `_spm_H`** numerics and **`_link_streams`**
assembly (assembly was ruled out by byte-matched **`a`**). **Update (2026-04-24):**
core MI now uses MATLAB-like sequential marginals, **`sum(a,'all')`** via
`_sum_all_matlab_like`, and a Fortran-order **`a`** copy before MI. **Lane C**
exhaustive (`MI_PUSH`+`MATLAB_EIG`, native link `spm_dir_MI`) **still** fails at
**`MDP{1}.ss.ID{1,2}(1,58)`** as of the same date — see **`logs\log_0.md`** and
**`[SS-LINK-DIAG]`** “Open” note above. Harness-only **`RGMS_FSL_LINK_DIR_MI_MATLAB`**
remains the bridge sanity lane (**Lane D**). **Empirical (2026-04-22):** with
checkpoint + EIG + MI_PUSH + **`LINK_DIR_MI`**, the exhaustive oracle **passes**
(Lane D).

## `spm_dir_MI` current status policy (temporary, scoped, migration-safe)

This note captures the current settled operating policy so work can proceed to
other bottlenecks without confusing this as final global closure.

- **Runtime intent remains fully Python-native:** default `python_src/spm_dir_MI.py`
  does not call MATLAB Engine or import MATLAB outputs.
- **Default arithmetic is the general MATLAB-like expression form** in local
  `_spm_H` (`psi(a0+1) - sum(a.*psi(a+1))/a0` shape), with alternate float
  grouping retained only behind a diagnostics env flag.
- **Scoped tolerance acceptance is enabled only at link-MI assertion boundaries**
  (`ss.ID` / `ss.IE` checks in SL oracle paths), currently `abs(MATLAB-Python) <= 1e-15`.
- **Observed accepted residual class in this bottleneck lane** is typically
  around `8.88e-16` (both `0.0` vs tiny MATLAB nonzero and tiny nonzero-vs-nonzero).
- **Non-link assertions remain strict canonical-byte checks.** This is not a
  blanket tolerance policy for all translated outputs.

Rationale: this keeps `spm_dir_MI` non-hypertailored while documenting a narrow,
explicit migration policy at the known link-MI bottleneck boundary.

## Bottleneck isolation workflow policy (applies beyond `spm_dir_MI`)

Decision: for any newly investigated numeric bottleneck, use boundary-capture
replay as the default method before spending time on repeated long end-to-end runs.

Required workflow:

1. **Deterministic upstream state first**
   - Lock/random-replay upstream inputs so mismatches are attributable to the
     target bottleneck function.

2. **Capture exact runtime bottleneck inputs**
   - Save the true call-boundary inputs that enter the bottleneck function during
     execution (not only distant upstream checkpoints).
   - Save MATLAB outputs for those exact inputs in the same capture artifact.

3. **Fast replay oracle**
   - Add a replay test that compares Python vs stored MATLAB outputs using the
     captured boundary corpus.
   - Use this replay test as the inner loop for candidate experiments.

4. **Long-run discipline**
   - Reserve long exhaustive runs for milestone confirmation or intentional
     capture refresh/expansion.
   - Do not regress to long-run-only iteration after a boundary replay gate exists.

5. **Explicit acceptance scope**
   - If tolerance is used, it must be scoped to a named boundary, with clear
     magnitude, rationale, and tests; no implicit global relaxation.

## `spm_rgm_group` cell `O{o,t}` orientation (MATLAB Engine)

`spm_cat(R(o,:))` concatenates each time slice with the same **row** layout as
MATLAB `horzcat`. If `O{o,t}` is pushed into the Engine as a Python `tolist()`
from a column vector **without** an explicit `(Ns, 1)` shape, MATLAB may treat
it as a **1×Ns** row, producing a **1×(Ns·Nt)** `spm_cat` result instead of
**Ns×Nt** and breaking parity with NumPy. Oracle tests (and callers) should use
`matlab.double(..., size=(Ns, 1))` (or equivalent) so each `O{o,t}` is an
**Ns×1** column, matching `python_src`’s `(Ns, 1)` `ndarray` layout.

## `spm_rgm_group` spectral step: `eig`, `max(diag(v))`, and `sort(abs(...),'descend')`

This records cross-cutting lessons from debugging **byte-exact** parity on the
snippet-scale exhaustive checkpoint when the earliest failure sits inside
`spm_rgm_group`’s spectral grouping (`[e,v]=eig(MI(i,i),'nobalance');` then
`[~,j]=max(diag(v),[],1);` then `sort(abs(e(:,j)),'descend')` in staged
`spm_rgm_group.m`).

**Eigenpair column order is part of the contract.** MATLAB and SciPy may return
the **same multiset of eigenvalues** (up to floating noise) yet permute
**eigenvector columns** differently. The statement `[~,j]=max(diag(v),[],1)` is
always relative to **that function’s returned `v` layout**; you cannot infer
`j` from another library’s column order without an explicit alignment step.

**Principal direction can match while discrete outputs diverge.** Two
implementations can agree on the **dominant eigenvector up to global phase**
(entrywise residuals ~1e-15) and still produce different **`sort(abs(e(:,j)),'descend')`**
permutations when many `|e|` entries are **ties at printed precision** but differ
at **ULP** in the underlying floats. That changes early ranks in the sorted order,
hence which indices survive the `dx` cap / threshold, hence **canonical 1-based
group vectors** under strict byte equality.

**Validated vs guessed behavior.** On the failing checkpoint, NumPy
`argsort(-abs(x), kind="mergesort")` matched MATLAB’s `sort(abs(x),'descend')`
**when `x` was the exact MATLAB-exported principal column**. When `x` is the
Python-produced column from SciPy `eig`, the same sort rule can still diverge
from MATLAB because **`x` is not bitwise identical**, not because mergesort was
“wrong” in the abstract.

**Symmetric `MI(i,i)` still follows MATLAB’s general-real `eig` path.** Even when
the mutual-information block is symmetric positive semidefinite in theory,
MATLAB calls the **non-specialised** `eig` path (`'nobalance'`). Python should not
silently switch to `eigh` for convenience unless an oracle proves identical
**discrete** downstream choices (sorting + indexing), not just similar
eigenvalues.

**`sort(abs(e(:,j)))` uses complex magnitude.** MATLAB’s `e` is generally complex
from `eig`; the next line uses `abs` on that complex vector. A Python port that
first projects **`real(e(:,j))`** and only then takes **`abs`** can differ at
ULP scale from **`abs(e(:,j))`** when tiny imaginary parts are present, which
matters when many `|e|` entries sit in a **near-tie** band for `sort(...,'descend')`.

**Empirical checkpoint (2026-04-21, stream 1 group 2, spectral iter2):** with
`abs(complex)` aligned to MATLAB, SciPy `eig` vs MATLAB `eig` still yields a
**few-ULP** mismatch at the first sort-rank competitor row while the MATLAB
rank-1 row matches in **0 ULP** between `abs` vectors — enough to permute the
sorted index list under mergesort and change the discrete group vector under
strict byte equality.

**BLAS / LAPACK vendor (byte-exact `eig` gate):** the `rgms` conda stack here uses
**OpenBLAS-backed** NumPy/SciPy (`numpy.show_config` reports `scipy-openblas`).
MATLAB’s shipped linear algebra on Windows is typically **Intel MKL**. Both may
call **LAPACK `*geev`**, but **implementation and rounding differ** at the last
few ulps of eigenvectors — layout tricks (**C vs Fortran contiguous**,
`overwrite_a`, NumPy vs SciPy `eig`) did **not** change the failing checkpoint’s
`max|abs(e_py)-abs(e_mat)|` (~8.6e-16) or the **`js` permutation match** in a
dedicated probe. Closing a **strict byte-exact** spectral gate therefore likely
requires **toolchain alignment** (e.g. MKL-linked SciPy/NumPy where feasible and
authorized) or an **explicit MATLAB-backed** reference for this step — not
further local Python tie-break tweaks alone.

**Policy reminder:** if a new corner case needs a project decision (for example
accepting non-byte grouping when LAPACK layouts differ), ask the user first, then
record the settled rule here or in the repo-root `Python Matlab Translation Issues.md`.

## `spm_RDP_sort` NESS vector: same `eig(B,'nobalance')` discrepancy class as `spm_rgm_group`

This is **not** a new numerical phenomenon; it is the same cross-cutting issue
already documented above for `spm_rgm_group`’s spectral step (MATLAB
`eig(...,'nobalance')` vs a native Python/SciPy/NumPy `eig` pipeline, BLAS
vendor differences, and **ULP-level** drift in the principal vector that still
passes loose `allclose` checks against a MATLAB capture).

**MATLAB source (`matlab_src/toolbox/DEM/spm_RDP_sort.m`).** After building the
normalised flow matrix `B`, MATLAB does `[e,v]=eig(B,'nobalance');`,
`[~,j]=max(real(diag(v)));`, then `p = spm_dir_norm(abs(e(:,j)))'` (row NESS
vector), then a **stable** ascending `sort(p,'ascend')` to drive the NESS pruning
loop, then a descending sort on retained indices, then `spm_RDP_compress`.

**Entry-10 boundary (Atari sort capture, small `training_t` / `n_outer`).**
Measured with the same `B` built in Python as in the capture (`B` matches
`B_mat` bitwise): MATLAB Engine `eig(B,'nobalance')` reproduces the captured
`p_mat` **exactly** (including the **multiset of float values** in `p`, e.g. 62
distinct probabilities on that boundary), while `np.linalg.eig(B)` on the
identical `B` can still agree with `p_mat` to ~1e-15 **elementwise** yet collapse
to **fewer distinct float levels** (e.g. 55 on that boundary). That changes the
**effective tie structure** for MATLAB’s stable `sort`, hence the **removal
order** in the pruning `for i=k` loop, hence the surviving state index in `j`
even when `B` and `spm_dir_norm` paths match the capture.

**Verification policy (already established for structure learning).** For
**gated** parity of the full `spm_RDP_sort` pipeline (NESS `p`, pruning mask,
final `j`, compressed `MDP`), treat **MATLAB outputs** (capture artifacts and/or
live Engine) as the reference for this eigen-step—just as
`spm_faster_structure_learning` exposes optional `rgm_eig_pair` and the harness
uses `RGMS_FSL_RGM_MATLAB_EIG=1` / `_make_matlab_rgm_eig_pair(...)` to inject
MATLAB `eig(...,'nobalance')` into `spm_rgm_group` for oracle work. Do **not**
re-diagnose the pruning `if all(any(B(d,d)),1))` loop or `np.lexsort` tie policy
in isolation when the dominant eigenvector from native `eig(B)` is not the same
**discrete** object MATLAB used; that work is **redundant** once the eigen-step
mismatch class is recognised.

**Implementation (2026-05-02).** ``python_src/toolbox/DEM/spm_RDP_sort.py`` ``spm_RDP_sort`` accepts a
keyword-only ``eig`` hook ``(B) -> (w, V)`` (same layout as ``numpy.linalg.eig``). The Entry-10 boundary
oracle ``test_spm_RDP_sort_matlab_boundary_oracle`` passes MATLAB ``eig(B,'nobalance')`` via
``_make_matlab_spm_RDP_sort_eig`` in ``tests/oracle/toolbox/DEM/test_spm_RDP_sort.py``, analogous to
``rgm_eig_pair`` → ``spm_rgm_group(..., eig_pair=...)``. Default callers omit ``eig`` and keep native
``numpy.linalg.eig`` for the committed Pass-1 transliteration unless/until toolchain alignment
(MKL-linked NumPy/SciPy, etc.) is explicitly authorised and proven sufficient.

## `spm_MDP_generate` prescribed `s` / `u` and local `spm_induction`

**Copying prescribed states/controls:** MATLAB `try … find(MDP.s); k(i)=MDP.s(i)` copies
non-zero linear indices into a fresh `Nf×T` zero matrix. A naïve Python port that
does `s_new.ravel(order="F")[ii] = s0.ravel(order="F")[ii]` on `s_new =
zeros((Nf,T))` can **fail silently** because `ndarray.ravel("F")` may return a
**copy** (not a view) when the buffer is C-contiguous, so assignments never
reach `s_new`. When `(Nf,T)` matches, assign with `s_new[:, :] = s0`; otherwise
scatter with `np.unravel_index(..., order="F")`. Apply the same pattern to
`u`.

**`hid` / `hif` and `G(k)=R*P{r,k}`:** Staged `spm_MDP_generate.m` calls
`G(k)=R*P{r,k}` where `r` is the second output of `spm_induction`. In MATLAB
R2024b this line **errors** with “Too many input arguments” when `numel(r)>1`
(two or more factors in `hif`). Oracle coverage for `spm_induction` therefore
uses `id.hid` shaped so `hif` is a **single** factor index (e.g. one non-zero
row in `hid`). Python matches that regime and builds the Kronecker column stack
with `np.kron` in `r_fac` order when `numel(r)==1`.

## RNG: `spm_MDP_generate`, logical `A{g}`, `spm_sample`, and MATLAB–Python `rand()` replay

This subsection records what was learned while closing the **Pong → GDP →
`spm_MDP_generate`** integration oracle (`tests/oracle/toolbox/DEM/test_spm_MDP_pong_generate_integration.py`).
The goal was strict rollout parity (`s`, `u`, `o`, and `O{g,t}`) under a shared
random-number contract. The lessons generalise to other MATLAB-to-Python work
where tests **replay** MATLAB’s scalar `rand()` stream in NumPy.

### MATLAB local `spm_sample` has two incompatible paths

In staged `spm_MDP_generate.m`, the nested `spm_sample` behaves as follows:

- **Logical `P`:** `i = find(P); i = i(randperm(numel(i),1));` — uniform choice
  among the linear indices returned by `find(P)` (sorted order for a logical
  matrix), implemented via **`randperm`**, not via `cumsum` of a normalised
  column.
- **Numeric `P`:** `i = find(rand < cumsum(P),1);` — one scalar **`rand()`**
  per call (for the usual column-stochastic `P`), with MATLAB’s column-major
  `cumsum` down the column.

Python must branch on **`dtype == bool`** (after slicing) the same way. If
likelihood columns are coerced to **`float64`** before sampling (for example by
`np.asarray(A{g}, dtype=np.float64)` before indexing), every logical modality
silently takes the **numeric** path. That is not just a distribution bug: it
changes **how many** scalar random draws occur and in what order, so **all**
later draws (policy `PK` sampling, state transitions, further outcomes)
desynchronise even when a MATLAB `rand()` buffer is replayed in Python.

**Decision:** when translating outcome generation, slice **`MDP.A{g}`** (Python
`mdp["A"][g]`) without destroying logical dtype; densify sparse slices to a dense
array for indexing, then pass the resulting column to `_spm_sample` as **bool**
or **float** according to the slice’s dtype. Store `O` cells for oracles in a
numeric form compatible with `full(...)` comparisons (for example `float64`
0/1 for former logical columns).

### `randperm(k,1)` is not universally “one `rand()`” on the twister stream

For oracle tests that patch **`numpy.random.rand`** with a vector of values from
MATLAB **`rand(N,1)`**, every Python call to `np.random.rand()` must correspond
to one MATLAB **`rand()`** scalar in order. MATLAB’s **`randperm(k,1)`** does
**not** always advance that stream by exactly one **`rand()`** output.

Empirical checks on MATLAB’s **`twister`** generator (used deliberately in the
oracle) showed the following **stream alignment** relative to successive MATLAB
**`rand()`** outputs after a common `rng(seed,'twister')` reset:

- **`k == numel(i) == 1`:** no scalar **`rand()`** consumption (deterministic
  choice among a single index).
- **`k` in `{2,3,4}`:** **`randperm(k,1)`** advances the global stream by **two**
  successive MATLAB **`rand()`** scalars. The **selected** linear index among the
  `k` positives still matches **`floor(k * r1) + 1`** in **1-based** position
  along MATLAB’s sorted `find(P)` list, where **`r1`** is the **first** of those
  two scalars; the **second** scalar must still be drawn in Python so the next
  `rand()` in the replay buffer lines up with MATLAB’s next explicit or implicit
  draw.
- **`k >= 5`:** **`randperm(k,1)`** advances the stream by **one** MATLAB
  **`rand()`** scalar, with the same **`floor(k * r1) + 1`** mapping to a
  1-based position among the `k` entries (equivalently 0-based
  **`floor(r1 * k)`** clamped to `0 … k-1` on `flatnonzero` order).

**Decision:** Python’s `_spm_sample` for boolean masks implements the above
consumption pattern so that **`rand()` replay** matches MATLAB for
`spm_MDP_generate` rollouts. Do **not** substitute **`np.random.permutation`**
for parity with MATLAB **`randperm`** under this replay scheme: NumPy’s
permutation machinery does not consume the patched **`rand()`** sequence in a
MATLAB-identical way.

### Fix the MATLAB **generator label**, not only the seed integer

`rng(0)` without a second argument selects MATLAB’s **current default**
algorithm, which can differ across MATLAB versions and session settings. A
buffer built with one generator label and a script run with another will not
match even if the seed integer is zero.

**Decision:** for paired MATLAB/Python oracles that record `rand(N,1)` in
MATLAB and replay it in Python, set the generator **explicitly** on the MATLAB
side (for example **`rng(0,'twister')`**) both when running the reference and
when filling the buffer, and document that choice next to the test.

### Preamble before `spm_MDP_generate` matters for the buffer

`spm_MDP_pong(..., Np=0)` does not execute the “random pixels” loop in `.m`, so
with `Np == 0` MATLAB Pong does not consume **`rand()`** before
`spm_MDP_generate`. If **`Np > 0`**, MATLAB Pong calls **`rand()`** during
construction; any oracle buffer must then be collected **after** the same
Pong call (and any other preamble) that the reference script runs, not from a
bare `rng; rand(N)` in isolation.

### `spm_faster_structure_learning` on `PDP.O(:,1:k)` (tiered T11)

**`test_spm_faster_structure_learning_pdp_o_slice_integration_oracle`** builds
the same **`GDP` / `PDP`** as the §1.1 integration oracle (`spm_MDP_pong(4,4,1,1,0)`,
**`GDP.T=4`**, **`tau=1`**, **`rng(0,'twister')`**), then slices **`PDP.O(:,1:k)`**
for small **`k`** and runs **`spm_faster_structure_learning(..., S, dx, dt)`**
with the §5 snippet-shaped **`S`**. Python **`spm_MDP_generate`** is driven with
**`numpy.random.rand`** patched from a MATLAB **`rand(8192,1)`** buffer collected
**after** the same preamble (same pattern as **`test_spm_MDP_pong_generate_integration`**).
Structure learning itself is deterministic given **`O`**; the replay contract
matters so **`O`** matches before SL runs. The PDP slice oracles in
**`test_spm_faster_structure_learning.py`** assert **`PDP.O(:,1:k)`** cell-by-cell
against Python’s **`pdp["O"]`** immediately after **`spm_MDP_generate`** (same
**`rand`** patch) and **before** **`spm_faster_structure_learning`**, so the
Pong→generate→**`O`**→SL numeric chain is checked in one test path without figures.

On this path, **`spm_log`** and **`spm_MDP_MI`** can emit NumPy **`RuntimeWarning`**
(divide-by-zero in **`log`**, invalid divide in MI) on degenerate Dirichlet
slices—MATLAB does not surface equivalent warnings. The PDP slice oracle test
filters those two known messages so pytest’s warnings summary stays actionable;
do not silence new warning classes without confirming MATLAB parity.

**`SPINBLOCK`:** Staged `spm_faster_structure_learning.m` sets **`SPINBLOCK = false`**
(the mutual-information / **`spm_rgm_group`** partition). The §5 gameplay snippet
uses that default. RGMs Python mirrors **`~SPINBLOCK`** only for this chain; the
**`true`** branch (spatial **`spm_group`** blocks, alternate **`S`** / **`O`**
advance at the level boundary) is **not** required for snippet-level “complete
T11” or for Pong→generate→SL integration oracles until a driver explicitly enables
it and we add a dedicated oracle (Engine would call the same flag in staged `.m`).

**Wider outcome windows:** With **`GDP.T = 4`**, **`PDP.O`** has only four time
columns, so **`k ≤ 4`** is the natural cap for slice parity at that configuration.
Tiered coverage for larger **`k`** (toward the script’s **`1:1000`**) uses a larger
**`GDP.T`** in a separate oracle (marked **`slow`** when **`T`** or **`k`** is
large) and a proportionally larger **`rand(N,1)`** replay buffer so
**`spm_MDP_generate`** does not exhaust the patched stream mid-rollout.

Current tier coverage includes a snippet-scale slow oracle:
**`spm_MDP_pong(12,9,4,1,0)`**, **`GDP.T = 1000`**, **`PDP.O(:,1:1000)`**,
**`S(1,:)=[12,9,1]`**, and **`spm_faster_structure_learning(...,Sc)`** with
**`Sc = 9`**. This matches the non-plotting end of the §5 snippet.

An additional **exhaustive canonical-byte comparator** exists for this same
snippet-scale setup. It traverses all nested `MDP` entries (`a`, `b`, `id`,
`G`, `sA/sB/sC`, `ss`) and compares canonicalized bytes field-by-field.
Current status: **expected mismatch** at least at **`MDP{1}.a{5}`** on the
snippet-scale run; the exhaustive test is marked **`xfail`** while the exact
state-ordering divergence is investigated.

### Forward-ordered mismatch triage rule (active T11 workflow)

For snippet-scale reproducibility work on
`spm_faster_structure_learning(PDP.O(:,1:1000),S,Sc)`, treat late-field
differences (for example `MDP{1}.a{5}`) as **symptoms**, not immediate fix
targets. The required triage order is:

1. confirm replay-controlled equivalence from the earliest operation in the
   active pipeline path;
2. locate the first checkpoint that diverges;
3. fix only that earliest divergence;
4. revalidate all prior checkpoints before touching downstream leaves.

This prevents unstable “fix-later-then-backtrack” cycles and keeps progress
coherent with the reproducibility objective.

### Scope limit of `rand()`-only replay

Replaying **`rand()`** scalars covers every draw that the translated code routes
through **`np.random.rand()`** with the same call order as MATLAB’s use of
**`rand()`** in the mirrored paths. It does **not** automatically cover other
MATLAB RNG entry points (`randi`, `randn`, internal toolbox calls) unless those
are also bridged or the test uses a different strategy (for example structural
comparison without bit-identical RNG, or a full portable generator port).

## `spm_backwards` (from `spm_MDP_VB_XXX.m`)

**Staged MATLAB:** `matlab_src\toolbox\DEM\spm_backwards.m` (extracted from
`spm_MDP_VB_XXX.m` with local `spm_norm` and `spm_children` so the Engine can call
it on the path).

**Python:** `python_src\toolbox\DEM\spm_backwards.py` — Pass 1 transliteration in
progress.

**Oracle:** `tests\oracle\toolbox\DEM\test_spm_backwards.py` now passes on the
minimal `Nm=1, Nf=1, T=2` Engine case (`F` and `Q{1,1,1}`), after fixing
`pagetranspose` semantics in Python (`swap first two dims per page`, not last two).

**Integration status:** this closes standalone `spm_backwards` parity on the current
gate, but `spm_backwards` is still not yet wired into the main
`spm_MDP_VB_XXX` `OPTIONS.B` tail.

---

## `spm_MDP_VB_XXX` (Entry 12): local `spm_sample` and RNG surface

**MATLAB source:** `spm_MDP_VB_XXX.m` ends with a file-local `spm_sample(P)` (same
pattern as staged `spm_MDP_generate.m`):

- **`islogical(P)`:** `i = find(P); i = i(randperm(numel(i),1));`
- **else:** `P = cumsum(P); i = find(rand*P(end) < P,1);`

A scan of `spm_MDP_VB_XXX.m` for **`rand` / `randn` / `randi`** shows **only** the
numeric-branch draw inside **`spm_sample`** (no other stochastic primitives in that
file). So for Pass 1 translation, mirroring **`spm_MDP_generate`’s `_spm_sample`**
—including **logical vs numeric branching**, **twister `randperm` consumption**
for `2 ≤ k ≤ 4` (see **MATLAB local `spm_sample` has two incompatible paths** and
**`randperm(k,1)` is not universally “one `rand()`”** above)—is the correct basis
for **draw-aligned** MATLAB vs Python oracles on this engine.

**Oracle discipline:** use the same artifact workflow as
**`test_spm_MDP_pong_generate_integration`**: record MATLAB **`rand(N,1)`** after
the **same preamble** and generator label (`rng(seed,'twister')`), patch
**`numpy.random.rand`** in Python to consume that buffer in order, and compare
outputs at the agreed boundary (`PDP` / nested `MDP` fields). If future SPM edits
add **`randn`** / **`randi`** / other draws in `spm_MDP_VB_XXX.m`, revisit this
subsection and extend the replay bridge explicitly.

**Entry 12 call-2 regroup note (2026-05-27):** do **not** globally coerce numeric
0/1 columns to logical in `spm_MDP_VB_XXX` sampling helpers. Paired MATLAB
trace on `rgms_atari_call2` shows early `spm_sample` sites where MATLAB passes a
numeric one-hot/delta vector (`double`, pattern `N1`) and still consumes one
scalar `rand()`. Blind numeric-0/1→bool coercion reduces Python draws, breaks
`K` consistency, and can manufacture misleading "fixed" local rows while moving
the stochastic trajectory. Only preserve logical semantics when the source
column is actually logical at the call site.

### Entry 12 call-2 — generative process (`GA`/`GB`/`GU`/`GD`) MATLAB inventory

**Call context:** Entry 12 **call 2** (`RGMS_ENTRY12_CAPTURE_RUN_TAG=rgms_atari_call2`)
exercises hierarchical VB with a nested **process** child. Call **1**
(`rgms_canonical`) does not attach `GDP.A/B/U/D` to the parent in the same way;
call 2 is the lane that proves `spm_MDP_VB_XXX` works when `MDP.MDP` carries
generative-process tensors copied from Pong.

**MATLAB assembly (driver):** `matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m`
→ `entry12_dem_call2_rdp_game1_` assigns, on the parent model shell:

- `MDP{1}.GA = GDP.A`
- `MDP{1}.GB = GDP.B`
- `MDP{1}.GU = GDP.U`
- `MDP{1}.GD = GDP.D`
- `MDP{1}.ID = GDP.id`
- `MDP{1}.chi = 512`

then `spm_set_goals`, `spm_set_costs`, `spm_mdp2rdp`. Saved fixture:
`tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_rgms_atari_call2_rdp.mat`
with **`RDP.MDP.GA`** at the **top-level** parent (111 modalities), not under a
nested `MDP.MDP` row in the saved `.mat`.

**MATLAB source of `GDP.A` (Pong):** `matlab_src/toolbox/DEM/spm_MDP_pong.m`
builds outcome likelihoods mostly as **`logical`**:

- Default grid modalities `A{g} = false(5,Ns,Nc)` with background row set `true`.
- Paddle overlays assign `true`/`false` on logical tensors.
- Random-pixel distractors: `A{j} = logical(full(spm_speye(5,3)))`.
- With **`Na=true`** (Atari call 2 uses `spm_MDP_pong(..., Na=true, Np=0)`), the
  **`if true`** branch appends proprioception as **`A{end+1} = eye(Nc,Nc)`** —
  a **`double`** identity matrix (not wrapped in `logical(...)`). For the Atari
  grid `Nr=12`, `Nc=9`, this is modality **g=111**, shape **`[9 9]`**, **`No=9`**.

**Measured classes on the saved call-2 RDP (MATLAB R2024b, fixture above):**

| Field | Count | Classes |
|-------|------:|---------|
| **`GA{g}`** | 111 | **110× `logical`**, **1× `double`** (g=111 proprioception `eye(9,9)`) |
| **`GB{f}`** | 2 | **2× `double`** (`[176 176]` factor 1; `[9 9 3]` factor 2 after `spm_dir_norm`) |
| **`GU`** | — | **`double`** (not a cell; scalar/matrix control tensor) |
| **`GD{f}`** | 2 | **2× `double`** (`[176 1]`, `[9 1]`) |

Note: Pong initially constructs **`B{1}`, `B{2}`** as **`false(...)`** (logical),
but **`spm_dir_norm(B)`** before export yields **`GB`** stored as **`double`** in
the saved RDP. Do not assume “binary ⇒ logical” from values alone on **`GB`**.

**VB assignment inside `spm_MDP_VB_XXX.m`:** process child gets direct copies
(`GP(m).A = MDP(m).GA`, same for `B`, `U`, `D`). Local **`spm_sample(P)`** branches
only on **`islogical(P)`** — no modality-size heuristics.

**`loadmat` dtype loss (Python oracle lane):** `scipy.io.loadmat(..., simplify_cells=True)`
on the call-2 RDP maps **all** `GA{g}` leaves to **`uint8`**, including the
proprioception **`double`** `eye(9,9)` (binary-valued). That makes Python treat
110 logical modalities as numeric at `spm_sample`, changing draw counts vs MATLAB.

**Decision (2026-05-27):** restore dtypes at the **load/assignment boundary** in
`tests/oracle/toolbox/DEM/entry12_loadmat_convert.py`, guided by MATLAB class
metadata exported to
`tests/oracle/toolbox/DEM/fixtures/entry12_call2_gp_matlab_class.json`
(see `matlab_custom/entry12/export_call2_gp_class_json.m`). Apply via
`load_entry12_rdp_mat_nested_for_tag(..., tag='rgms_atari_call2')` before
`spm_MDP_checkX`. Do **not** add `No<=5` or other modality-count rules inside
`_spm_sample` or `_vb_coerce_process_gp_A_like_matlab`.

**RNG consequence:** logical `GA` columns must reach `_spm_sample` as **`bool`**
so `k=1` sites consume **0** draws and `2≤k≤4` sites consume **2** draws, matching
MATLAB `randperm` replay. The proprioception **`double`** column stays numeric
(**`N1`**, one draw). This is the approved fix for call-2 nested-child trace skew
(e.g. py `N1` vs mat `L0` at early seqs) without rejected global 0/1→bool coercion.

**Implemented slice:** `python_src/toolbox/DEM/spm_MDP_VB_XXX.py` defines **`_spm_sample`**
(Pass 1 duplicate of `spm_MDP_generate._spm_sample`). Closed-oracle coverage:
**`tests/oracle/toolbox/DEM/test_spm_MDP_VB_XXX_spm_sample.py`** (MATLAB Engine inline
scripts + drift guard vs `spm_MDP_generate`).

## `spm_MDP_pong`: `nP` output, `RGB.V` layout, PNG read vs MATLAB `imread`

**`nP` when `Np==0`:** Unmodified SPM `spm_MDP_pong.m` never assigns `nP` if the
distractor loop does not run, so requesting six outputs from MATLAB errors. The
staged copy under `matlab_src\toolbox\DEM\spm_MDP_pong.m` adds `nP =
zeros(1,Np)` after the default `Np` handling so Engine/oracle calls remain valid.
Python returns `nP` as a **1×Np** `float64` row (`zeros((1,0))` when `Np==0`).

**`S(s,:) = r` dynamic growth:** MATLAB grows `S` automatically when assignment
index `s` exceeds current rows. In `spm_MDP_pong.py`, the deterministic path for
larger grids (for example `12×9`) can exceed the initial `Ng` rows before loop
closure, so Python must explicitly append zero rows before `S[s-1,:] = r`.

**`RGB.V`:** MATLAB assigns **the same** basis matrix `V` into **every**
location of an **Nr×Nc** cell array (`RGB.V{i,j} = V`). Python mirrors this with
a list-of-lists of shape **Nr×Nc**, each entry a copy of the `192×5` matrix (for
`n=8`). Oracle tests compare `RGB.V{1,1}` to `RGB["V"][0][0]`.

### `spm_O2rgb` (T10) Engine pulls

**`test_spm_O2rgb.py`** assigns MATLAB workspace temps with **`eng.eval("rgms_tmp_mx = …")`**
when reading **`PDP.O{g,t}`**, **`RGB.G{i,j}`**, and **`RGB.V{i,j}`**. Temps whose names
start with an underscore (for example **`_oc`**) triggered **“Invalid text character”**
from MATLAB Engine **`eval`** in this environment; use **`rgms_`-prefixed** names
consistent with other DEM oracles.

**`RGB.V` oracle tolerance:** MATLAB `imread` applies PNG **gAMA / display**
handling for the DEM sprites; PyPNG’s `asDirect()` decode matches **raw**
stored samples and can differ from MATLAB by **well over 100** per channel on
the same file. `tests\oracle\toolbox\DEM\test_spm_MDP_pong.py` therefore uses
`assert_allclose(..., atol=155)` on `RGB.V` only; `RGB.N`, `RGB.G`, and the
full `MDP` structure remain tight (`assert_matlab_match`). Revisit if Python
gains MATLAB-equivalent ICC/gamma handling for these assets.

**Dependency:** `pypng` was added to the **`rgms`** conda environment (`pip
install pypng`) for PNG loading in `python_src\toolbox\DEM\spm_MDP_pong.py`.

**Oracle priority (structure-learning path):** Default pytest oracles emphasize
parity on **`MDP`** and returns used by **`spm_MDP_generate`** (`hid`, `cid`,
`con`, **`id`** including **`Na=true`** branches: **`reward`**, **`contraint`**,
**`control`**). **`spm_O2rgb`** now has its own oracle (`test_spm_O2rgb.py`),
while snippet-completion work intentionally defers plotting-loop invocation
(`spm_figure` / `imshow` / `drawnow` and in-loop `spm_O2rgb(...)`) to **T12**
scope in `structure_learning_plan_week2.md`.

**`Na` reward / constraint tensors:** MATLAB builds `a = false(2,...)` then
`a(1,:,:) = true` before clearing/placing hits or misses. An early Python
mistake used `np.ones((2,...))`, which incorrectly set **both** outcome rows to
true initially; Port uses **`zeros`** then **`a[0,:,:] = True`** to mirror the
`.m` source.

## `spm_MDP_VB_XXX`: `Pu_carry` vs `spm_forwards` / `spm_VBX`

MATLAB sets **`Pu = spm_softmax(G, alpha)`** after **`spm_forwards`** builds **`G`**
(`spm_MDP_VB_XXX.m` ~1326, with **`G`** from ~1261).

**Current Python (`spm_MDP_VB_XXX.py`, `_vb_run_partial_t_loop`):** each **`t`**: generation, then
**`if OPTIONS.O`** outcome blocks, then **`BP`/`IP`**, then **`spm_forwards`** (**`spm_VBX`**) and
**`_vb_belief_after_forwards`** (**~1264–1346**) for every model in **`M(t,:)`** — **no skip** when **`O`**
is empty (removed interim **`_vb_placeholder_pu_carry_softmax`** / **`_vb_o_row_ready_for_model`** guard, 2026-05-18).
**`isempty(O)` one-hot (`.m` ~977–978):** **`_vb_generate_outcomes_if_options_o`** (12E) + **`_vb_fill_O_empty_from_realized_o_at_t`** at 12E→12F seam before belief — authoritative policy in **`Atari_example.md`** § **Entry 12 workflow — four scripts** / **Script 3 compute contract**.
**`run_dem_atariiii(entry_stop=12)`** calls **`spm_MDP_VB_XXX(RDP)`** in **full mode** (no `_rgms_partial_ok`) and returns an
assembled **`PDP`**. Optional **`_rgms_partial_ok`** remains for staged isolation only (not the driver acceptance path).
Full level-0 **`F`** vs MATLAB on the Entry-12 artifact lane is gated by **`test_entry12_python_full_F_vector_parity_from_artifact`**
(documented under **Entry 12 (DEM_AtariIII): authoritative full level-0 `F` parity gate** below).

## Empty policy rows / `Nu == 0` in `spm_MDP_checkX` and `spm_MDP_VB_XXX._spm_norm`

Nested RDPs can produce factors with **zero** control count **`Nu(f)=0`** (e.g. **`B{f}`** with a
degenerate third dimension). **Guards (2026-05):** `spm_MDP_checkX` uses **`zeros((0,1))`** for default **`E{f}`**
instead of **`spm_dir_norm(ones((0,1)))`**; **`spm_dir_norm`** skips **`1/size(A,1)`** when **`size(A,1)==0`**;
**`_spm_norm`** in **`spm_MDP_VB_XXX`** returns empty arrays without **`1/Ns`** NaN repair when **`Ns==0`**.
**`spm_set_costs`** uses **`np.atleast_1d`** on **`U`** so scalar/broadcast **`U`** does not yield a 0-D boolean
working vector.

### Degenerate **`spm_sample`**, **`Np==0`**, **`spm_induction`** (2026-05-04)

Nested Atari **`RDP`** can yield zero-sum / NaN probability columns before **`cumsum`**, **`Np==0`** (empty **`V`** rows)
while MATLAB still writes **`BP{m,f,1}`** on uncontrolled factors, **`Pu_carry`** length zero at **`t>1`**, and
**`id.hid`** stored as a **1-D** NumPy vector. Python mirrors **`spm_MDP_generate._spm_sample`** in **`spm_MDP_VB_XXX`**:
uniform fallback when total mass is non-positive / non-finite; **`r==1`** maps to the last bin; **`BP`/`IP`** inner
policy dimension uses **`max(Np,1)`** slots; **`_vb_belief_after_forwards`** treats **`Np==0`** **`G`** without reshaping
to **`(0,-1)`**; **`_vb_prior_QP_paths_states_one_model`** skips **`spm_sample`** on empty **`Pu`** and skips **`V`**
indexing when **`V`** has zero rows; **`spm_forwards._spm_induction_vb`** promotes **`hid`** to **`Ns×1`**, skips
factors with empty **`B{f}`** tensors (subset **`hid`** rows to **`hif_kept`**), and returns empty **`R`** when no valid
induction tensor remains; **`_vb_gp_transition_column`** returns zeros when **`size(B,3)==0`**. Treat as **numerical
stability** on degenerate graphs; run Engine oracles on captured **`RDP`** slices when claiming MATLAB parity.

## `spm_MDP_VB_XXX` local `spm_multiply` (~2603) — not elementwise `p.*q`

**MATLAB** (nested in ``spm_MDP_VB_XXX.m``): ``p = spm_softmax(spm_log(p) + spm_log(q))`` — renormalised **log-domain** product.

**Do not** replace with ``spm_norm(p .* q)`` when porting hierarchical ``id.E`` / ``id.D`` updates (~1063, ~1071). **Python**
uses file-local ``_spm_multiply`` + existing ``_spm_log`` / ``spm_softmax``; see ``test_vb_local_spm_multiply_is_softmax_log_sum``.

## Nested `spm_action` in `spm_MDP_VB_XXX` (~2688–2766)

**MATLAB** implements explicit-action selection for generative-process agents as a **nested** function
``spm_action(MDP,A,Q,t)``. The hierarchical subordinate call (~1087) uses ``Q = mdp.D`` and ``t = mdp.T``.

**Python** mirrors this as file-local ``_spm_action`` (same arguments). ``spm_parents`` is called with
``id`` (likelihood index structure) for both outcome prediction and inner free-energy terms; MATLAB line ~2753
writes ``spm_parents(MDP.ID, ...)`` but the likelihood graph lives on ``id`` — Python follows ``id`` for both loops.

Main-loop process control (~814–816: ``spm_action(MDP(m),A(m,:),Q(m,:,t),t-1)``) is wired through
``_vb_gen_control_one_model`` → ``_spm_action``, passing ``bundle['A'][m]``, per-factor ``Q`` at timestep ``t_idx``,
and fourth argument ``t_idx`` (MATLAB ``t-1`` when Python ``t_idx`` matches the inner loop index). Process models
without ``GV`` still raise ``NotImplementedError``.

## Hierarchical `S` → `O` before child `spm_MDP_VB_XXX` (~1136–1151)

**MATLAB** removes ``O``/``o`` from the subordinate ``mdp``, then if ``isfield(mdp,'S')`` sets
``mdp.O = mdp.S(:, seg(j))`` with ``j = (seg <= size(mdp.S,2))`` and
``seg = (1:mdp.T) + size(mdp.Q.O{mdp.L},2)`` when ``mdp.Q`` exists, else ``seg = (1:mdp.T)``.

**Python** uses ``_vb_hierarchical_apply_S_as_O_if_present`` immediately after ``child.pop("O")``/``"o"``, before
the recursive call. ``Q.O{mdp.L}`` is approximated as the list index ``L-1`` of the child’s ``Q['O']`` cell (width =
last axis of that array). If no column index is valid, ``O`` is **n×0** (not omitted), matching ``S(:,seg(j))`` with
all-false ``j``.

## Child init: ``MDP(m).O{g,t}`` vs dense ``mdp.O`` from ``S`` (~732–752, Entry 12 **12F**)

**Ground truth:** ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~732–752 (band **12B**).

After hierarchical ``mdp.S→O`` (~1189–1191), ``mdp.O`` is a **dense matrix** (stacked stimulus columns), **not**
a ``Ng×T`` cell array. Init only loads outcomes via curly indexing ``MDP(m).O{g,t}`` (~741). That fails for the
matrix → ``catch`` (~747–748) sets ``O{m,g,t} = []`` (~748); outcome generation ~913–985 then fills ``O{m,g,t}``
(e.g. ``GP(m).A{g}`` when ``n==0``, ~961–967).

**Python policy (2026-05-19):** ``_vb_mdp_O_is_cell_gt_layout`` gates the ~732–752 mirror in
``_vb_init_QXSP_outcomes_and_process``. Do **not** read ``mdp.O[g,:]`` as modality ``g`` on a numeric matrix (that
disabled generation and broke ``12F.out_t1.MDP.MDP.Q.O[*]`` vs MATLAB). Code comments cite ``.m`` line ranges, not
``OPTIONS.O`` toggles as the story.

**Validation 12:** first red for this class was ``12F.out_t1.MDP.MDP.Q.O[1]`` (living list in
``matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt`` after **3→4**).

## Hierarchical `mdp.Q` record append (`try/catch`) (~1180–1209)

**MATLAB** updates child ``mdp.Q`` after recursion by:

- optional ``mdp.Q.a{mdp.L} = mdp.a`` when ``a`` exists,
- appending ``s,u,P,X,Y,O,o,j,E`` at level ``L`` with ``[old new]``,
- accumulating scalar ``mdp.Q.F = mdp.Q.F + sum(mdp.F)``,
- falling back in ``catch`` to direct assignment at level ``L`` and ``mdp.Q.F = sum(mdp.F)``.

**Python** mirrors this with ``_vb_hierarchical_update_parent_Q_from_child``.
For current partial outputs, ``Q`` may still be a plain list (not MATLAB-like struct); in that case we preserve
that list as-is. Where ``Q`` is struct-like, we apply append-first / assignment-fallback semantics.

## Entry 12 (DEM_AtariIII): authoritative full level-0 `F` parity gate

**Problem:** `F` is a **parity** target, not an optimization objective. Acceptance must not begin from a loose
`rtol`/`atol` policy that can hide translation bugs. Stochastic VB must be compared under **aligned** randomness
(the same protocol as `test_spm_MDP_VB_XXX_spm_sample.py` / `test_spm_MDP_generate.py`: replay MATLAB scalar
`rand()` into `numpy.random.rand`).

**Capture ordering (v5, preamble-true):** Parity must match MATLAB **from the first executable line of**
`spm_MDP_VB_XXX` **under the real call site** — i.e. whatever `rng` state exists **immediately after** the
capture preamble builds `rgms_rdp11` (no `rng(...)` inserted before VB). Flow: save `s_pre = rng`, run
`spm_MDP_VB_XXX(rgms_rdp11)`, then `rng(s_pre)` and `rand(K,1)` where `K` comes from a Python VB dry-run count on
the same pulled `rdp11`. That buffer is exactly the VB draw sequence under preamble continuation. Store
`entry12_vb_matlab_rand_buf` in the pickle; Python replays via `spm_MDP_VB_XXX_with_matlab_rand_buf`. **Do not** use
a VB-local arbitrary `rng` seed for this oracle — that misrepresents `DEM_AtariIII` / capture entry conditions.
(Superseded **v4** used a VB-local seed; invalidate old pickles.)

**Authoritative test:** `test_entry12_python_full_F_vector_parity_from_artifact` — strict **`numpy.array_equal`**
on mutually finite elements of the full raveled level-0 `F` vs `pdp12_F_mat`, after matching non-finite masks.
**No** `assert_allclose` acceptance path unless a **documented, proved** residual inequality exists (then record
the reason here and only then discuss thresholds).

**Structural lane:** `test_entry12_python_full_structural_checkpoint_from_artifact` uses the same replay buffer
when present so shapes/`X`/`P`/… align with the captured MATLAB trajectory.

**Diagnostics:** `_entry12_level0_F_diagnostics` augments failure messages (max/mean/p50/p90/p99 abs diff,
sign-mismatch count, sums).

**Degenerate `spm_sample` note:** MATLAB’s numeric branch can yield an **empty** `find(...,1)` when `P(end)==0`
after `cumsum`, corrupting `u` and later indexing. Python `_spm_sample` currently **repairs** some zero-mass
cases with a uniform fallback — that is **not** bitwise-faithful to MATLAB’s crash/empty behavior and can
desynchronise draws vs Engine if both paths are exercised; prefer fixing **inputs** (`GP.E`, `spm_norm`
outputs) so `pu` is valid, and keep draw replay as the parity mechanism.

## `spm_VBX`: `_spm_VBX_sparse` reduced prior shape

MATLAB **`R{f} = P{f}(s{f})`** keeps a **column** of selected masses. NumPy boolean indexing
**`Pf[mask]`** returns a **1-D** vector; leaving it 1-D made **`spm_cross`** / **`_spm_times`**
reshape it like **`(1, N)`**, broadcasting **`exp(L) * R`** to **`N×N`** instead of element-wise
**`(N,1)`** as in MATLAB **`spm_times`**. **Policy:** in **`_spm_VBX_sparse`**, set
**`R[f] = Pf[mask].reshape(-1, 1)`** so **`R{f}`** matches MATLAB’s column layout (fixes **`F`**
and **`P`** on the no-**`ff`** **`spm_VBX`** path and any caller, including **`spm_forwards`**).

## `spm_MDP_VB_XXX._vb_mdp_field_matrix`: ``nf×1`` hierarchical prep ``s`` / ``u``

**MATLAB (~707–721):** After hierarchical prep sets ``mdp.s`` / ``mdp.u`` as column vectors
(``mdp.s(f) = spm_sample(...)``), setup does ``k = zeros(NF,T); i = find(MDP.s); k(i) = MDP.s(i);``.
``find`` on an ``nf×1`` vector fills the **first column** of ``k`` (column-major linear indices).

**Python (2026-05-17):** Do **not** require ``s.size == NF*T`` before copying; if the raveled
field is shorter, use ``find`` semantics on the raveled vector and assign into
``zeros(NF,T)`` at matching linear indices (skip out-of-range). Discarding ``nf×1`` prep
caused nested child VB to re-``spm_sample`` ``s`` at ``t=1`` and broke Entry **12E**
``O{m,g,1}`` from child ``X{f}(:,1)`` for large factors (e.g. ``ns=41``).

## Entry 12 — `GP(m).A` frozen at init; workspace `A{m,g}` updates online

**MATLAB** (`spm_MDP_VB_XXX.m` ~368, ~964–967, ~1424): at setup, `GP(m).A = MDP(m).A` (or `GA` for process models). The loop updates workspace `A{m,g} = spm_norm(qa{m,g})` but does **not** write back into `GP(m).A{g}`. The `n(o,t)==0` outcome branch samples from **`GP(m).A{g}(:,ind{:})`** (initial likelihood shape / `No`).

**Python bug (fixed 2026-05-19):** `gpm["A"] = md["A"]` aliased the same list/objects as `md["A"]`, so active-learning updates shrank `GP` tensors (e.g. modalities **109–111** became **2×2** / **9×9**). That collapsed `O` / nested `Q.O` row stacks (**553** vs **555** rows) and triggered Validation **12** `Q.O` compare-lane overflow at **g=110**.

**Policy:** `copy.deepcopy` generative-process `GP(m).A/B/D/E/U` (and `GA/GB/GU`) at **12B** init; keep updating `bundle["A"]` / `md["A"]` for online `A{m,g}` only.

## Entry 12 — `MDP.Y{o,t}` first index is `Ng`, not `max(No)`

**MATLAB** (`spm_MDP_VB_XXX.m` ~1644–1659): posterior predictive `MDP(m).Y{o,t}` uses outcome modality index **`o`** from `spm_parents` (1..`Ng(m)`), same as `O{m,o,t}` indexing.

**Python bug (fixed 2026-05-19):** `_vb_posterior_predictive_Y` allocated `md["Y"]` with `max(No)` rows, producing 9×`T` cells instead of 111×`T` and Validation **12** compare-lane `Y` flatten **9 ≠ 222**.

**Policy:** size `Y` (and bounds on `o`) with **`Ng`**, not `max(No)`.

## Entry 12 — one solver, multi-tag regression (pointer)

**Authoritative policy:** **`Atari_example.md`** § **One solver, same `OPTIONS`, different `RDP` (all four VB calls — mandatory)** and § **Multi-tag regression gate**.

All four VB invocations in **`DEM_AtariIII.m`** use **`spm_MDP_VB_XXX(RDP, OPTIONS)`** with the **same** options profile; only **`RDP`** differs. A compute change that greens one **`tag`** but reds another captured tag is a **holistic failure** until all captured tags are restored. After every **`spm_MDP_VB_XXX.py`** edit: script **3 → 4** on **`rgms_canonical`**, **`rgms_atari_call2`**, and **`rgms_atari_call3`** (add **`rgms_atari_call4`** when captured; no new **1b** unless draw contract changes).

**Checkpoint vs done (2026-05-27):** Calls **1–3** can exit script **4** **0** without proving full **`DEM_AtariIII`**, call **4**, or all loop games — see **`Atari_example.md`** § **Multi-tag regression gate**. **Stale `1b`:** mixed capture causes false reds; fix with **`1a→1b→3→4`** on that tag. **1-D `GP.A`:** **`_vb_gp_A_outcome_column`** **`ndim==1`** path. **Call 3 `A_peaks_*`:** phase-log witness selection in **`entry12_matlab_capture.py`** (class **B**, not VB compute).

## Entry 12 — Validation 12 and compare-lane honesty (pointer)

**Authoritative policy:** **`Atari_example.md`** § **Entry 12 — Validation 12 and compare-lane honesty (mandatory)**. Validation **12** (script **4**) is the **full** Phase **1** sign-off oracle: causal **12D–12F** lean snaps (**15** steps, fix at **first** red), input **`RDP`**, subentries **12A–12I** (gating: **12A–12F**, **12H**, **12I**; **12G** excluded), and **final `PDP`** — one paired **1b/3** run. Compare lane (`entry12_matlab_capture.py`) may reshape for representation only — it must **not** substitute MATLAB values on layout failure (`Entry12CompareLaneError`).

## Entry 12 — Phase 1 oracle lane and Validation 12 lean boundaries

**XXX 12 default input (Phase 1):** `test_DEM_AtariIII_XXX_12.py` loads
`DEMAtariIII_fsl_1_11_rdp.mat` by default (same lane as MATLAB dump / VB monitor).
Use `RGMS_XXX_12_RDP_FROM_CTX=1` only for non-oracle ctx PKL smoke. Explicit
`RGMS_XXX_12_RDP_FROM_MAT=1` still forces the `.mat` lane.

**`spm_MDP_checkX(..., transform=False)` (Entry 12 provisional):** default unchanged. With
`transform=True` and `transform_reference` (raw ``.mat`` nested template), run checkX once
then align container types (e.g. ``csc_array`` on ``A{g}``, ``id.g`` as ``(1, ng)`` ``ndarray``).
**VB compute** uses ``entry12_rdp_for_vb_from_mat_nested`` (checkX only, no transform).
**Validation 12 input RDP** uses ``entry12_rdp_for_validation_from_mat_nested`` +
``entry12_align_py_rdp_to_validation_lane`` and reuses
``compare_nested_rdp_oracle_lane`` from ``fsl_1_11_compare_ctx_pkl_to_mat.py`` (same mat path:
``_fsl_1_11_mat_path`` / ``_load_matlab_nested_rdp_for_fsl_oracle``).

**`spm_MDP_checkX` — ``C{g}`` 1-D from ``loadmat(..., simplify_cells=True)`:** FSL oracle load
can yield ``C{g}`` shape ``(n,)`` instead of ``(n, 1)``; reshape to column before
``spm_dir_norm`` so normalization matches MATLAB column vectors.

**Authoritative sign-off contract:** **`Atari_example.md`** § **Phase 1 oracle RNG — mandatory policy** (four-script lane, forbidden draw hacks, Phase **0** gate). This file holds **`spm_sample`** mechanics only.

**VB RNG replay (Phase 1):** `spm_MDP_VB_XXX(..., reuse_matlab_draws=False)` (default)
uses native `numpy.random.rand` in file-local `_spm_sample`. With
`reuse_matlab_draws=True`, Python replays scalars from
`fixtures/DEMAtariIII_entry12_vb_matlab_rand_buf.mat` (env
`RGMS_ENTRY12_VB_MATLAB_RAND_MAT`), captured once by
`DEMAtariIII_entry12_dump_all_subentries.m` after
`python tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py` writes `K`.
XXX 12 oracle uses `monitoring=False`, `dump_subentries=True` to match the dump.
Opt out: `RGMS_XXX_12_NATIVE_RNG=1`. Native py vs native mat VB parity without
replay remains out of scope.

**Twister / seed vs replay (do not conflate):** Phase 1 oracle parity uses
**`vb_rand_buf` replay** — Python patches **`np.random.rand`** to return the next
MATLAB-captured scalar. That lane does **not** set a NumPy seed to “match” MATLAB
twister. For **native** `rand()` vs `rand(1,'twister')` in MATLAB, the same
non-zero seed can align only up to finite precision; **`randperm`** is a separate
stream contract (see RNG subsection above). **Do not** refresh `vb_rand_buf` / `K`
without draw-count or protocol justification.

**Entry 12F draw-index audit (2026-05-17):** Under replay (`K=27199`,
`entry12_v5_preamble_rewind`), Python consumes **exactly** `K` scalars;
`spm_sample` call count equals `K`; parent `t=1` `spm_forwards` uses **no**
additional `rand()` between entry and return (`draw_index` 424). Stochastic
divergence vs canonical MATLAB **`MDP.G`** (−32.4 vs −64.4) must occur **before**
that index (hierarchical / outcome / path sampling), not inside `spm_forwards`.
**Frozen cross-check:** On Python replay inputs (`entry12_12f_live_inputs.mat`),
MATLAB Engine reports **`ih≈32`**, **`spm_dot=0`**, same `R` support (231, 458
1-based) and **`Qf(R>0)=0`** as Python — so the **−32 `G` gap is not an
`spm_dot` implementation difference** on the replay belief; paired probe
MATLAB `spm_dot≈+32` used **native RNG**, a different trajectory. Snap `P`/`Q`
can match while stored `G` differs (uniform row shift; `Pu` softmax invariant).

**Validation 12 — MATLAB struct-row broadcast on lean 12D–12F snaps:** When MATLAB saves
`struct('t', t, 'O', Ot)` with `Ot` a non-scalar cell, `save -struct` can produce a
1×N struct row; `mat_nested_to_py` becomes a Python `list` of dicts. For **12E**,
Validation 12 reassembles `O` into `[row]` (one model row) before compare. For other
keys, take the first snap when the list is a broadcast artifact. **`matlab_release`**
on **12I** `spine` is environment metadata — stripped on both sides before compare.

**`spm_MDP_checkX` — scalar `MDP.B{f}` from `.mat`:** Hierarchical child MDPs from
`mat_nested_to_py` can leave `B{f}` as a Python `int` (MATLAB 1×1 scalar). Treat
`int` / `float` / 0-D numeric as `reshape(1, 1)` before `ns[f] = bf.shape[0]`.

## Entry 12 — `spm_MDP_checkX` and `id.g` covert partitions

**Policy:** MATLAB `id.g{i}` is one **covert partition** (a vector of modality indices for that partition). `numel(id.g)` is the number of partitions, not the number of modalities.

**Bug (fixed):** Normalizing `id.g` with `np.asarray(flat, dtype=object).ravel()` on a single cell holding `array(1, n)` produced shape `(1, 1, n)` and raveled into **n** scalar cells. That inflated `Ni` in `spm_forwards` to **n**, repeated the same `iH` risk term on every column, and made `sum(G, 2)` about **n×** too negative (12F `MDP.G` / `v` off by ~640 for Atari with one `(1,20)` partition).

**Fix:** `_id_g_cell_partitions` in `spm_MDP_checkX.py` iterates **cells** (partitions), not modality scalars inside one row.

## Entry 12 — `_spm_induction_vb` path column (`P(:,max(n-1,1))`)

**MATLAB:** After `[d,n] = max(G,[],1)` and `[n,i] = min(n)`, `n` is the **1-based row**
index of the maximum score in `G` (time / backwards column). The path mask is
`P = P{i}(:, max(n - 1, 1))` (1-based column into `P{i}`).

**Python:** `nmx = np.argmax(G, axis=0)` is **0-based**. The matching column index is
`col_idx = max(int(n_use) - 1, 0)`, **not** `max(n_use - 1, 1) - 1` (that applies an
extra `-1` and picked the wrong backwards column, yielding `R_sum=64` with two
nonzeros vs MATLAB `R_sum=32` with one).

**Frozen oracle:** `matlab_custom/entry12_12f_induction_compare.py` on captured
`B,H,Q,N,id` at parent `t=1,m=1`.

## Entry 12 — `.mat` capture oracles (canonical tag)

**Sources:** **`matlab_custom/saved_rdp_DEM_AtariIII.mat`** (`RDP`) and **`DEMAtariIII_entry12_<runTag>_12A.mat`** (`MDP` after MATLAB **`spm_MDP_checkX`**), produced by **`DEMAtariIII_entry12_dump_all_subentries.m`**.

**Python:** Tests convert **`loadmat`** payloads with **`tests/oracle/toolbox/DEM/entry12_loadmat_convert.py`** (`mat_nested_to_py`) before **`spm_MDP_checkX`** / compares. Parity vs **`_12A.mat`** uses **`_assert_nested_rdp_equal`** from **`test_spm_mdp2rdp`** (same nested-float tolerance policy).

**Run-tag alignment:** Python constant **`ENTRY12_CANONICAL_RUN_TAG`** (default **`rgms_canonical`**, env **`RGMS_ENTRY12_CANONICAL_RUN_TAG`**) should match **`RGMS_ENTRY12_CAPTURE_RUN_TAG`** used in MATLAB when generating files, or set **`RGMS_ENTRY12_CAPTURE_RUN_TAG`** in the pytest environment to match whatever tag was used (e.g. **`default`**).

## Entry 12 — saved-structure compare contract (Validation 12 causal gate)

**Policy:** Paired **1b** / **3** compares must use **symmetric** canonicalization — not “reshape Python to mat list length” per tee line. One documented rule per MATLAB storage class; apply the **same** transform to py and mat before `_assert_nested_rdp_equal`.

**`ss.{D,E,ID,IE}` (checkX / structure-learning on nested MDP):** MATLAB saves each block as **`cell(4,4)`** (``loadmat`` → ``4×4`` object array). Script **3** pickle stores a **flat length-16** list in **row-major** order (**`k = i*4 + j`**); paired compare must flatten``.mat`` nested **`[i][j]`** the same way (not MATLAB ``(:)`` column-major unless Python compute is changed to match). Validation **12** calls **`entry12_canonicalize_saved_structures_for_compare`** on **both** aligned py and mat snapshots before causal asserts.

**`mdp.Q.{Y,j,i,o}{L}` append row:** Python must flatten child ``Ng×T`` nested grids with MATLAB ``(:)`` index **`o + t*Ng`** (loop **`t` then `o`** in ``_vb_hierarchical_q_ot_grid_to_cell_row``). Wrong order **`o*T+t`** permutes cells vs live ``mdp.Y{o,t}`` while live ``Y`` can still match. Compare: ``_entry12_canonicalize_Q_ot_grid_levels`` on paired snaps.

**Nested `mdp.O` / `MDP.MDP.O` (post-``shiftdim`` vs ``.mat`` load):** After child VB, MATLAB ``shiftdim(O,1)`` yields **`O{t,g}`** (**T×Ng**); Python mirrors as **`O[t][g]`** in script **3** dumps. Paired **1b** ``loadmat`` still exposes workspace-style **`cell(Ng,T)`** as **`O[g][t]`** (e.g. **111×2** object array → length-**111** list of length-**2** rows). Same **222** outcome cells; transposed nesting only. Compare lane: **`entry12_canonicalize_saved_structures_for_compare`** maps both sides to **`O[g][t]`** via **`_entry12_canonicalize_O_nested_block`** (not a VB change). Flat **`Q.O{L}`** rows still use **`_entry12_q_o_flat_index_t_shiftdim`** (**`t + g*T`**) when folding matrix ↔ flat cells — separate surface from full nested **`MDP.MDP.O`**.

**`mdp.Q.O{L}` (2026-05-25, class A):** MATLAB ``[mdp.Q.O{L} mdp.O]`` (~1238) appends on **`cell(Ng,T)`** with **variable ``No(g)``** per row (ragged vectors), not a single dense ``(sum(No),T)`` matrix. Paired **``.mat``** often shows **`len(mdp.Q.O)==Ng`** (one row per modality). Python must use **`_vb_hierarchical_O_field_to_ng_t_rows``** + **`_vb_hierarchical_q_O_ng_t_hstack``**; detect **Ng×T** before **T×Ng** when dimensions are ambiguous. Compare: **`_entry12_align_q_o_ng_t_rows`**.

**`mdp.Q.o{L}` (2026-05-25):** ``mdp.o`` is an **`Ng×T`** **scalar** matrix (~725 / assemble). ``[mdp.Q.o{L} mdp.o]`` matches **`s``/``u``** — **`np.hstack``** on the matrix, **not** ``_vb_hierarchical_field_to_ot_nested`` (that helper is for **`Y``/``j``/``i``** nested cells only). Routing ``o`` with ``Y`` left **`Q.o``** empty on PDP while live ``mdp.o`` was fine.

**`entry12_Yfill`:** MATLAB **`cell(Ng,T)`** (e.g. **111×2**). Preserve as nested **`[g][t]`** in **`mat_nested_to_py`** (do not flatten to **`Ng×T`**). Distinct from **`4×4`** **`ss`** blocks — shape heuristics must not treat all 2D object arrays alike.

## Entry 12 — `spm_dot(B, P)` path axis when `Nu>1`

**MATLAB:** For vector `P` with `numel(P)` matching multiple `size(B)` entries, `spm_dot(B,P)` wraps `P` as a **cell** `{P}` so contraction uses the **last** matching dimension (path / `Nu` axis), not the first (state / `Ns`).

**Python:** `spm_dot(B, P)` with a plain 1-D array can contract the **state** axis when `ns == nu` (e.g. Atari `10×10` `B` and length-10 `P`), corrupting `Q{m,f,t} = spm_dot(B,P)*Q` and leaving diffuse path posteriors after hierarchical child VB.

**Fix:** Use **`spm_dot(B, [P])`** (cell/list-of-one-vector form) anywhere MATLAB passes a path belief vector into `spm_dot` for forwards / `prior_QP` / uncontrollable `BP`/`IP` fills. Frozen on Entry 12: child `P{2}(:,end)` one-hot at `out_t2`, causal **`12E.out_t2.O[3]`**, **`MDP.F`**.

## Entry 12 — workspace ``A{m,g}`` peak index (`A_peaks_*`)

**MATLAB:** ``entry12_vec_peak_`` uses ``v(:)`` (column-major linearization) then ``max(v)`` (1-based index).

**Python:** ``_entry12_vec_peak`` in ``spm_MDP_VB_XXX.py`` must use ``np.asarray(...).ravel(order='F')`` before ``argmax``, not default C-order ``ravel()``. On 2D workspace ``A`` (e.g. ``(41,485)``), C-order peak indices disagree with MATLAB while F-order peaks match paired phase logs. Compare-lane ``_entry12_normalize_a_peaks_list`` must use the same rule when re-``argmax``ing array payloads.

## FSL 1–11 — MATLAB capture vs stock `dump_rdp_DEM_AtariIII.m`

**Policy:** **`matlab_custom/dump_rdp_DEM_AtariIII_FSL_1_11.m`** stages the same **Entry 11 assemble-RGM fence** as **`DEM_AtariIII.m`**: ``RDP = spm_set_goals(MDP,[2,3],[C,-C]);`` then ``spm_set_costs`` → ``spm_mdp2rdp`` → ``RDP.T = 64`` (MATLAB names the MDP-cell output ``RDP`` after the first call even before conversion). Python **`run_dem_atariiii(entry_stop=11)`** must mirror that **four-line** order (Entry **10** still has its own ``spm_set_goals`` for ``P``). The FSL script differs from **`dump_rdp_DEM_AtariIII.m`** only where the **Python driver** differs from that legacy dump: **``GDP.tau = 1``**, **128** basin outers (not **256**), and **one** ``spm_RDP_sort`` (not four). It does **not** omit **`spm_set_goals`** in Entry **11**. Regenerate the **``.mat``** fixture after any FSL-relevant change.
