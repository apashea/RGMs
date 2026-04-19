# MATLAB → Python Migration: Practical Reference

## Goal

Translate MATLAB code into Python as **exactly as possible**, with a first pass that stays **MATLAB-looking** for auditability.

We do **not** trust automatic translation by itself.

We trust:
1. the original MATLAB code
2. oracle tests that compare MATLAB vs Python
3. gradual translation in dependency order

---

## Core Principle

**MATLAB is the oracle. Python must prove it matches.**

For each function:
1. run the MATLAB original
2. run the Python translation
3. compare outputs, shapes, and important behavior
4. only accept the Python version if it matches

---

## What "exact" means here

"Exact" means:
- same inputs → same outputs
- same shape behavior
- same important logic
- same nested structure behavior
- same milestone demo behavior when relevant

For floating-point math, tiny tolerance may be needed.
For indexing and logic, exact equality is preferred.

---

## What is not realistic

There is **no known 100% guaranteed push-button MATLAB → native Python translator** for a codebase like this.

There are tools that help:
- MATLAB Engine API for Python: Python can call MATLAB
- MATLAB Compiler SDK: package MATLAB for Python use
- MATLAB Coder: generates C/C++, not Python
- community translators: can help draft code, but are not trustworthy enough to be the source of truth

So the guarantee comes from **testing**, not from conversion.

---

## Best overall strategy

Use a **2-pass migration**.

### Pass 1: faithful transliteration
Goal:
- preserve variable names
- preserve operation order
- preserve control flow
- preserve comments where useful
- keep Python close to MATLAB
- do not optimize
- do not refactor beyond what is needed for faithful behavior

### Pass 2: cleanup and optimization
Only after Pass 1 is proven:
- make code more Pythonic
- simplify proven local code where safe
- optimize speed
- refactor carefully with tests still green

---

## The actual workflow

### Step 1: make sure Python can call MATLAB
This is the most important setup step.

Why:
- Python needs to ask MATLAB for the original answer

Tool:
- MATLAB Engine API for Python

Minimal test:

```python
import matlab.engine
eng = matlab.engine.start_matlab()
print(eng.sqrt(4.0))
eng.quit()
```

If this works, the core migration workflow is possible.

### Step 2: keep `matlab_compat.py` narrow

`matlab_compat.py` is an approved **narrow exception** to the default rule against shared runtime translation helpers.

Use it only for **small, mechanical MATLAB-compatibility primitives** that are clearly shared across multiple translated files.

Good fits include things like:
- row-vector normalization
- MATLAB-like scalar unwrapping
- sparse `full` conversion
- `size` / `ndims` compatibility behavior
- other tiny generic shape or storage-order helpers that are already needed in multiple files

Do **not** use `matlab_compat.py` as a general shared toolbox.

Keep helper logic **inside the translated Python file** when it is:
- used by only one translated file
- specific to one algorithm or file family
- encoding behavior such as cell-array interpretation, concatenation rules, tensor products, or MDP field access
- being added just for neatness rather than true reuse

A good rule:
- if the helper is a tiny generic MATLAB primitive likely to be reused broadly, it may belong in `matlab_compat.py`
- if it smells tied to one function, one data structure, or one algorithm, keep it local

### Step 3: start with tiny helper functions

Do **not** start with the giant solver.
Start with small files first, such as:
- safe log
- softmax
- normalization
- vectorization helpers
- small Dirichlet helpers

Why:
- easier to test
- faster feedback
- helps settle reusable compatibility behavior conservatively
- lower risk

### Step 4: translate one file at a time

For each file:
1. read the MATLAB carefully
2. note inputs, outputs, shapes, and dependencies
3. translate into MATLAB-looking Python
4. create an oracle test that compares MATLAB vs Python
5. keep any failing cases as regression coverage only if they are justified by the file

### Step 5: for large files, compare checkpoints

For very large functions, do not compare only the final output.
Also compare internal checkpoints such as:

- initialization
- forward pass outputs
- backward pass outputs
- posterior updates
- recursion inputs/outputs

Use checkpoint comparisons only where they materially improve auditability.

### Step 6: use milestone demos

After enough lower-level files are translated:
- run milestone demos
- compare behavior at the system level

This checks integration, not just individual functions.

---

## Translation rules for Pass 1

1. Preserve semantics over style.
2. Keep variable names close to MATLAB.
3. Keep the order of operations.
4. Keep control flow unchanged.
5. Do not optimize early.
6. Keep array shapes explicit.
7. Prefer tiny shared compatibility primitives over clever rewrites.
8. Keep translation-specific helper logic in the translated file.
9. Keep local subfunctions in the same Python module at first.
10. Every translated file must have an oracle test.

---

## Main MATLAB → Python dangers

These are the biggest sources of bugs:

### 1. Indexing

- MATLAB starts at 1
- Python starts at 0

### 2. Shape and vectors

MATLAB often treats row/column vectors more explicitly than NumPy code does.

### 3. Memory order

MATLAB is column-major.
NumPy can behave differently unless handled carefully.

### 4. Broadcasting

NumPy may silently broadcast shapes in ways MATLAB code did not intend.

### 5. Transpose

A 1-D NumPy array does not transpose the way MATLAB users expect.

### 6. Cells, structs, sparse matrices

These need deliberate handling.

### 7. Over-abstraction

Trying to "clean up" MATLAB too early often introduces behavior drift.

---

## Tools to use

### Required
- MATLAB
- Python
- NumPy
- SciPy
- pytest
- Cursor and/or Codex

### Strongly recommended
- MATLAB Engine API for Python

### Optional later
- Hypothesis for randomized tests

---

## Good role for Cursor/Codex

Use them to:
- draft translations
- explain MATLAB idioms
- draft oracle tests
- point out repeated low-level compatibility behavior

Do **not** use them as proof that the translation is correct.

Rule:
**LLMs generate candidates. Tests decide truth.**

---

## Good repo structure

```text
project/
├── matlab_src/
├── matlab_compat.py
├── python_src/
│   ├── spm12/
│   └── toolbox/
├── tests/
│   ├── oracle/
│   ├── demos/
│   └── helpers/
├── scripts/
└── docs/
```

---

## Definition of done for one file

A file is done only when:
1. Python translation exists
2. it stays close to MATLAB
3. any needed shared compatibility primitive is genuinely shared
4. the oracle test exists
5. the oracle test passes

No oracle test = not done.

---

## Definition of done for the migration

The migration is only trustworthy when:

1. critical files are translated
2. file-level oracle tests pass
3. large-function checkpoints match where needed
4. milestone demos run
5. only then optimization begins

---

## Recommended first move

Do this first:
1. get MATLAB Engine working from Python
2. translate one tiny helper function
3. compare MATLAB vs Python on a few test cases
4. save that oracle-test pattern
5. repeat

That proves the pipeline works.

---

## One-sentence summary

**Do not trust the translator. Trust the MATLAB-vs-Python oracle tests, and keep `matlab_compat.py` tiny, shared, and mechanical.**
