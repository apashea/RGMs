# Agent–user communication directives (RGMs)

**Status:** Working notes from a failed exchange (2026-05). Treat as guidance for assistants on this repo unless superseded by explicit user instruction.

## What went wrong (brief)

- Replies led with **jargon** (“opt-in”, “truthy”) and **identifiers** before stating **what actually runs** and **what changes in the world** (CPU time, assertions, skips).
- Two different shell invocations (pytest with vs without env) were described **without** labeling them as two separate commands, which read as a **contradiction**.
- A **time limit** was described as if it capped wall time globally; the implementation only runs at **explicit check sites**, so behavior did not match the user’s mental model. That gap should have been stated **first**, not implied.
- Tone drifted toward **patronizing enumeration** (lists of strings as if that were the whole answer) instead of **engineer-to-engineer**: mechanism → effect → how to verify.

## Directives for future turns

1. **Effect before mechanism.** For env flags: first sentence = what **runs or does not run**, what **assertions** fire, and **order-of-magnitude cost** if known. Second = how (variable name, file). Not the reverse.

2. **No vague gate words without a binding.** Words like “opt-in”, “truthy”, “enabled” must be immediately tied to: (a) exact accepted string values if relevant, (b) the **one** behavioral sentence (e.g. “pytest executes the test body” vs “pytest records SKIPPED and returns in ~seconds”).

3. **Multiple commands → explicit labels.** If comparing runs, use “Run A: …” / “Run B: …” and never reuse “we” without a referent.

4. **Limits and guarantees:** When describing timeouts, sampling, or ceilings, state **where** enforcement happens (which function / between which calls). If a long library call has **no** internal checks, say so plainly (“elapsed time can exceed N minutes while inside `spm_MDP_generate`”).

5. **Frustration:** Respond with **tighter technical content**, not longer apologies. Acknowledge confusion once, then fix the content.

6. **Uncertainty:** If behavior is inferred from code rather than observed at runtime, say **“From reading the code, …”** and cite the controlling branch.

## FSL ledger tests — factual summary (for reuse)

**`RGMS_ATARI_RUN_FULL_STAGED_LEDGER_1_11` set to `1`, `true`, `yes`, or `on` (case-insensitive after strip):**

- Pytest **executes** `test_full_staged_atari_ledger_1_through_11_pre_entry12` (it is not skipped by that test’s `skipif`).
- That test calls `run_dem_atariiii(entry_stop=11)` with **outer=128** and **training horizon 10000** (via env forced in `_run_fsl_entry11_context`), then checks **Python-side** outputs (GDP/RDP scales, `RDP["T"]` 64, `P` shape, etc.). On **success** it **always** writes **`ctx`** to the default PKL path (optional override: `RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH`). MATLAB nested **`RDP`** vs the FSL **`.mat`** is **not** in this pytest file — run **`python tests/oracle/toolbox/DEM/fsl_1_11_compare_ctx_pkl_to_mat.py`** afterward.

**Unset or any other value:** that structural test is **skipped**; pytest does not call `run_dem_atariiii` for it.

**Deadline:** set **`RGMS_ATARI_RUN_DEADLINE_MINUTES`** only (or optional explicit **`RGMS_ATARI_RUN_DEADLINE_MONO`**); the driver seeds **`perf_counter`** from minutes on first check. Enforcement remains at `_rgms_run_deadline_check()` call sites in `run_dem_atariiii`, so long single calls can still exceed wall patience between checks.
