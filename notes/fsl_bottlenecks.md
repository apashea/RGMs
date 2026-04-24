# FSL structure-learning bottlenecks: working notes (final-to-first strategy)

This document consolidates **crucial** planning and validation context for
`spm_faster_structure_learning` parity work (snippet / “FSL” harness), including
**Lane D final-output validation**, **default file boundaries**, **known
`spm_dir_MI` / link-stage facts**, and **recommended next steps** when approaching
the problem from **last bottleneck toward first**. It is intended to stay in
sync with `logs\log_0.md` and `notes\structure_learning_plan_week2_22APR2026.md`;
this file is the **single** additional note created for correspondence consistency.

---

## A. Strategic rationale: final-to-first bottleneck direction (authoritative intent)

### A.0 Verbatim source text (copy-paste from project correspondence)

> While I understand the idea of starting with the first mismatch, I think we
> should begin with the LAST mismatch given that our lane design allows us to
> isolate the problem thus the earliest mismatches do not prevent us from
> tasting the later mismatches; I am choosing beginning with the LAST mistatch in
> the pipeline because there are NO GUARANTEES that we will be able to achieve
> perfect equivalence between Python and MATLAB for ANY of these bottlenecks,
> whereby AS A LAST RESORT we would need to pick a tolerance policy for
> redefining what 'reproduction' means, and with such a tolerance policy in place
> we might end up with slight differences later in the pipeline; if we work
> backwards, we'll be able to cover everything without needing to experiment back
> and forth with flags due to earliest inputs changing later results.
>
> WITH THIS CRUIAL NOTE THAT WE WILL APPROACH THIS FROM THE
> FINAL-to-FIRST-BOTTLENECK DIRECTION in mind: it is almost CERTAIN that we will
> need to be very THOROUGH, COHERENT, and WELL-DOCUMENTED in a FORWARD-THINKING
> MANNER in our planning to ensure that 1) we never create additional files (code
> nor documents) unless FULLY NECESSARY, 2) we are AWARE of the files we're
> working with, 3) doing our testing and modifications in the CORRECT LANE, and 4)
> we undertake any PREREQUISITE STEPS before starting. Therefore state in
> advance:
>
> 1. For Lane D (which uses all of the MATLAB bridges for all three
>    spm_MDP_MI/spm_rgm_group/spm_dir_MI bottlenecks), how is the FINAL OUTPUT of
>    the overall pipeline VALIDATED? (i.e. validating the final outputs of
>    spm_faster_structure_learning in Python against the MATLAB outputs). This is
>    crucial, as if this is not being done properly, then we of course will end
>    up either endlessly debugging because a genuine translation won't match
>    corrupted testing outputs or corrupted validation test design.
>
> 2. which subset of files will we be working with? we MUST NOT go beyond this
>    set of files in our edits (unless it becomes NECESSARY, or if it would be
>    lead to a CLEAR EXPEDIENT BENEFIT WITHOUT RISKING CONTEXT LOSS AND
>    DISORGANIZATION)
>
> 3. what do we already know about this problem? We already tried to debug this
>    spm_dir_MI (see log_0.md for older references, likely the oldest references,
>    to spm_dir_MI), and must continue to track our progress and attempts at
>    solutions and seeking further information when necessary to prevent repetitie
>    forgetful circular debugging.

### A.1 Same intent in structured prose (no information loss)

While the idea of starting with the **first** mismatch is common, this project
instead chooses to begin with the **LAST** mismatch in the pipeline where lane
design allows isolation: **earliest mismatches do not prevent observing or
fixing later mismatches** when bridges and lanes are used deliberately.

The project lead chooses to begin with the **LAST** mismatch because:

- There are **NO GUARANTEES** that perfect numerical equivalence between Python
  and MATLAB will be achievable for **ANY** of the tracked bottlenecks.
- As a **LAST RESORT**, the team may need a **tolerance policy** that redefines
  what “reproduction” means for some quantities.
- With such a tolerance policy, **slight differences can propagate** and appear
  **later** in the pipeline.
