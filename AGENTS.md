# AGENTS.md

## Environment

Use the `rgms` conda environment for all Python work in this repository.

Before running Python scripts or tests, activate:

`conda activate rgms`

Do not use another Python environment unless explicitly told to do so.

---

## Purpose

This repository is for **faithful MATLAB-to-Python translation with oracle testing**.

The goal is:

- translate selected MATLAB files into Python
- keep the Python as close to the MATLAB as possible
- verify Python against the original MATLAB using oracle tests
- build the codebase gradually in dependency order
- minimize edits to shared files

Do **not** optimize, redesign, refactor for style, or add speculative abstractions.

---

## Core rules

1. **MATLAB is the source of truth.**
2. **Do not add code that is not strictly needed for faithful translation or testing.**
3. **Minimize edits to shared files.**
4. **Each translated Python file must have an oracle test.**
5. **Read `Python Matlab Translation Issues.md` before translating or changing tests.**

If a new MATLAB/Python corner case appears, ask the user before choosing a
policy. After the decision is settled, record it in
`Python Matlab Translation Issues.md` so future translations handle it
consistently.

---

## Workspace model

Each person works on one MATLAB file at a time.

Default flow for one file:

1. copy the target MATLAB file into `matlab_src/`
2. translate it into `python_src/`
3. create its oracle test in `tests/oracle/`
4. run the oracle test
5. only touch shared test helpers if strictly necessary

Default outputs for one file:

- `matlab_src/<name>.m`
- `python_src/<name>.py`
- `tests/oracle/test_<name>.py`

---

## Shared-file minimization

To reduce git conflicts:

- do not create shared runtime translation helper modules except the approved
  repo-root `matlab_compat.py`
- keep `matlab_compat.py` limited to mechanical MATLAB compatibility
  primitives used by multiple translated files
- keep translation-specific helper logic inside the translated Python file
- if the MATLAB file has local subfunctions, keep them in the same Python file as private helpers
- only edit shared test helpers in `tests/helpers/` if strictly necessary
- prefer putting special-case test logic in `tests/oracle/test_<name>.py`

Do not rewrite shared files for style or consistency.

---

## Translation rules

When translating MATLAB to Python:

- preserve semantics over style
- keep variable names close to MATLAB where practical
- keep order of operations
- keep control flow close to MATLAB
- keep shapes explicit
- avoid clever rewrites
- avoid silent behavior changes
- add only small comments if they help auditability

The Python should be MATLAB-looking enough to audit.

### Strict fidelity rule

Do **not** add extra logic, validation layers, convenience wrappers, helper classes, or cleanup code unless they are strictly required for faithful translation.

If it is not required for faithful behavior, do not add it.

---

## Testing model

Use only these test categories:

- **oracle tests**: per-file MATLAB vs Python comparison
- **demo tests**: larger milestone tests added later

Default to oracle testing.

For most files, black-box testing is enough:
- same input to MATLAB and Python
- compare outputs

For very large or tricky files, add a small number of internal checkpoints only if needed.

---

## What to compare

When comparing MATLAB and Python, check:

- output structure
- shape
- sparse vs dense behavior when relevant
- numeric values
- important nested fields when relevant

Do not manually inspect results if they can be compared automatically.

---

## Repository layout

Typical layout:

```text
matlab_src/
python_src/
tests/
  oracle/
  demos/
  helpers/
docs/
```

### `matlab_src/`
Original MATLAB files. Do not rewrite these unless explicitly asked.

### `python_src/`
Translated Python files.

### `tests/oracle/`
Per-file MATLAB-vs-Python oracle tests.

### `tests/demos/`
Larger milestone tests added later.

### `tests/helpers/`
Small shared test utilities only.

Examples:
- MATLAB Engine session helper
- MATLAB function caller
- recursive comparison helper

Rules:
- keep shared helpers minimal
- do not edit them unless needed for the current file
- prefer file-specific logic in `test_<name>.py` over expanding shared helpers unnecessarily

---

## Expected workflow for one file

For each target file:

1. read the MATLAB file
2. identify inputs, outputs, dependencies, and risky MATLAB features
3. translate it conservatively into Python
4. create `tests/oracle/test_<name>.py`
5. compare MATLAB vs Python
6. fix mismatches
7. mark the file done only when the oracle test passes

---

## Risky MATLAB features

Be extra careful with:

- 1-based indexing
- row vs column vectors
- reshape/flatten behavior
- broadcasting differences
- sparse matrices
- cell arrays
- structs
- local subfunctions
- recursion
- nested models

When in doubt, preserve behavior rather than simplifying.

---

## MATLAB Engine usage

Use MATLAB Engine from Python for oracle tests.

Standard pattern:

1. start or reuse a MATLAB engine session
2. call the MATLAB function
3. call the Python function
4. compare outputs

---

## File completion standard

A translated file is complete only if:

- the Python translation exists
- it stays close to the MATLAB
- the oracle test exists
- the oracle test passes

No oracle test means the file is not done.

---

## Agent behavior rules

When working in this repository:

- do one concrete step at a time
- keep changes small and reviewable
- explain briefly what file is being translated or tested
- do not overcomplicate the plan
- do not introduce unnecessary abstractions
- do not optimize
- do not silently change semantics
- do not mark work complete without a passing oracle test

---

## Output expectations

For each task, produce only what is needed:

1. the translated Python file, or
2. the oracle test file, or
3. the smallest required shared test-helper change

At the end, briefly state:

- what file(s) changed
- why they changed
- whether any shared file was touched
- any known uncertainty
