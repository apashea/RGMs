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

## `spm_rgm_group` cell `O{o,t}` orientation (MATLAB Engine)

`spm_cat(R(o,:))` concatenates each time slice with the same **row** layout as
MATLAB `horzcat`. If `O{o,t}` is pushed into the Engine as a Python `tolist()`
from a column vector **without** an explicit `(Ns, 1)` shape, MATLAB may treat
it as a **1×Ns** row, producing a **1×(Ns·Nt)** `spm_cat` result instead of
**Ns×Nt** and breaking parity with NumPy. Oracle tests (and callers) should use
`matlab.double(..., size=(Ns, 1))` (or equivalent) so each `O{o,t}` is an
**Ns×1** column, matching `python_src`’s `(Ns, 1)` `ndarray` layout.

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

## `spm_MDP_pong`: `nP` output, `RGB.V` layout, PNG read vs MATLAB `imread`

**`nP` when `Np==0`:** Unmodified SPM `spm_MDP_pong.m` never assigns `nP` if the
distractor loop does not run, so requesting six outputs from MATLAB errors. The
staged copy under `matlab_src\toolbox\DEM\spm_MDP_pong.m` adds `nP =
zeros(1,Np)` after the default `Np` handling so Engine/oracle calls remain valid.
Python returns `nP` as a **1×Np** `float64` row (`zeros((1,0))` when `Np==0`).

**`RGB.V`:** MATLAB assigns **the same** basis matrix `V` into **every**
location of an **Nr×Nc** cell array (`RGB.V{i,j} = V`). Python mirrors this with
a list-of-lists of shape **Nr×Nc**, each entry a copy of the `192×5` matrix (for
`n=8`). Oracle tests compare `RGB.V{1,1}` to `RGB["V"][0][0]`.

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
**`control`**). **`RGB`** / **`imread`** comparisons are **deferred** — the
Python translation still executes the MATLAB-faithful RGB block for Pass 1, but
oracle assertions on **`RGB.N`**, **`RGB.G`**, and **`RGB.V`** are **`skip`ped**
until visualization / **`spm_O2rgb`** work is scheduled (`structure_learning_plan_week2.md` **S5**).

**`Na` reward / constraint tensors:** MATLAB builds `a = false(2,...)` then
`a(1,:,:) = true` before clearing/placing hits or misses. An early Python
mistake used `np.ones((2,...))`, which incorrectly set **both** outcome rows to
true initially; Port uses **`zeros`** then **`a[0,:,:] = True`** to mirror the
`.m` source.