- If work proceeds **backwards** (from the final bottleneck toward earlier
  ones), the team can **cover the full chain** without endless **back-and-forth
  flag experimentation** driven by early-stage changes continuously **changing
  downstream results**.

**Crucial operating note:** work will proceed from **FINAL → FIRST** bottleneck
order. That makes it **almost certain** that execution must be **thorough**,
**coherent**, and **well-documented** in a **forward-thinking** way, with these
constraints:

1. **Do not create additional files** (code nor documents) unless **fully
   necessary**. This `notes\fsl_bottlenecks.md` is the **only** additional file
   agreed for this correspondence thread; otherwise extend existing logs and
   plan notes.
2. Stay **aware of exactly which files** are in scope for each change set.
3. Perform testing and edits in the **correct lane** (A/B/C/D/E semantics as
   documented in the week-2 plan).
4. Complete **prerequisite steps** before starting implementation (oracle
   contract, fixtures, lane choice, checkpoint validity).

The sections below record the answers that were agreed as **foundational** for
that strategy (items 1–3 from the verbatim block are answered in sections B–D;
“most coherent next steps” are section F).

---

## B. Question 1 — Lane D: how is the **final** output of the overall pipeline
validated? (Python `spm_faster_structure_learning` vs MATLAB)

This matters because if final validation or reference construction is wrong, the
team risks **endless debugging** of a good translation against **corrupted
references** or **corrupted test design**.

### B.1 Reference side (MATLAB): no Python “bridges”

In the exhaustive oracle test
`tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py`, function
`test_spm_faster_structure_learning_snippet_scale_T1000_exhaustive_exact_oracle`,
MATLAB builds a workspace variable:

```text
MDP_fsl_snip_exact = spm_faster_structure_learning(O_fsl_sx, S_fsl_sx, sc);
```

There are **no** Python-side Lane D bridge hooks on the MATLAB execution path:
MATLAB runs **stock** `spm_faster_structure_learning` from the MATLAB Engine
session. The Python environment variables
`RGMS_FSL_RGM_MATLAB_MI_PUSH`, `RGMS_FSL_RGM_MATLAB_EIG`,
`RGMS_FSL_LINK_DIR_MI_MATLAB` only affect **how Python** calls
`spm_faster_structure_learning` (callbacks into MATLAB for isolated numerics);
they do **not** change how MATLAB computes `MDP_fsl_snip_exact`.

### B.2 Candidate side (Python): Lane D wires three MATLAB numerics hooks

Python runs:

```text
mdp_p = spm_faster_structure_learning(
    o_sl,
    s_mat,
    sc,
    rgm_eig_pair=rgm_eig_pair,           # when RGMS_FSL_RGM_MATLAB_EIG=1
    rgm_mi_override_fn=rgm_mi_override_fn,  # when RGMS_FSL_RGM_MATLAB_MI_PUSH=1
    link_dir_mi_fn=link_dir_mi_fn,       # when RGMS_FSL_LINK_DIR_MI_MATLAB=1
)
```

The test’s docstring (same file) documents the bridge semantics:

- **`RGMS_FSL_RGM_MATLAB_EIG=1`** — pass MATLAB `eig(...,'nobalance')` into
  `spm_faster_structure_learning` only (`rgm_eig_pair`). Step-6
  `_assert_rgm_group_streams_exact` still uses MATLAB MI + eig for slice-indexed
  `O` when this flag is set.
- **`RGMS_FSL_RGM_MATLAB_MI_PUSH=1`** — pass `rgm_mi_override_fn` so every
  `spm_rgm_group` rebuilds MI in MATLAB from the current Python `o_sub` (many
  Engine round-trips; slow). With `RGMS_FSL_RGM_MATLAB_EIG=0` this is Lane B
  (MATLAB MI + Python eig); with `RGMS_FSL_RGM_MATLAB_EIG=1` this is Lane C
  (MATLAB MI + MATLAB eig).
