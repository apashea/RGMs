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