- **`RGMS_FSL_LINK_DIR_MI_MATLAB=1`** — optional `link_dir_mi_fn` so stream-link
  stored MI matches MATLAB `spm_dir_MI` on each pulled `a` (many Engine calls
  inside `_link_streams`). Use when isolating `ss.ID` / `IE` parity; combine with
  `RGMS_FSL_RGM_MATLAB_*` when validating end-to-end.

**Lane D** means all three flags are on so **MI assembly (grouping), eig
ordering injection, and link-time `spm_dir_MI`** are MATLAB-sourced at the
Python call sites the harness defines.

### B.3 Final gate: what “validated” means for the nested `MDP` tree

After Python returns `mdp_p`, the test calls:

```text
_assert_mdp_tree_exhaustive_exact(eng, mdp_m_name, mdp_p, n_stream=4)
```

with `mdp_m_name = "MDP_fsl_snip_exact"` (same string as the MATLAB reference
variable name).

`_assert_mdp_tree_exhaustive_exact` (same test module) does the following at a
high level:

- Asserts the **same number of MDP levels** (`numel(MDP)` vs `len(mdp_py)`).
- For **each** level:
  - **`fieldnames` parity** between MATLAB and Python structs.
  - For every compared numeric payload it calls **`_assert_exact_canon`**, which
    canonicalizes `float64` arrays (including NaN payload normalization where
    applicable), uses **Fortran-order** layout, and compares **`tobytes`**
    (**canonical byte equality**), **not** `numpy.allclose`.

Compared content includes, per level:

- All **`a{gi}`** sparse/dense matrices (via `full(...)` on MATLAB side).
- All **`b{fi}`** matrices.
- Scalar **`T`**.
- **`sA`, `sB`, `sC`** (vector slices per harness logic).
- **`id.A`, `id.D`, `id.E`** cell arrays converted for comparison.
- Per-stream **`G{s}{gi}`** index/grouping matrices (raveled for row/column
  layout conventions).
- **`ss.D`, `ss.E`, `ss.ID`, `ss.IE`** via **`_assert_ss_exact`**, which walks
  stream pairs, compares key sets for maps, uses integer equality for `D`/`E`
  entries, and uses **`_assert_exact_canon`** for **`ID`/`IE` float scalars**
  (this is where **`MDP{1}.ss.ID{1,2}(1,58)`** class failures surface).

Therefore, in Lane D, **“final pipeline output validated”** means:

> **The full nested Python `MDP` list-of-dicts tree is asserted to be
> byte-identical (under `_assert_exact_canon`) to MATLAB’s `MDP_fsl_snip_exact`
> for every field and index that this exhaustive helper traverses, with Python
> optionally using MATLAB numerics at the three bridge hooks.**

### B.4 Harness assumptions and risks (avoid chasing ghosts)

**Checkpoint path (`RGMS_FSL_USE_CHECKPOINT=1` without refresh):**

- MATLAB: `load(..., 'O_fsl_sx', 'S_fsl_sx')` then MATLAB FSL as above.
- Python: `o_sl` loaded from pickle
  `tests/oracle/toolbox/DEM/_checkpoint_data/fsl_snippet_t1000_o_sl.pkl`.
- The **logical** validity of the comparison assumes the pickle and `.mat`
  artifacts still describe the **same** fixed input window (they are written
  together when the checkpoint save path runs).
- On **checkpoint-only** runs, the test **does not** re-run
  `_assert_pdp_o_window_matches` against freshly generated `PDP_sx`; that gate
  runs on the **non-checkpoint** branch after Python `spm_MDP_generate` with
  replay-patched `numpy.random.rand`. If checkpoints are ever **manually**
  desynchronized or corrupted, tree compares become meaningless until
  checkpoints are rebuilt.

**Pre–full-tree checks (same exhaustive test, before Python SL):**

- The test calls **`_assert_rgm_group_streams_exact`** with the **same**
  `rgm_eig_pair` / `rgm_mi_override_fn` as the subsequent Python SL call.
- So Lane D is **not** “only a blind end-tree compare”: it also enforces
  stream-wise Step-6 checkpoints consistent with the bridge configuration,
  unless someone changes that ordering in the test.

**What Lane D proves vs does not prove:**

- **Proves:** With MATLAB numerics injected at the **three** instrumented hooks,
  **the remainder of the Python translation and data plumbing** (as exercised by
  this harness) produces a tree that is **byte-identical** to MATLAB’s reference
  tree for the **fixed checkpointed inputs**.
- **Does not prove:** Native Python parity at `spm_MDP_MI`, SciPy/MATLAB eig, or
  native `spm_dir_MI` without bridges.
- **Does support:** Confidence that the **MATLAB reference tree** and the
  **exhaustive compare machinery** are **internally consistent** for that fixed
  artifact when bridges align numerics.

**Independent sanity check (outside automated test):** if doubt ever arises about
the reference, run MATLAB `spm_faster_structure_learning(O_fsl_sx, S_fsl_sx, sc)`
on the **same** workspace objects and spot-check cells—but **within this repo**
the authoritative automated definition of “match” for this gate is the test
above.

---

## C. Question 2 — Default file subset (edits must not wander beyond this set
without necessity or clear expedient benefit)

Treat this table as the **default edit boundary** for a **last-bottleneck-first**
campaign focused on **`spm_dir_MI` / link storage** (`ss.ID` / `ss.IE`). Expand
only with an **explicit** reason (e.g. a shared helper is genuinely shared across
call sites and must change in one place).

| Role | Path |
|------|------|
| Link-time MI storage and stream linking | `python_src/toolbox/DEM/spm_faster_structure_learning.py` (`_link_streams`, `_stream_link_mi`, and strictly local helpers already in that module if needed) |
| Scalar Dirichlet MI kernel | `python_src/spm_dir_MI.py` |
| Shared log / entropy helpers used by MI | `python_src/spm_log.py` — **only** if the fix is truly in the shared `spm_log` contract, not opportunistic refactors |
| Oracle tests and harness diagnostics | `tests/oracle/test_spm_dir_MI.py`, `tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py` — **narrow** edits: targeted asserts or **optional** diagnostics behind env flags; prefer extending **existing** hooks such as `[SS-LINK-DIAG]` rather than inventing new scattered print paths |
| Chronology and consolidated plan | `logs\log_0.md`, `notes\structure_learning_plan_week2_22APR2026.md` |
| Corner-case / policy memory (project rules) | `notes\andrew Python Matlab Translation Issues.md` — when locking a **tolerance policy** or a **MATLAB-defined semantic** ambiguity, per project workflow |

**Explicitly out of default scope for “link MI only” work:**

- `python_src/toolbox/DEM/spm_rgm_group.py`
- `python_src/spm_MDP_MI.py`

Touch those only when the backward plan explicitly moves upstream, or when a
link-stage policy change **forces** a regression pass that cannot be isolated
elsewhere.

**No new files** unless unavoidable (e.g. a third duplicate of the same helper
would be worse than a well-motivated addition). The user’s constraint for this
thread: **this** `notes\fsl_bottlenecks.md` is the **only** additional document
created for correspondence consistency; other new files still require strong
justification.

---

## D. Question 3 — What we already know (anti–circular-debugging record,
especially `spm_dir_MI`)

### D.1 Lane C / `[SS-LINK-DIAG]` facts (canonical, exhaustive scope)

When **`RGMS_FSL_RGM_MATLAB_MI_PUSH=1`** and **`RGMS_FSL_RGM_MATLAB_EIG=1`** are
active but **link-time** `spm_dir_MI` remains **native Python** (no
`RGMS_FSL_LINK_DIR_MI_MATLAB`), the **first** exhaustive failure is at:

```text
MDP{1}.ss.ID{1,2}(1, 58): canonical byte mismatch
```

Diagnostic evidence (from harness `[SS-LINK-DIAG]` and plan/log narrative):

- The **linked Dirichlet matrix** in the diagnostic narrative:
  **`MDP{2}.a{21}`** — **byte match** between MATLAB and Python (`linked a bytes
  match: True` in diagnostics).
- The **stored scalar** at link time still diverges:
  - MATLAB **`spm_dir_MI`** on that matrix: about **`8.8817841970012523e-16`**
  - Python stored value: **`0.0`**
- Interpretation class: **near-cancellation / signed-zero / branch ordering** in
  the Dirichlet MI / entropy chain — **not** “wrong matrix shape” or gross matrix
  mismatch.

### D.2 Harness strictness vs tolerance helpers

- The exhaustive tree gate uses **`_assert_exact_canon`** (hard **byte**
  equality) for `ss.ID` / `ss.IE` floats where applied.
- The same test module defines **`_assert_repro_close_f64`** for **tolerant**
  `float64` comparisons (`allclose`-style with explicit `atol`/`rtol`), but the
  **exhaustive nested-tree gate does not substitute that** for `ss.ID` / `IE` in
  the byte-exact path documented above.

### D.3 Lane E / logs: related but distinct warnings

Older `logs\log_0.md` entries and Lane E runs show **`spm_dir_MI`** /
**`spm_log`** can emit **`RuntimeWarning`** (divide by zero in log, invalid value
in divide) under edge mass patterns in **`test_spm_faster_structure_learning_checkpoint_rgm_streams_matlab_eig_parity`**. That is **related context** for
numerical hygiene but is **not the same evidence** as the Lane C **`(1,58)`**
canonical-byte mismatch on the exhaustive selector.

### D.4 Anti-forgetfulness discipline

- Append each experiment to **`logs\log_0.md`** (chronological).
- Fold stable conclusions into **`notes\structure_learning_plan_week2_22APR2026.md`**
  (team-readable consolidated state), including a short **hypothesis → result →
  next** block for `spm_dir_MI` when iterating.
- Escalate to **`notes\andrew Python Matlab Translation Issues.md`** when a
  **policy** is locked (for example accepting `allclose` at link storage with a
  documented `atol`) or when MATLAB semantics are genuinely ambiguous.

---

## E. Lane map (minimal reminder for “correct lane” work)

Definitions align with `notes\structure_learning_plan_week2_22APR2026.md`:

- **Lane A:** exhaustive selector; native MI, native eig, native link
  `spm_dir_MI` (no three MATLAB bridges).
- **Lane B:** exhaustive; **`RGMS_FSL_RGM_MATLAB_MI_PUSH=1`**; native eig; native
  link `spm_dir_MI`.
- **Lane C:** exhaustive; **`RGMS_FSL_RGM_MATLAB_MI_PUSH=1`** and
  **`RGMS_FSL_RGM_MATLAB_EIG=1`**; native link `spm_dir_MI` — **primary native
  isolation lane for link-time `spm_dir_MI`** once grouping is bridged.
- **Lane D:** exhaustive; all three flags including
  **`RGMS_FSL_LINK_DIR_MI_MATLAB=1`** — **bridge sanity**: full tree byte pass
  when MATLAB numerics are injected at all three hooks (often with checkpoint for
  runtime).
- **Lane E:** **non-exhaustive** subset in the same test file via
  `-k "not exhaustive_exact_oracle"` — regression hygiene **only**; cannot
  replace exhaustive bottleneck classification.

Exhaustive selector (for A–D scope statements):

```text
tests/oracle/toolbox/DEM/test_spm_faster_structure_learning.py::test_spm_faster_structure_learning_snippet_scale_T1000_exhaustive_exact_oracle
```

---

## F. Best next steps (aligned with final → first, planning-forward)

1. **Freeze the oracle contract (one sentence the team signs):**  
   The exhaustive gate means **byte-identical nested `MDP`** vs MATLAB
   **`MDP_fsl_snip_exact`** on **checkpointed** `(O_fsl_sx, S_fsl_sx)` / `o_sl`
   for the fields the helper traverses. Any future **tolerance policy** is a
   **second contract** (separate assertion path or gated mode), **not** a silent
   replacement of `_assert_exact_canon` semantics without team agreement.

2. **Work in the correct lane:**

   - **Isolate link MI:** **Lane C** (MI + eig bridged, **link native**) already
     pins first native failure to **`ss.ID` / `spm_dir_MI`** storage.
   - **Confirm end-to-end with bridges:** **Lane D** (full tree pass sanity).
   - **Do not** use **Lane E alone** to justify native exhaustive parity.

3. **Prerequisites before code changes:**

   - Re-read **`spm_dir_MI.py`** and the **exact** call path in **`_stream_link_mi`**
     (dtypes, copies, normalization, sparse vs dense).
   - Capture **one** minimal numeric fixture: the `a_mat` (or harness-equivalent)
     at stream link `(1,2)` key `(1,58)` and both scalars — partially done today
     via **`[SS-LINK-DIAG]`**.
   - Decide **in advance** whether this stage’s goal is:
     - **(A)** byte-match MATLAB on that path, or
     - **(B)** match MATLAB only after a **documented** rounding rule, or
     - **(C)** match a **derived** reference (explicit “Python canonical” policy).  
     Tolerance thinking belongs here as an **explicit branch**, not a late
     surprise retrofitted into byte tests.

4. **Implementation order (backward strategy, forward execution):**

   - First: **`spm_dir_MI.py`** to match MATLAB’s scalar on the **fixed**
     fixture **without** changing upstream grouping (Lanes A/B behavior unchanged
     for their native failure modes).
   - Then: **`_link_streams` / `_stream_link_mi`** only if evidence says the bug
     is wiring, dtype, or caching — not speculative duplication of MI math.
   - Extend **`tests/oracle/test_spm_dir_MI.py`** with a **small permanent**
     regression case derived from the Lane C matrix/scalar situation.
   - Only after Lane C’s first failure **moves upstream** or disappears: touch
     **`spm_rgm_group.py` / `spm_MDP_MI.py`**.

5. **Guard against flag ping-pong:**

   Fixing **link** first avoids reshaping the full tree before measuring **link**
   behavior. **Checkpointed `o_sl`** is fixed for a given artifact pair; upstream
   code changes **should not** alter inputs to link unless checkpoints are
   **regenerated** or **pre-SL** code changes — **document** whenever checkpoints
   are invalidated.

---

## G. Bottom line (single paragraph)

**Lane D** final validation is **rigorous nested `MDP` canonical-byte equality**
against **`MDP_fsl_snip_exact`** computed by **pure MATLAB**
`spm_faster_structure_learning`, while **Python** may use **three** MATLAB
numerics hooks at well-defined call sites; the main intellectual risks are
**checkpoint / `o_sl` ↔ `O_fsl_sx` alignment** and treating **byte** identity as
the sole definition of “reproduction” until a **second**, explicitly named
**tolerance contract** exists. Working **last-bottleneck-first** remains coherent
if **Lane C** is treated as the primary **native** isolation lane for
**link-time `spm_dir_MI`**, **Lane D** as **bridge sanity**, and any tolerance
shift is **documented policy**, not an unreviewed tweak inside
`_assert_exact_canon`.

---

## H. File path index (absolute, for Windows workspace copy-paste)

- Harness / exhaustive + Step-6 helpers:  
  `C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\test_spm_faster_structure_learning.py`
- Checkpoint artifacts directory:  
  `C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\_checkpoint_data\`
- Learner:  
  `C:\Users\andre\.cursor\RGMs\python_src\toolbox\DEM\spm_faster_structure_learning.py`
- Dirichlet MI:  
  `C:\Users\andre\.cursor\RGMs\python_src\spm_dir_MI.py`
- Log helper:  
  `C:\Users\andre\.cursor\RGMs\python_src\spm_log.py`
- Oracle for `spm_dir_MI`:  
  `C:\Users\andre\.cursor\RGMs\tests\oracle\test_spm_dir_MI.py`
- Run chronology:  
  `C:\Users\andre\.cursor\RGMs\logs\log_0.md`
- Consolidated week-2 plan:  
  `C:\Users\andre\.cursor\RGMs\notes\structure_learning_plan_week2_22APR2026.md`
- This note:  
  `C:\Users\andre\.cursor\RGMs\notes\fsl_bottlenecks.md`

---

*End of document — content is intentionally complete and non-truncated relative to
the correspondence it consolidates.*
